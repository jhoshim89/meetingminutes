"""Deepgram API 테스트 (SDK v5)"""
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

AUDIO_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\temp_audio\test_sample6.wav")
OUTPUT_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\output")
OUTPUT_PATH.mkdir(exist_ok=True)

API_KEY = os.getenv("DEEPGRAM_API_KEY")

def main():
    print("=" * 60)
    print("Deepgram API 테스트 (SDK v5)")
    print("=" * 60)

    print(f"\n오디오 파일: {AUDIO_PATH}")
    print(f"파일 크기: {AUDIO_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    from deepgram import DeepgramClient
    client = DeepgramClient(api_key=API_KEY)

    with open(AUDIO_PATH, "rb") as f:
        audio_data = f.read()

    print("\n[1] 업로드 및 전사 중...")
    start = time.time()

    response = client.listen.v1.media.transcribe_file(
        request=audio_data,
        model="nova-2",
        language="ko",
        smart_format=True
    )
    transcribe_time = time.time() - start

    # pydantic 모델 - 직접 속성 접근
    text = response.results.channels[0].alternatives[0].transcript
    confidence = response.results.channels[0].alternatives[0].confidence

    print(f"\n전사 완료: {transcribe_time:.1f}초")
    print(f"텍스트 길이: {len(text)}자")
    print(f"신뢰도: {confidence:.2%}")

    # 저장
    with open(OUTPUT_PATH / "deepgram_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "full_text": text,
            "transcribe_time": transcribe_time,
            "model": "deepgram-nova-2",
            "confidence": confidence
        }, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH / "deepgram_result.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n저장완료: {OUTPUT_PATH}")
    print("\n=== 처음 500자 ===")
    print(text[:500])

if __name__ == "__main__":
    main()
