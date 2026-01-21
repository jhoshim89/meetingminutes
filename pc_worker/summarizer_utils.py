"""
Summarizer 공통 유틸리티 모듈
============================
hybrid_summarizer, natural_summarizer에서 공통으로 사용하는 함수들
"""

import re
import requests
from typing import List, Tuple, Optional

# 설정
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "exaone3.5:7.8b"
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200


def format_time(seconds: Optional[float]) -> str:
    """초를 MM:SS 형식으로 변환"""
    if seconds is None:
        return "00:00"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def format_time_range(start: Optional[float], end: Optional[float]) -> str:
    """시간 범위 포맷팅 (MM:SS ~ MM:SS)"""
    return f"{format_time(start)} ~ {format_time(end)}"


def call_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
    temperature: float = 0.3,
    timeout: int = 120
) -> str:
    """Ollama API 호출"""
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 2000}
            },
            timeout=timeout
        )
        return response.json().get('response', '')
    except Exception as e:
        print(f"Ollama 호출 오류: {e}")
        return ""


def chunk_transcript(
    transcript: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Tuple[str, str]]:
    """
    전사본을 청크로 분할 (시간 범위 포함)

    Returns:
        List of (time_range, chunk_text) tuples
    """
    chunks = []
    lines = transcript.strip().split('\n')

    current_chunk = []
    current_length = 0
    chunk_start_time = None
    chunk_end_time = None

    for line in lines:
        # 타임스탬프 추출 시도
        time_match = re.match(r'\[(\d+\.?\d*)s', line)
        if time_match:
            timestamp = float(time_match.group(1))
            if chunk_start_time is None:
                chunk_start_time = timestamp
            chunk_end_time = timestamp

        line_length = len(line)

        if current_length + line_length > chunk_size and current_chunk:
            # 청크 저장
            time_range = format_time_range(chunk_start_time, chunk_end_time)
            chunks.append((time_range, '\n'.join(current_chunk)))

            # 오버랩 처리
            overlap_lines = []
            overlap_length = 0
            for prev_line in reversed(current_chunk):
                if overlap_length + len(prev_line) < chunk_overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_length += len(prev_line)
                else:
                    break

            current_chunk = overlap_lines
            current_length = overlap_length
            chunk_start_time = chunk_end_time

        current_chunk.append(line)
        current_length += line_length

    # 마지막 청크
    if current_chunk:
        time_range = format_time_range(chunk_start_time, chunk_end_time)
        chunks.append((time_range, '\n'.join(current_chunk)))

    return chunks


def parse_bullet_list(response: str, max_items: int = 5, max_length: int = 80) -> List[str]:
    """
    LLM 응답에서 불릿 리스트 파싱

    Args:
        response: LLM 응답 텍스트
        max_items: 최대 항목 수
        max_length: 항목당 최대 길이

    Returns:
        파싱된 항목 리스트
    """
    items = []
    for line in response.strip().split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
            item = line.lstrip('-•*').strip()
            if item and len(item) < max_length:
                items.append(item)
    return items[:max_items]


# 카테고리 정의 (회의록용)
CATEGORIES = {
    "현황": ["현재", "진행", "상황", "상태", "현황", "보고", "완료"],
    "배경": ["배경", "이유", "원인", "맥락", "경위", "계기", "이전"],
    "논의": ["논의", "토론", "검토", "협의", "의논", "얘기", "이야기"],
    "문제점": ["문제", "이슈", "어려움", "제약", "부족", "지연", "실패"],
    "의견": ["제안", "의견", "생각", "방안", "아이디어", "고려", "추천"],
    "결의": ["결정", "합의", "결의", "승인", "확정", "가결", "채택"]
}


def infer_category(content: str) -> str:
    """내용에서 카테고리 추론"""
    content_lower = content.lower()

    # 우선순위: 결의 > 문제점 > 의견 > 현황 > 배경 > 논의(기본)
    priority_order = ["결의", "문제점", "의견", "현황", "배경"]

    for category in priority_order:
        if any(kw in content_lower for kw in CATEGORIES[category]):
            return category

    return "논의"  # 기본값
