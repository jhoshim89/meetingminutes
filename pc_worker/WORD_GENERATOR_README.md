# Word Generator - 회의록 Word 문서 생성기

## 개요

`word_generator.py`는 회의록을 전문적인 Word 문서(.docx)로 생성하는 모듈입니다.

## 주요 기능

### 1. 회의록 생성
- 제목, 일시, 참석자, 소요 시간 등 메타데이터 자동 포함
- AI 생성 요약 및 핵심 포인트 삽입
- 전체 대화 내용 (화자별, 타임스탬프 포함)
- 액션 아이템 정리

### 2. AI 분류 카테고리 (0-3개 선택 가능)
- 현황
- 배경
- 논의
- 문제점
- 의견
- 결의

### 3. 한글 폰트 지원
- 기본 폰트: 맑은 고딕
- 커스터마이징 가능

### 4. 프로덕션 레벨 기능
- 파일명 자동 생성 및 sanitization
- 에러 핸들링 및 로깅
- 입력 검증
- 템플릿 생성 기능

## 설치

```bash
pip install python-docx>=1.1.0
```

또는 전체 의존성 설치:

```bash
cd pc_worker
pip install -r requirements.txt
```

## 사용 방법

### 기본 사용

```python
from word_generator import WordGenerator, get_word_generator
from models import Meeting, TranscriptSegment, MeetingSummary

# 1. Generator 초기화
generator = get_word_generator()

# 2. 회의록 생성
output_path = generator.generate_meeting_minutes(
    meeting=meeting,           # Meeting 객체
    transcripts=transcripts,   # List[TranscriptSegment]
    summary=summary           # MeetingSummary 객체
)

print(f"Generated: {output_path}")
```

### 카테고리 포함 생성

```python
# 원하는 카테고리 선택 (0-3개)
selected_categories = ["현황", "논의", "결의"]

output_path = generator.generate_meeting_minutes(
    meeting=meeting,
    transcripts=transcripts,
    summary=summary,
    selected_categories=selected_categories
)
```

### 커스텀 파일명 사용

```python
output_path = generator.generate_meeting_minutes(
    meeting=meeting,
    transcripts=transcripts,
    summary=summary,
    custom_filename="2024_Q1_전략회의"  # .docx 확장자 자동 추가
)
```

### 템플릿 생성

```python
# 빈 템플릿 생성 (참고용)
template_path = generator.generate_template_document(
    title="회의록 템플릿",
    include_all_sections=True
)
```

## 설정

### 출력 디렉토리 설정

```python
from pathlib import Path

generator = WordGenerator(
    output_dir=Path("D:/Meetings/Output"),
    default_font="맑은 고딕",
    default_font_size=11
)
```

기본 출력 디렉토리: `./output/`

### 폰트 커스터마이징

```python
generator = WordGenerator(
    default_font="나눔고딕",
    default_font_size=12,
    title_font_size=20,
    heading_font_size=16
)
```

## 문서 구조

생성되는 Word 문서는 다음 구조를 따릅니다:

```
1. 제목 (회의명)
2. 메타데이터
   - 일시
   - 소요 시간
   - 참석자
3. 요약
4. 핵심 포인트
5. AI 분류 (선택한 카테고리만)
   - 현황
   - 배경
   - 논의
   - 문제점
   - 의견
   - 결의
6. 전체 대화 내용
   - [타임스탬프] 화자: 대화 내용
7. 액션 아이템
```

## 파일명 규칙

자동 생성되는 파일명 형식:

```
회의록_{회의제목}_{날짜}.docx
```

예시:
- `회의록_프로젝트_킥오프_회의_20260116.docx`
- `회의록_주간_팀_미팅_20260116.docx`

특수 문자는 자동으로 `_`로 변환됩니다.

## 테스트

테스트 스크립트 실행:

```bash
cd pc_worker
python test_word_generator.py
```

테스트 항목:
- 기본 문서 생성
- 카테고리 포함 생성
- 템플릿 생성
- 에지 케이스 (특수 문자, 빈 카테고리 등)

## API 레퍼런스

### WordGenerator 클래스

