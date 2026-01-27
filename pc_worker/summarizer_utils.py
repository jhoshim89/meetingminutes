"""
Summarizer 공통 유틸리티 모듈
============================
hybrid_summarizer, natural_summarizer에서 공통으로 사용하는 함수들
"""

import os
import re
import time
import logging
import requests
from typing import List, Tuple, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 설정 - 환경 변수에서 읽기 (Docker 호환)
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = "exaone3.5:7.8b"
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class OllamaConnectionError(Exception):
    """Ollama 서버 연결 실패"""
    pass


class OllamaEmptyResponseError(Exception):
    """Ollama가 빈 응답 반환"""
    pass


def check_ollama_health(ollama_url: str = OLLAMA_URL, timeout: int = 5) -> bool:
    """
    Ollama 서버 헬스체크

    Returns:
        True if server is healthy, False otherwise
    """
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama 헬스체크 실패: {e}")
        return False


def ensure_ollama_ready(
    ollama_url: str = OLLAMA_URL,
    model: str = DEFAULT_MODEL,
    timeout: int = 10
) -> bool:
    """
    Ollama 서버와 모델이 준비되었는지 확인

    Returns:
        True if ready, raises OllamaConnectionError if not
    """
    # 1. 서버 체크
    if not check_ollama_health(ollama_url):
        raise OllamaConnectionError(
            f"Ollama 서버에 연결할 수 없습니다: {ollama_url}\n"
            "ollama serve 명령어로 서버를 시작하세요."
        )

    # 2. 모델 체크
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=timeout)
        models = [m['name'] for m in response.json().get('models', [])]

        # 모델명 매칭 (태그 포함/미포함 모두 체크)
        model_base = model.split(':')[0]
        if not any(model_base in m for m in models):
            raise OllamaConnectionError(
                f"모델 '{model}'이 설치되지 않았습니다.\n"
                f"ollama pull {model} 명령어로 설치하세요.\n"
                f"설치된 모델: {models}"
            )

        logger.info(f"Ollama 준비 완료: {ollama_url}, 모델: {model}")
        return True

    except requests.exceptions.RequestException as e:
        raise OllamaConnectionError(f"Ollama 서버 통신 오류: {e}")


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
    timeout: int = 120,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
    raise_on_empty: bool = True
) -> str:
    """
    Ollama API 호출 (재시도 및 검증 로직 포함)

    Args:
        prompt: LLM에 전달할 프롬프트
        model: 사용할 모델명
        ollama_url: Ollama 서버 URL
        temperature: 생성 온도 (0.0~1.0)
        timeout: 요청 타임아웃 (초)
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 대기 시간 (초)
        raise_on_empty: 빈 응답 시 예외 발생 여부

    Returns:
        LLM 응답 텍스트

    Raises:
        OllamaConnectionError: 서버 연결 실패
        OllamaEmptyResponseError: 빈 응답 (raise_on_empty=True일 때)
    """
    last_error = None

    for attempt in range(max_retries):
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

            # HTTP 에러 체크
            response.raise_for_status()

            result = response.json().get('response', '')

            # 빈 응답 체크
            if not result or not result.strip():
                logger.warning(
                    f"Ollama 빈 응답 (시도 {attempt + 1}/{max_retries}), "
                    f"프롬프트 길이: {len(prompt)}자"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                elif raise_on_empty:
                    raise OllamaEmptyResponseError(
                        f"Ollama가 {max_retries}회 시도 후에도 빈 응답 반환. "
                        f"모델: {model}, 프롬프트 길이: {len(prompt)}자"
                    )
                else:
                    return ""

            # 성공
            if attempt > 0:
                logger.info(f"Ollama 응답 성공 (시도 {attempt + 1}회)")

            return result

        except requests.exceptions.Timeout:
            last_error = f"타임아웃 ({timeout}초)"
            logger.warning(f"Ollama 타임아웃 (시도 {attempt + 1}/{max_retries})")

        except requests.exceptions.ConnectionError as e:
            last_error = f"연결 실패: {e}"
            logger.error(f"Ollama 연결 실패: {e}")
            # 연결 에러는 서버가 꺼져있을 가능성이 높으므로 즉시 실패
            raise OllamaConnectionError(
                f"Ollama 서버에 연결할 수 없습니다: {ollama_url}\n"
                "ollama serve 명령어로 서버를 시작하세요."
            )

        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP 에러: {e}"
            logger.warning(f"Ollama HTTP 에러 (시도 {attempt + 1}/{max_retries}): {e}")

        except Exception as e:
            last_error = str(e)
            logger.error(f"Ollama 예기치 않은 오류: {e}")

        # 재시도 전 대기
        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    # 모든 재시도 실패
    raise OllamaConnectionError(
        f"Ollama 호출 실패 ({max_retries}회 재시도 후): {last_error}"
    )


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
