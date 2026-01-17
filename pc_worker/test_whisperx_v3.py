"""WhisperX large-v3 테스트"""
import whisperx
import soundfile as sf
import numpy as np
import torch
import time
import json
from pathlib import Path

AUDIO_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\temp_audio\test_sample6.wav")
OUTPUT_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\output")
OUTPUT_PATH.mkdir(exist_ok=True)

def test_model(model_name):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"=" * 60)
    print(f"WhisperX {model_name} 테스트")
    print(f"=" * 60)
    print(f"Device: {device}")

    # 모델 로드
    print(f"\n[1] {model_name} 로드...")
    start = time.time()
    model = whisperx.load_model(
        model_name,
        device,
        compute_type=compute_type,
        download_root="./models",
        language="ko"
    )
    load_time = time.time() - start
    print(f"로드: {load_time:.1f}초")

    # 오디오 로드
    audio, sr = sf.read(str(AUDIO_PATH))
    audio = audio.astype(np.float32)

    # 전사
    print(f"\n[2] 전사 중...")
    start = time.time()
    result = model.transcribe(audio, batch_size=16, language="ko")
    transcribe_time = time.time() - start
    print(f"전사: {transcribe_time:.1f}초")

    segments = result.get("segments", [])
    full_text = " ".join([seg["text"].strip() for seg in segments])

    print(f"세그먼트: {len(segments)}개")
    print(f"텍스트 길이: {len(full_text)}자")

    # 저장
    safe_name = model_name.replace("-", "_").replace("/", "_")
    with open(OUTPUT_PATH / f"whisperx_{safe_name}_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "full_text": full_text,
            "segments": segments,
            "load_time": load_time,
            "transcribe_time": transcribe_time
        }, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH / f"whisperx_{safe_name}_result.txt", "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\n저장: whisperx_{safe_name}_result.txt")
    print(f"\n=== 처음 500자 ===")
    print(full_text[:500])

    return {
        "model": model_name,
        "load_time": load_time,
        "transcribe_time": transcribe_time,
        "segments": len(segments),
        "text_length": len(full_text)
    }

if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "large-v3"
    test_model(model)
