"""
회의록 생성 파이프라인
======================
오디오 → 전사 → 요약/회의록 → DOCX

전체 워크플로우를 하나의 명령으로 실행
"""

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

# 로컬 모듈
from whisperx_engine import WhisperXEngine, WhisperXConfig
from hybrid_summarizer import HybridSummarizer

# Supabase 연동용
from models import Transcript, TranscriptSegment, MeetingStatus
from config import DEFAULT_USER_ID
from supabase_client import get_supabase_client

# 설정
DEFAULT_STT_MODEL = "large-v3-turbo"
DEFAULT_LLM_MODEL = "exaone3.5:7.8b"


def format_duration(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def segments_to_transcript(meeting_id: str, segments: List) -> Transcript:
    """WhisperX segments 리스트를 Transcript 객체로 변환"""
    transcript_segments = []
    for seg in segments:
        transcript_segments.append(TranscriptSegment(
            meeting_id=meeting_id,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            speaker_label=seg.speaker_label,
            confidence=getattr(seg, 'confidence', None)
        ))

    duration = segments[-1].end_time if segments else 0.0
    return Transcript(
        meeting_id=meeting_id,
        segments=transcript_segments,
        language="ko",
        duration=duration
    )


async def upload_to_supabase(
    audio_path: Path,
    transcript: Transcript,
    summary_dict: Optional[Dict],
    user_id: Optional[str] = None,
    title: Optional[str] = None
) -> Tuple[bool, str]:
    """
    파이프라인 결과를 Supabase에 업로드

    Returns:
        (success: bool, message: str) - 성공 여부와 meeting_id 또는 에러 메시지
    """
    meeting_id = None

    try:
        supabase = get_supabase_client()

        # Health check
        if not await supabase.health_check():
            return False, "Supabase 연결 실패"

        # 1. Meeting 레코드 생성
        meeting_title = title or audio_path.stem
        meeting_data = await supabase.create_meeting_from_local(
            title=meeting_title,
            audio_filename=audio_path.name,
            user_id=user_id or DEFAULT_USER_ID
        )
        meeting_id = meeting_data["id"]

        # 2. 상태: PROCESSING
        await supabase.update_meeting_status(
            meeting_id=meeting_id,
            status=MeetingStatus.PROCESSING
        )

        # 3. Transcript 저장
        if transcript and transcript.segments:
            # meeting_id 업데이트
            for seg in transcript.segments:
                seg.meeting_id = meeting_id
            transcript.meeting_id = meeting_id
            await supabase.save_transcript(meeting_id, transcript)

        # 4. Summary 저장
        if summary_dict:
            summary_dict["meeting_id"] = meeting_id
            await supabase.save_summary(meeting_id, summary_dict)

        # 5. 상태: COMPLETED
        await supabase.update_meeting_status(
            meeting_id=meeting_id,
            status=MeetingStatus.COMPLETED
        )

        return True, meeting_id

    except Exception as e:
        # 실패 시 상태 업데이트
        if meeting_id:
            try:
                supabase = get_supabase_client()
                await supabase.update_meeting_status(
                    meeting_id=meeting_id,
                    status=MeetingStatus.FAILED,
                    error_message=str(e)
                )
            except:
                pass
        return False, str(e)


def run_pipeline(
    audio_path: str,
    output_dir: Optional[str] = None,
    output_format: str = "all",
    stt_model: str = DEFAULT_STT_MODEL,
    llm_model: str = DEFAULT_LLM_MODEL,
    metadata: Optional[Dict[str, Any]] = None,
    skip_stt: bool = False,
    transcript_path: Optional[str] = None,
    verbose: bool = True,
    enable_diarization: bool = True,
    min_speakers: int = 1,
    max_speakers: int = 10,
    # Supabase 업로드 옵션
    upload: bool = False,
    user_id: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, str]:
    """
    전체 회의록 생성 파이프라인 실행

    Args:
        audio_path: 오디오 파일 경로
        output_dir: 출력 디렉토리 (기본: 오디오 파일과 같은 디렉토리)
        output_format: 출력 형식 ("summary", "minutes", "docx", "all")
        stt_model: WhisperX STT 모델
        llm_model: Ollama LLM 모델
        metadata: 회의록 메타데이터 (부서명, 장소 등)
        skip_stt: STT 건너뛰기 (기존 전사본 사용)
        transcript_path: 기존 전사본 파일 경로 (skip_stt=True 시 필요)
        verbose: 상세 출력
        enable_diarization: 화자분리 활성화 (기본: True)
        min_speakers: 최소 화자 수
        max_speakers: 최대 화자 수
        upload: Supabase에 결과 업로드 (기본: False)
        user_id: Supabase user ID (기본: DEFAULT_USER_ID)
        title: 회의 제목 (기본: 파일명)

    Returns:
        생성된 파일 경로들
    """
    start_time = time.time()
    results = {}

    # 경로 설정
    audio_file = Path(audio_path)
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = audio_file.parent

    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = audio_file.stem

    print("=" * 60)
    print("🎤 회의록 생성 파이프라인")
    print("=" * 60)
    print(f"입력: {audio_path}")
    print(f"출력 디렉토리: {out_dir}")
    print(f"출력 형식: {output_format}")
    print(f"STT 모델: {stt_model}")
    print(f"LLM 모델: {llm_model}")
    print(f"화자분리: {'활성화' if enable_diarization else '비활성화'}")
    if enable_diarization:
        print(f"화자 수: {min_speakers}~{max_speakers}명")
    print("-" * 60)

    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: STT (음성 → 텍스트)
    # ═══════════════════════════════════════════════════════════════════

    transcript_text = ""
    raw_segments = []  # 업로드용 원본 segments 저장
    summary_result = None  # 업로드용 요약 결과 저장
    summarizer = None  # to_meeting_summary 호출용
    meeting_id = str(uuid.uuid4())  # 항상 meeting_id 생성

    if skip_stt and transcript_path:
        print(f"\n[1/3] STT 건너뛰기 - 기존 전사본 사용: {transcript_path}")
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        results['transcript'] = transcript_path
    else:
        print(f"\n[1/3] STT 처리 중... ({stt_model})")
        stt_start = time.time()

        try:
            config = WhisperXConfig(
                model_size=stt_model,
                enable_diarization=enable_diarization,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            engine = WhisperXEngine(config=config)

            # transcribe is async, so we need to run it with asyncio
            segments = asyncio.run(engine.transcribe(Path(audio_path), meeting_id))
            raw_segments = segments  # 업로드용 저장

            # 전사본 저장
            transcript_path = out_dir / f"{base_name}_전사본.txt"
            transcript_lines = []

            for segment in segments:
                start = segment.start_time
                end = segment.end_time
                text = segment.text
                speaker = segment.speaker_label or ''

                if speaker:
                    transcript_lines.append(f"[{start:.1f}s-{end:.1f}s] {speaker}: {text}")
                else:
                    transcript_lines.append(f"[{start:.1f}s-{end:.1f}s] {text}")

            transcript_text = '\n'.join(transcript_lines)

            with open(str(transcript_path), 'w', encoding='utf-8') as f:
                f.write(transcript_text)

            results['transcript'] = str(transcript_path)

            stt_duration = time.time() - stt_start
            print(f"    ✓ 완료 ({stt_duration:.1f}초)")
            print(f"    → {transcript_path}")

        except Exception as e:
            print(f"    ✗ STT 오류: {e}")
            import traceback
            traceback.print_exc()
            return results

    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: LLM 하이브리드 요약 (구조화 + 비구조화 통합)
    # ═══════════════════════════════════════════════════════════════════

    print(f"\n[2/3] LLM 하이브리드 요약 처리 중... ({llm_model})")
    summary_start = time.time()

    try:
        summarizer = HybridSummarizer(model=llm_model)

        # 하이브리드 요약 실행 (한 번에 모든 형식 생성)
        summary_result = summarizer.summarize(transcript_text, verbose=verbose)

        if output_format in ["summary", "all"]:
            # 통합 요약 텍스트 저장
            summary_path = out_dir / f"{base_name}_요약.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_result.raw_text)

            results['summary'] = str(summary_path)
            print(f"    ✓ 요약 완료")
            print(f"    → {summary_path}")

        if output_format in ["minutes", "docx", "all"]:
            # 회의록 JSON 생성
            minutes_json = summarizer.to_minutes_json(
                summary_result,
                metadata=metadata or {}
            )

            json_path = out_dir / f"{base_name}_회의록.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(minutes_json, f, ensure_ascii=False, indent=2)

            results['minutes_json'] = str(json_path)
            print(f"    ✓ 회의록 JSON 완료")
            print(f"    → {json_path}")

        summary_duration = time.time() - summary_start
        print(f"    총 요약 시간: {summary_duration:.1f}초")

    except Exception as e:
        print(f"    ✗ 요약 오류: {e}")
        import traceback
        traceback.print_exc()
        return results

    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: DOCX 생성
    # ═══════════════════════════════════════════════════════════════════

    if output_format in ["docx", "all"] and 'minutes_json' in results:
        print(f"\n[3/3] DOCX 회의록 생성 중...")
        docx_start = time.time()

        try:
            import subprocess

            script_path = Path(__file__).parent / "generate_minutes_docx.js"
            docx_path = out_dir / f"{base_name}_회의록.docx"

            result = subprocess.run(
                ["node", str(script_path), results['minutes_json'], str(docx_path)],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent)
            )

            if result.returncode == 0:
                results['docx'] = str(docx_path)
                docx_duration = time.time() - docx_start
                print(f"    ✓ 완료 ({docx_duration:.1f}초)")
                print(f"    → {docx_path}")
            else:
                print(f"    ✗ DOCX 생성 오류: {result.stderr}")

        except FileNotFoundError:
            print("    ✗ Node.js가 설치되지 않음 - JSON만 생성됨")
        except Exception as e:
            print(f"    ✗ DOCX 생성 오류: {e}")
    else:
        print(f"\n[3/3] DOCX 생성 건너뛰기")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 4: Supabase 업로드 (선택)
    # ═══════════════════════════════════════════════════════════════════

    if upload:
        print(f"\n[4/4] Supabase 업로드 중...")
        upload_start = time.time()

        try:
            # Transcript 객체 생성
            transcript_obj = None
            if raw_segments:
                transcript_obj = segments_to_transcript(meeting_id, raw_segments)

            # Summary dict 생성
            summary_dict = None
            if summary_result and summarizer:
                summary_dict = summarizer.to_meeting_summary(
                    summary_result,
                    meeting_id=meeting_id
                )

            # 업로드 실행
            success, result = asyncio.run(upload_to_supabase(
                audio_path=audio_file,
                transcript=transcript_obj,
                summary_dict=summary_dict,
                user_id=user_id,
                title=title or base_name
            ))

            upload_duration = time.time() - upload_start
            if success:
                results['meeting_id'] = result
                print(f"    ✓ 업로드 완료 ({upload_duration:.1f}초)")
                print(f"    → Meeting ID: {result}")
            else:
                print(f"    ✗ 업로드 실패: {result}")

        except Exception as e:
            print(f"    ✗ 업로드 오류: {e}")
    else:
        if verbose:
            print(f"\n[4/4] Supabase 업로드 건너뛰기 (--upload 옵션 없음)")

    # ═══════════════════════════════════════════════════════════════════
    # 완료
    # ═══════════════════════════════════════════════════════════════════

    total_duration = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ 파이프라인 완료 (총 {total_duration:.1f}초)")
    print("=" * 60)

    if results:
        print("\n생성된 파일:")
        for key, path in results.items():
            print(f"  - {key}: {path}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="회의 음성 → 전사 → 요약/회의록 → DOCX 자동 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
출력 형식:
  summary  - 자연스러운 요약 (클로바노트 스타일)
  minutes  - 회의록 JSON
  docx     - 회의록 DOCX 문서
  all      - 모든 형식 (기본값)

예시:
  # 오디오 파일에서 전체 파이프라인 실행
  python meeting_pipeline.py ../data/회의.m4a

  # 요약만 생성
  python meeting_pipeline.py ../data/회의.m4a -f summary

  # 기존 전사본으로 회의록 생성
  python meeting_pipeline.py ../data/회의.m4a --skip-stt -t ../data/회의_전사본.txt -f docx

  # 메타데이터 지정
  python meeting_pipeline.py ../data/회의.m4a --department "수의과대학" --location "교수회의실"

  # Supabase에 업로드
  python meeting_pipeline.py ../data/회의.m4a --upload

  # 제목 지정하여 업로드
  python meeting_pipeline.py ../data/회의.m4a --upload --meeting-title "주간회의"
        """
    )

    parser.add_argument('audio', help='오디오 파일 경로')
    parser.add_argument('-o', '--output-dir', help='출력 디렉토리')
    parser.add_argument('-f', '--format', default='all',
                        choices=['summary', 'minutes', 'docx', 'all'],
                        help='출력 형식 (기본: all)')
    parser.add_argument('--stt-model', default=DEFAULT_STT_MODEL,
                        help=f'STT 모델 (기본: {DEFAULT_STT_MODEL})')
    parser.add_argument('--llm-model', default=DEFAULT_LLM_MODEL,
                        help=f'LLM 모델 (기본: {DEFAULT_LLM_MODEL})')
    parser.add_argument('--skip-stt', action='store_true',
                        help='STT 건너뛰기 (기존 전사본 사용)')
    parser.add_argument('-t', '--transcript', help='기존 전사본 파일 경로')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='간략한 출력')

    # 화자분리 옵션
    parser.add_argument('--no-diarization', action='store_true',
                        help='화자분리 비활성화')
    parser.add_argument('--min-speakers', type=int, default=1,
                        help='최소 화자 수 (기본: 1)')
    parser.add_argument('--max-speakers', type=int, default=10,
                        help='최대 화자 수 (기본: 10)')

    # 메타데이터 옵션
    parser.add_argument('--department', help='부서명')
    parser.add_argument('--location', help='장소')
    parser.add_argument('--datetime', help='일시')
    parser.add_argument('--organizer', help='소집자')
    parser.add_argument('--attendees', help='참석자 (쉼표로 구분)')
    parser.add_argument('--absentees', help='불참자')

    # Supabase 업로드 옵션
    parser.add_argument('--upload', '-u', action='store_true',
                        help='Supabase에 결과 업로드')
    parser.add_argument('--user-id',
                        help='Supabase user ID (기본: DEFAULT_USER_ID)')
    parser.add_argument('--meeting-title',
                        help='회의 제목 (기본: 파일명)')

    args = parser.parse_args()

    # 메타데이터 구성 (None이 아닌 값만 포함)
    metadata_fields = ['department', 'location', 'datetime', 'organizer', 'attendees', 'absentees']
    metadata = {k: getattr(args, k) for k in metadata_fields if getattr(args, k)}

    # 파이프라인 실행
    results = run_pipeline(
        audio_path=args.audio,
        output_dir=args.output_dir,
        output_format=args.format,
        stt_model=args.stt_model,
        llm_model=args.llm_model,
        metadata=metadata if metadata else None,
        skip_stt=args.skip_stt,
        transcript_path=args.transcript,
        verbose=not args.quiet,
        enable_diarization=not args.no_diarization,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
        # Supabase 업로드 옵션
        upload=args.upload,
        user_id=args.user_id,
        title=args.meeting_title
    )

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
