"""
최종 WhisperX 전사 테스트
변경된 VAD 설정(onset=0.1, offset=0.1)으로 학과회의 전사
"""

# PyTorch 2.6+ 호환성 패치 적용 (반드시 torch import 전에!)
from config import WHISPERX_MODEL, ENABLE_GPU, CUDA_DEVICE, MODEL_CACHE_DIR

import json
import time
from pathlib import Path
import torch
import whisperx
import soundfile as sf
import numpy as np

# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"  # 프로젝트 루트의 data
OUTPUT_DIR = Path(__file__).parent / "output"
AUDIO_FILE = DATA_DIR / "학과회의.m4a"
CLOVANOTE_FILE = DATA_DIR / "학과회의.txt"

# 출력 파일
OUTPUT_TXT = OUTPUT_DIR / "whisperx_final_전사.txt"
OUTPUT_JSON = OUTPUT_DIR / "whisperx_final_전사.json"

# VAD 설정 (whisperx_engine.py와 동일)
VAD_CONFIG = {
    "vad_onset": 0.1,  # 한국어 최적화
    "vad_offset": 0.1,
    "chunk_size": 30
}

MODEL_SIZE = "large-v3-turbo"  # 빠른 모델


def load_audio(audio_path: Path) -> np.ndarray:
    """오디오 로드 (16kHz mono)"""
    import subprocess
    import tempfile

    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_path = "ffmpeg"

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        temp_wav = tmp.name

    try:
        cmd = [
            ffmpeg_path,
            '-i', str(audio_path),
            '-ar', '16000',
            '-ac', '1',
            '-f', 'wav',
            '-y',
            temp_wav
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"ffmpeg error: {result.stderr}")

        audio_data, _ = sf.read(temp_wav)
        return audio_data.astype(np.float32)
    finally:
        import os
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def transcribe_with_vad():
    """VAD 설정으로 전사"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"\n[CONFIG]")
    print(f"   모델: {MODEL_SIZE}")
    print(f"   디바이스: {device}")
    print(f"   VAD onset: {VAD_CONFIG['vad_onset']}")
    print(f"   VAD offset: {VAD_CONFIG['vad_offset']}")

    # 모델 로드
    print(f"\n[LOAD] WhisperX 모델 로드 중...")
    start = time.time()

    model = whisperx.load_model(
        MODEL_SIZE,
        device,
        compute_type=compute_type,
        download_root=str(MODEL_CACHE_DIR),
        vad_options=VAD_CONFIG
    )

    load_time = time.time() - start
    print(f"[DONE] 모델 로드: {load_time:.1f}초")

    # 오디오 로드
    print(f"\n[LOAD] 오디오 로드 중: {AUDIO_FILE.name}")
    audio = load_audio(AUDIO_FILE)
    duration = len(audio) / 16000
    print(f"[DONE] 오디오: {duration:.1f}초 ({duration/60:.1f}분)")

    # 전사
    print(f"\n[TRANSCRIBE] 전사 시작...")
    start = time.time()

    result = model.transcribe(
        audio,
        batch_size=16,
        language="ko",
        chunk_size=30
    )

    transcribe_time = time.time() - start
    print(f"[DONE] 전사 완료: {transcribe_time:.1f}초")

    return result, {
        "model_load_time": load_time,
        "transcribe_time": transcribe_time,
        "audio_duration": duration
    }


def load_clovanote():
    """ClovaNote 전사본 로드"""
    if not CLOVANOTE_FILE.exists():
        return None
    with open(CLOVANOTE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def main():
    print("=" * 60)
    print("WhisperX 최종 전사 테스트")
    print("VAD 설정: onset=0.1, offset=0.1 (한국어 최적화)")
    print("=" * 60)

    if not AUDIO_FILE.exists():
        print(f"[ERROR] 오디오 파일 없음: {AUDIO_FILE}")
        return

    # 전사 실행
    result, timing = transcribe_with_vad()

    # 세그먼트 처리
    segments = []
    full_text = ""

    for seg in result["segments"]:
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })
        full_text += seg["text"].strip() + " "

    full_text = full_text.strip()

    # ClovaNote와 비교
    clovanote = load_clovanote()
    clovanote_len = len(clovanote) if clovanote else 0

    ratio = (len(full_text) / clovanote_len * 100) if clovanote_len > 0 else 0

    # 결과 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 텍스트 저장
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("WhisperX 전사 결과\n")
        f.write(f"모델: {MODEL_SIZE}\n")
        f.write(f"VAD: onset={VAD_CONFIG['vad_onset']}, offset={VAD_CONFIG['vad_offset']}\n")
        f.write(f"전사 시간: {timing['transcribe_time']:.1f}초\n")
        f.write(f"오디오 길이: {timing['audio_duration']:.1f}초\n")
        f.write("=" * 60 + "\n\n")

        for seg in segments:
            start_min = int(seg["start"] // 60)
            start_sec = int(seg["start"] % 60)
            f.write(f"[{start_min:02d}:{start_sec:02d}] {seg['text']}\n")

    # JSON 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "model": MODEL_SIZE,
            "vad_config": VAD_CONFIG,
            "timing": timing,
            "segment_count": len(segments),
            "total_text_length": len(full_text),
            "clovanote_length": clovanote_len,
            "ratio_vs_clovanote": round(ratio, 2),
            "segments": segments
        }, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print("\n" + "=" * 60)
    print("[결과]")
    print("=" * 60)
    print(f"   세그먼트 수: {len(segments)}")
    print(f"   전체 텍스트: {len(full_text):,} 글자")
    print(f"   ClovaNote:   {clovanote_len:,} 글자")
    print(f"   비율:        {ratio:.1f}%")
    print(f"\n   전사 시간:   {timing['transcribe_time']:.1f}초")
    print(f"   실시간 비율: {timing['audio_duration']/timing['transcribe_time']:.1f}x")

    print(f"\n[저장됨]")
    print(f"   {OUTPUT_TXT}")
    print(f"   {OUTPUT_JSON}")

    # 샘플 출력
    print("\n" + "=" * 60)
    print("[샘플] 처음 10개 세그먼트:")
    print("=" * 60)
    for seg in segments[:10]:
        start_min = int(seg["start"] // 60)
        start_sec = int(seg["start"] % 60)
        text = seg["text"][:60] + "..." if len(seg["text"]) > 60 else seg["text"]
        try:
            print(f"[{start_min:02d}:{start_sec:02d}] {text}")
        except UnicodeEncodeError:
            print(f"[{start_min:02d}:{start_sec:02d}] (인코딩 오류)")


if __name__ == "__main__":
    main()
