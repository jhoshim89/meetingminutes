"""SungBeom/whisper-small-ko 테스트"""
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import torch
import time
import json
from pathlib import Path

AUDIO_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\temp_audio\test_sample6.wav")
OUTPUT_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\output")
OUTPUT_PATH.mkdir(exist_ok=True)

def main():
    print("=" * 60)
    print("SungBeom/whisper-small-ko 테스트")
    print("=" * 60)

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if device == "cuda:0" else torch.float32

    print(f"Device: {device}")

    model_id = "SungBeom/whisper-small-ko"

    print("\n[1] 모델 로드...")
    start = time.time()
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)
    load_time = time.time() - start
    print(f"로드: {load_time:.1f}초")

    print("\n[2] 파이프라인 생성...")
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        chunk_length_s=30,
        batch_size=8,
        torch_dtype=torch_dtype,
        device=device,
    )

    print("\n[3] 전사 중...")
    start = time.time()
    result = pipe(str(AUDIO_PATH), return_timestamps=False)
    transcribe_time = time.time() - start
    print(f"전사: {transcribe_time:.1f}초")

    text = result.get("text", "") if isinstance(result, dict) else str(result)
    print(f"텍스트 길이: {len(text)}자")

    # 저장
    with open(OUTPUT_PATH / "small_ko_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "full_text": text,
            "load_time": load_time,
            "transcribe_time": transcribe_time,
            "model": model_id
        }, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH / "small_ko_result.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n저장완료: {OUTPUT_PATH}")
    print("\n=== 처음 500자 ===")
    print(text[:500])

if __name__ == "__main__":
    main()
