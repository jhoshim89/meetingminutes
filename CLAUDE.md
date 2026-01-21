# Meeting Minutes MVP

회의 음성을 자동으로 전사하고 요약하여 **회의록 DOCX**를 생성하는 시스템.

---

## Tech Stack

| 레이어 | 기술 |
|--------|------|
| Frontend | Flutter Web (PWA) |
| Backend | Python PC Worker + Supabase |
| STT | WhisperX (large-v3-turbo) |
| 요약 | EXAONE 3.5 (Ollama) - 하이브리드 요약 |
| DOCX | docx-js (Node.js) |
| DB | PostgreSQL + pgvector |

---

## Project Structure

| 디렉토리 | 용도 |
|---------|------|
| `flutter_app/` | Flutter Web PWA |
| `pc_worker/` | STT + 요약 + 회의록 생성 |
| `data/` | 테스트 오디오/회의록 파일 |
| `docs/` | 워크플로우 문서 |

---

## 개발 명령어

```bash
# 전체 파이프라인 (오디오 → 회의록)
cd pc_worker && python meeting_pipeline.py ../data/회의.m4a

# 요약만 (전사본 → 요약)
python hybrid_summarizer.py ../data/전사본.txt -f docx

# Flutter
cd flutter_app && flutter run -d chrome
```

---

## 회의록 파이프라인

```
🎤 오디오 (.m4a, .mp3, .wav)
      │
      ▼
  WhisperX STT ──→ 전사본.txt
      │
      ▼
  HybridSummarizer ──→ 요약.txt + 회의록.json
      │
      ▼
  docx-js ──→ 회의록.docx
```

**상세 워크플로우**: `docs/WORKFLOW.md`

---

## 주요 파일

| 파일 | 역할 |
|------|------|
| `pc_worker/meeting_pipeline.py` | **CLI 파이프라인** (로컬 오디오 처리) |
| `pc_worker/main_worker.py` | **서버 워커** (Supabase 연동) |
| `pc_worker/hybrid_summarizer.py` | 통합 요약기 (유일한 요약기) |
| `pc_worker/summarizer_utils.py` | 요약기 공통 유틸리티 |
| `pc_worker/whisperx_engine.py` | STT 엔진 (VAD 설정) |
| `pc_worker/generate_minutes_docx.js` | DOCX 생성 (Node.js) |

---

## AI 모델 설정

### WhisperX

| 파라미터 | 권장값 | 비고 |
|----------|--------|------|
| model | large-v3-turbo | |
| vad_onset | 0.5 | 기본값 권장 |
| vad_offset | 0.363 | |

**설정**: `pc_worker/whisperx_engine.py:26-41`

### LLM (Ollama)

| 모델 | 한국어 | 비고 |
|------|--------|------|
| EXAONE 3.5 (7.8B) | ✅ 우수 | **권장** |
| Gemma3 | ❌ 환각 | |
| Phi4 | ⚠️ 보통 | |

---

## 지원 오디오 형식

| 형식 | 지원 | 비고 |
|------|------|------|
| `.m4a` | ✅ | 아이폰 녹음 |
| `.mp3` | ✅ | |
| `.wav` | ✅ | |
| 기타 | ✅ | ffmpeg 지원 형식 |

비-WAV 형식은 **ffmpeg로 자동 변환** (`whisperx_engine.py:258-291`)

---

## 현재 상태

| 단계 | 상태 |
|------|------|
| Phase 1: 기초 설정 | ✅ 완료 |
| Phase 2: AI 엔진 | ✅ 완료 |
| Phase 3: 회의록 생성 | ✅ 완료 |
| Phase 4: RAG 검색 | ⏳ 대기 |
| Phase 5: 배포 | ⏳ 대기 |