#### `__init__(output_dir, default_font, default_font_size, title_font_size, heading_font_size)`

Word 문서 생성기 초기화

**파라미터:**
- `output_dir` (Path, optional): 출력 디렉토리 (기본: `./output/`)
- `default_font` (str): 기본 폰트 (기본: "맑은 고딕")
- `default_font_size` (int): 기본 폰트 크기 (기본: 11)
- `title_font_size` (int): 제목 폰트 크기 (기본: 18)
- `heading_font_size` (int): 헤딩 폰트 크기 (기본: 14)

#### `generate_meeting_minutes(meeting, transcripts, summary, selected_categories, custom_filename)`

회의록 Word 문서 생성

**파라미터:**
- `meeting` (Meeting): 회의 객체
- `transcripts` (List[TranscriptSegment]): 전사 세그먼트 리스트
- `summary` (MeetingSummary): AI 생성 요약
- `selected_categories` (List[str], optional): 선택한 카테고리 (0-3개)
- `custom_filename` (str, optional): 커스텀 파일명 (확장자 제외)

**반환:**
- `Path`: 생성된 문서 경로

**예외:**
- `DocumentGenerationError`: 문서 생성 실패 시

#### `generate_template_document(title, include_all_sections)`

템플릿 문서 생성

**파라미터:**
- `title` (str): 템플릿 제목 (기본: "회의록 템플릿")
- `include_all_sections` (bool): 모든 섹션 포함 여부 (기본: True)

**반환:**
- `Path`: 생성된 템플릿 경로

### Factory 함수

#### `get_word_generator(output_dir, default_font, default_font_size)`

WordGenerator 인스턴스 생성 (권장)

```python
from word_generator import get_word_generator

generator = get_word_generator(
    output_dir=Path("./output"),
    default_font="맑은 고딕",
    default_font_size=11
)
```

## 에러 처리

```python
from exceptions import DocumentGenerationError

try:
    output_path = generator.generate_meeting_minutes(
        meeting=meeting,
        transcripts=transcripts,
        summary=summary
    )
    print(f"Success: {output_path}")
except DocumentGenerationError as e:
    logger.error(f"Failed to generate document: {e}")
    # 에러 복구 로직
```

## 제약사항

1. **카테고리 제한**: 최대 3개까지만 선택 가능 (더 많이 선택하면 자동으로 처음 3개로 제한)
2. **파일명 길이**: 최대 200자로 제한
3. **특수 문자**: Windows 파일 시스템에서 허용되지 않는 문자는 자동으로 `_`로 변환
4. **폰트 요구사항**: 시스템에 지정한 폰트가 설치되어 있어야 함

## 통합 예시

PC Worker의 메인 처리 흐름에 통합:

```python
from audio_processor import AudioProcessor
from summarizer import get_summarizer
from word_generator import get_word_generator

# 1. 오디오 처리
processor = AudioProcessor()
result = await processor.process_meeting(meeting_id, audio_path)

# 2. 요약 생성
summarizer = get_summarizer()
summary = await summarizer.summarize(
    segments=result.transcript.segments,
    meeting_id=meeting_id
)

# 3. Word 문서 생성
generator = get_word_generator()
output_path = generator.generate_meeting_minutes(
    meeting=meeting,
    transcripts=result.transcript.segments,
    summary=summary,
    selected_categories=["논의", "결의"]  # 사용자 선택
)

logger.info(f"Meeting minutes saved: {output_path}")
```

## 로깅

모든 주요 작업은 로그로 기록됩니다:

```
INFO - WordGenerator initialized. Output dir: D:\Productions\meetingminutes\pc_worker\output
INFO - Generating meeting minutes for: 프로젝트 킥오프 회의
INFO - Meeting minutes generated successfully: D:\Productions\meetingminutes\pc_worker\output\회의록_프로젝트_킥오프_회의_20260116.docx
INFO - File size: 45.32 KB
```

## 참고 자료

- [python-docx 공식 문서](https://python-docx.readthedocs.io/)
- [PC Worker 아키텍처](../task_plan.md)
- [데이터 모델](./models.py)

## 라이선스

프로젝트 라이선스와 동일
