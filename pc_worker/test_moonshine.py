"""
Moonshine STT 테스트 스크립트
직접 오디오 파일로 한국어 인식 품질을 테스트합니다.
"""

import asyncio
import sys
from pathlib import Path

# 상위 디렉토리의 config를 먼저 로드
sys.path.insert(0, str(Path(__file__).parent))
from config import *

from moonshine_engine import MoonshineEngine, get_moonshine_engine


async def test_simple_transcription(audio_path: str):
    """단순 전사 테스트 (화자분리 없이)"""
    print("\n" + "="*60)
    print("🌙 Moonshine Korean STT 테스트")
    print("="*60)

    engine = get_moonshine_engine()

    print("\n[1/3] 모델 로딩 중...")
    await engine.initialize()

    model_info = engine.get_model_info()
    print(f"  ✓ 모델: {model_info['model_name']}")
    print(f"  ✓ 백엔드: {model_info['backend']}")
    print(f"  ✓ 디바이스: {model_info['device']}")

    print(f"\n[2/3] 오디오 전사 중: {audio_path}")
    segments = await engine.transcribe(
        Path(audio_path),
        meeting_id="test-001"
    )

    print("\n[3/3] 결과:")
    print("-"*60)
    for seg in segments:
        print(f"  [{seg.start_time:.1f}s - {seg.end_time:.1f}s]")
        print(f"  {seg.text}")
        print()
    print("-"*60)

    # 정리
    await engine.cleanup()
    print("\n✅ 테스트 완료!")


async def test_with_diarization(audio_path: str):
    """화자분리와 함께 전사 테스트"""
    print("\n" + "="*60)
    print("🌙 Moonshine + Pyannote 화자분리 테스트")
    print("="*60)

    from stt_pipeline import get_stt_pipeline

    pipeline = get_stt_pipeline()

    print("\n[1/4] 파이프라인 초기화 중...")
    await pipeline.initialize()

    print(f"\n[2/4] 오디오 처리 중: {audio_path}")
    result = await pipeline.process_audio(
        Path(audio_path),
        meeting_id="test-diarization-001",
        language="ko"
    )

    print(f"\n[3/4] 결과 요약:")
    print(f"  ✓ 감지된 화자 수: {result.num_speakers_detected}")
    print(f"  ✓ 세그먼트 수: {len(result.transcript.segments)}")
    print(f"  ✓ 처리 시간: {result.processing_time_seconds:.2f}초")
    print(f"  ✓ 화자분리 시간: {result.diarization_time:.2f}초")
    print(f"  ✓ 전사 시간: {result.transcription_time:.2f}초")

    print(f"\n[4/4] 트랜스크립트:")
    print("-"*60)
    for seg in result.transcript.segments:
        speaker = seg.speaker_label or "Unknown"
        print(f"  [{seg.start_time:.1f}s - {seg.end_time:.1f}s] {speaker}:")
        print(f"    {seg.text}")
        print()
    print("-"*60)

    # 정리
    await pipeline.cleanup()
    print("\n✅ 테스트 완료!")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Moonshine STT 테스트")
    parser.add_argument(
        "audio_path",
        nargs="?",
        default="test_audio.webm",
        help="테스트할 오디오 파일 경로 (기본: test_audio.webm)"
    )
    parser.add_argument(
        "--with-diarization", "-d",
        action="store_true",
        help="화자분리와 함께 테스트"
    )
    parser.add_argument(
        "--simple", "-s",
        action="store_true",
        help="단순 전사만 테스트 (기본)"
    )

    args = parser.parse_args()

    # 오디오 파일 확인
    audio_path = Path(args.audio_path)
    if not audio_path.exists():
        # 상위 디렉토리에서 찾기
        alt_path = Path(__file__).parent.parent / args.audio_path
        if alt_path.exists():
            audio_path = alt_path
        else:
            print(f"❌ 오디오 파일을 찾을 수 없습니다: {args.audio_path}")
            print("\n사용법:")
            print("  python test_moonshine.py <오디오파일>")
            print("  python test_moonshine.py test_audio.webm -d  # 화자분리 포함")
            sys.exit(1)

    # 테스트 실행
    if args.with_diarization:
        asyncio.run(test_with_diarization(str(audio_path)))
    else:
        asyncio.run(test_simple_transcription(str(audio_path)))


if __name__ == "__main__":
    main()
