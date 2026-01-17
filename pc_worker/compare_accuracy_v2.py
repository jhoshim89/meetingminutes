"""STT 정확도 비교 - 화자 정보 제거 버전"""
import re
from pathlib import Path
from difflib import SequenceMatcher

GROUND_TRUTH = Path(r"D:\Productions\meetingminutes\data\시설과팀장님회의.txt")
OUTPUT_PATH = Path(r"D:\Productions\meetingminutes\pc_worker\output")

RESULTS = {
    "v3-turbo": "whisperx_large_v3_turbo_result.txt",
    "v3": "whisperx_large_v3_result.txt",
    "v2": "whisperx_result.txt",
    "Deepgram": "deepgram_result.txt",
    "AssemblyAI": "assemblyai_result.txt",
    "small-ko": "small_ko_result.txt",
}

def clean_clova(text):
    """ClovaNote 화자/타임스탬프 제거"""
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        # "참석자 N HH:MM" 패턴 제거
        if re.match(r'^참석자\s*\d+\s+\d+:\d+', line):
            continue
        # 헤더 제거
        if '새로운 녹음' in line or '심재호' in line:
            continue
        if re.match(r'^\d{4}\.\d{2}\.\d{2}', line):
            continue
        clean_lines.append(line)
    return ' '.join(clean_lines)

def normalize(text):
    """정규화"""
    text = re.sub(r'\s+', '', text)
    return text

def similarity(ref, hyp, samples=5):
    """샘플링 유사도"""
    ref = normalize(ref)
    hyp = normalize(hyp)

    chunk = min(len(ref), len(hyp)) // samples
    ratios = []
    for i in range(samples):
        start = i * chunk
        r = ref[start:start+chunk]
        h = hyp[start:start+chunk]
        if r and h:
            ratios.append(SequenceMatcher(None, r, h).ratio())
    return sum(ratios) / len(ratios) * 100 if ratios else 0

def main():
    print("=" * 55)
    print("STT 정확도 비교 (화자 정보 제거)")
    print("=" * 55)

    with open(GROUND_TRUTH, "r", encoding="utf-8") as f:
        raw_truth = f.read()

    ground_truth = clean_clova(raw_truth)
    print(f"ClovaNote (정제): {len(normalize(ground_truth))}자")
    print()
    print(f"{'모델':<15} {'유사도(%)':<12} {'길이'}")
    print("-" * 45)

    for name, fname in RESULTS.items():
        fpath = OUTPUT_PATH / fname
        if not fpath.exists():
            print(f"{name:<15} 없음")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            hyp = f.read()

        sim = similarity(ground_truth, hyp)
        print(f"{name:<15} {sim:<12.1f} {len(normalize(hyp))}")

    print("-" * 45)

if __name__ == "__main__":
    main()
