"""
WhisperX 전사 결과 + LLM 요약 테스트
"""

import json
import time
from pathlib import Path
import requests

OUTPUT_DIR = Path(__file__).parent / "output"
WHISPERX_JSON = OUTPUT_DIR / "whisperx_final_전사.json"
SUMMARY_OUTPUT = OUTPUT_DIR / "llm_summary_결과.txt"

OLLAMA_URL = "http://localhost:11434"

# 테스트할 모델들
MODELS = [
    "exaone3.5:7.8b",  # 한국어 특화
    # "phi4:latest",   # 큰 모델
]

SUMMARY_PROMPT = """아래 회의 전사본을 주제별로 빠짐없이 상세하게 요약해주세요.
없는 내용을 만들어내지 마세요.

{transcript}
"""


def load_transcript():
    """전사본 로드"""
    if not WHISPERX_JSON.exists():
        print(f"[ERROR] 파일 없음: {WHISPERX_JSON}")
        return None

    with open(WHISPERX_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 타임스탬프 포함 전사본
    lines = []
    for seg in data["segments"]:
        start_min = int(seg["start"] // 60)
        start_sec = int(seg["start"] % 60)
        lines.append(f"[{start_min:02d}:{start_sec:02d}] {seg['text']}")

    return "\n".join(lines), data


def generate_summary(transcript: str, model: str) -> tuple:
    """LLM으로 요약 생성"""
    prompt = SUMMARY_PROMPT.format(transcript=transcript)

    try:
        start = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 2048,
                    "num_ctx": 16384  # 컨텍스트 윈도우 확장
                }
            },
            timeout=600
        )
        response.raise_for_status()
        elapsed = time.time() - start
        return response.json()["response"], elapsed
    except Exception as e:
        print(f"[ERROR] API 오류: {e}")
        return "", 0


def main():
    print("=" * 60)
    print("WhisperX 전사 + LLM 요약 테스트")
    print("=" * 60)

    result = load_transcript()
    if not result:
        return

    transcript, data = result
    print(f"[LOAD] 전사본: {len(transcript):,} 글자")
    print(f"       세그먼트: {data['segment_count']}개")

    results = []

    for model in MODELS:
        print(f"\n[TEST] {model}")
        print("-" * 40)

        summary, elapsed = generate_summary(transcript, model)

        if not summary:
            print(f"[ERROR] 요약 생성 실패")
            continue

        print(f"[DONE] 생성 완료: {elapsed:.1f}초")

        results.append({
            "model": model,
            "elapsed": elapsed,
            "summary": summary
        })

        # 결과 미리보기
        print(f"\n[미리보기]")
        print("-" * 40)
        preview = summary[:1500]
        try:
            print(preview)
            if len(summary) > 1500:
                print("...(생략)")
        except UnicodeEncodeError:
            print("(콘솔 인코딩 문제)")

    # 저장
    with open(SUMMARY_OUTPUT, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("WhisperX 전사 + LLM 요약 결과\n")
        f.write("=" * 60 + "\n\n")

        for r in results:
            f.write(f"모델: {r['model']}\n")
            f.write(f"생성 시간: {r['elapsed']:.1f}초\n")
            f.write("-" * 40 + "\n")
            f.write(r["summary"])
            f.write("\n\n")

    print(f"\n[저장됨] {SUMMARY_OUTPUT}")


if __name__ == "__main__":
    main()
