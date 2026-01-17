"""AssemblyAI API 테스트"""
import assemblyai as aai
import time
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

AUDIO_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\temp_audio\test_sample6.wav")
OUTPUT_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\output")
OUTPUT_PATH.mkdir(exist_ok=True)

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

def main():
    print("=" * 60)
    print("AssemblyAI API 테스트")
    print("=" * 60)

    aai.settings.api_key = API_KEY

    print(f"\n오디오 파일: {AUDIO_PATH}")
    print(f"파일 크기: {AUDIO_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    # 설정 - universal 모델 사용
    config = aai.TranscriptionConfig(
        language_code="ko",
        speech_model=aai.SpeechModel.nano
    )

    transcriber = aai.Transcriber()

    print("\n[1] 업로드 및 전사 중... (몇 분 소요)")
    start = time.time()
    transcript = transcriber.transcribe(str(AUDIO_PATH), config=config)
    transcribe_time = time.time() - start

    if transcript.status == aai.TranscriptStatus.error:
        print(f"오류: {transcript.error}")
        return

    text = transcript.text or ""
    print(f"\n전사 완료: {transcribe_time:.1f}초")
    print(f"텍스트 길이: {len(text)}자")

    # 저장
    with open(OUTPUT_PATH / "assemblyai_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "full_text": text,
            "transcribe_time": transcribe_time,
            "model": "assemblyai-best",
            "confidence": transcript.confidence
        }, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH / "assemblyai_result.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n저장완료: {OUTPUT_PATH}")
    print("\n=== 처음 500자 ===")
    print(text[:500])

if __name__ == "__main__":
    main()
