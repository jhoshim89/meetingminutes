#!/usr/bin/env python3
"""
STT 엔진 비교 테스트 스크립트
WhisperX (threshold 0.4) vs 한국어 파인튜닝 모델 비교

사용법:
    python test_stt_comparison.py <audio_file.wav>
    python test_stt_comparison.py <audio_file.wav> --models all
    python test_stt_comparison.py <audio_file.wav> --models whisperx
    python test_stt_comparison.py <audio_file.wav> --models korean
"""

import asyncio
import argparse
import time
from pathlib import Path
from typing import Dict, List
import sys

# 상위 모듈 import
sys.path.insert(0, str(Path(__file__).parent))

from models import TranscriptSegment


async def test_whisperx(audio_path: Path, meeting_id: str) -> Dict:
    """WhisperX 엔진 테스트 (threshold 0.4)"""
    from whisperx_engine import get_whisperx_engine, WhisperXConfig

    print("\n" + "=" * 60)
    print("🔵 테스트 A: WhisperX (large-v2, threshold=0.4)")
    print("=" * 60)

    config = WhisperXConfig(
        model_size="large-v2",
        language="ko",
        confidence_threshold=0.4  # 한국어 최적화
    )

    engine = get_whisperx_engine(model_size=config.model_size)
    engine.config = config

    start_time = time.time()

    try:
        await engine.initialize()
        print(f"✓ 모델 로드 완료: {engine.get_model_info()['model_size']}")
        print(f"  - Device: {engine.config.device}")
        print(f"  - Confidence Threshold: {engine.config.confidence_threshold}")

        segments = await engine.transcribe(audio_path, meeting_id)
        elapsed = time.time() - start_time

        print(f"\n📝 인식 결과 ({len(segments)} 세그먼트):")
        print("-" * 40)

        full_text = ""
        for seg in segments:
            time_str = f"[{seg.start_time:.1f}s-{seg.end_time:.1f}s]"
            conf_str = f"(신뢰도: {seg.confidence:.2f})" if seg.confidence else ""
            print(f"  {time_str} {seg.text} {conf_str}")
            full_text += seg.text + " "

        print("-" * 40)
        print(f"⏱️  처리 시간: {elapsed:.2f}초")

        await engine.cleanup()

        return {
            "engine": "WhisperX (large-v2, threshold=0.4)",
            "segments": segments,
            "full_text": full_text.strip(),
            "elapsed": elapsed,
            "segment_count": len(segments)
        }

    except Exception as e:
        print(f"❌ 오류: {e}")
        return {"engine": "WhisperX", "error": str(e)}


async def test_korean_model(audio_path: Path, meeting_id: str, model_id: str = None) -> Dict:
    """한국어 파인튜닝 모델 테스트"""
    from whisper_korean_engine import get_korean_whisper_engine, KoreanWhisperConfig, KOREAN_MODELS

    model_id = model_id or "ghost613/whisper-large-v3-turbo-korean"

    print("\n" + "=" * 60)
    print(f"🟢 테스트 B: 한국어 파인튜닝 모델")
    print(f"   Model: {model_id}")
    print("=" * 60)

    engine = get_korean_whisper_engine(model_id=model_id)

    start_time = time.time()

    try:
        await engine.initialize()
        info = engine.get_model_info()
        print(f"✓ 모델 로드 완료")
        print(f"  - Model: {info['model_id']}")
        print(f"  - Size: {info['model_size']}")
        print(f"  - Device: {info['device']}")
        print(f"  - GPU: {info['gpu_name']}")

        segments = await engine.transcribe(audio_path, meeting_id)
        elapsed = time.time() - start_time

        print(f"\n📝 인식 결과 ({len(segments)} 세그먼트):")
        print("-" * 40)

        full_text = ""
        for seg in segments:
            time_str = f"[{seg.start_time:.1f}s-{seg.end_time:.1f}s]"
            print(f"  {time_str} {seg.text}")
            full_text += seg.text + " "

        print("-" * 40)
        print(f"⏱️  처리 시간: {elapsed:.2f}초")

        await engine.cleanup()

        return {
            "engine": f"Korean Fine-tuned ({model_id})",
            "segments": segments,
            "full_text": full_text.strip(),
            "elapsed": elapsed,
            "segment_count": len(segments)
        }

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return {"engine": f"Korean ({model_id})", "error": str(e)}


def print_comparison(results: List[Dict]):
    """결과 비교 출력"""
    print("\n")
    print("=" * 70)
    print("📊 비교 결과 요약")
    print("=" * 70)

    valid_results = [r for r in results if "error" not in r]

    if not valid_results:
        print("❌ 모든 테스트 실패")
        return

    print(f"\n{'엔진':<45} {'세그먼트':<10} {'처리시간':<10}")
    print("-" * 70)

    for r in valid_results:
        print(f"{r['engine']:<45} {r['segment_count']:<10} {r['elapsed']:.2f}초")

    print("\n" + "-" * 70)
    print("\n📝 전체 텍스트 비교:")

    for r in valid_results:
        print(f"\n[{r['engine']}]")
        print(f"  {r['full_text'][:200]}..." if len(r['full_text']) > 200 else f"  {r['full_text']}")

    print("\n" + "=" * 70)
    print("💡 팁: 결과를 직접 들어보고 어느 쪽이 더 정확한지 판단하세요!")
    print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(description="STT 엔진 비교 테스트")
    parser.add_argument("audio_file", help="테스트할 오디오 파일 경로")
    parser.add_argument(
        "--models",
        choices=["all", "whisperx", "korean", "all3"],
        default="all3",
        help="테스트할 모델 (기본: all3 = 세 개 모두)"
    )

    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {audio_path}")
        sys.exit(1)

    meeting_id = f"test_{int(time.time())}"
    results = []

    print("\n" + "🎤 " * 20)
    print(f"STT 엔진 비교 테스트")
    print(f"오디오 파일: {audio_path}")
    print("🎤 " * 20)

    # WhisperX 테스트
    if args.models in ["all", "all3", "whisperx"]:
        result = await test_whisperx(audio_path, meeting_id)
        results.append(result)

    # 한국어 모델 테스트 - ghost613 (large-v3-turbo)
    if args.models in ["all3"]:
        result = await test_korean_model(
            audio_path, meeting_id,
            "ghost613/whisper-large-v3-turbo-korean"
        )
        results.append(result)

    # 한국어 모델 테스트 - seastar105 (medium)
    if args.models in ["all", "all3", "korean"]:
        result = await test_korean_model(
            audio_path, meeting_id,
            "seastar105/whisper-medium-ko-zeroth"
        )
        results.append(result)

    # 결과 비교
    if len(results) > 1:
        print_comparison(results)


if __name__ == "__main__":
    asyncio.run(main())
