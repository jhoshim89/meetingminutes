# Meeting Minutes MVP

회의 음성을 자동으로 전사하고 요약하는 시스템.

---

## Tech Stack

| 레이어 | 기술 |
|--------|------|
| Frontend | Flutter Web (PWA) |
| Backend | Python PC Worker + Supabase |
| STT | WhisperX (large-v3-turbo) |
| 요약 | EXAONE 3.5 (Ollama) |
| DB | PostgreSQL + pgvector |

---

## Project Structure

| 디렉토리 | 용도 |
|---------|------|
| `flutter_app/` | Flutter Web PWA |
| `pc_worker/` | STT + 요약 워커 |
| `data/` | 테스트 오디오 파일 |

---

## 개발 명령어

```bash
# Flutter
cd flutter_app && flutter pub get && flutter run -d chrome

# PC Worker
cd pc_worker && pip install -r requirements.txt && python main_worker.py
```

---

## AI 모델 설정

### WhisperX (한국어 최적화)

| 파라미터 | 기본값 | 한국어 권장 |
|----------|--------|-------------|
| vad_onset | 0.5 | **0.1** |
| vad_offset | 0.363 | **0.1** |
| model | - | large-v3-turbo |

**설정 파일**: `pc_worker/whisperx_engine.py:26-41`

### LLM 요약

| 모델 | 한국어 성능 | 비고 |
|------|------------|------|
| EXAONE 3.5 (7.8B) | ✅ 우수 | 한국어 특화, 환각 적음 |
| Gemma3 (4.3B) | ❌ 나쁨 | 환각 심함 |
| Phi4 (14.7B) | ⚠️ 보통 | 형식 준수 미흡 |

**요약 프롬프트** (범용):
```
아래 회의 전사본을 주제별로 빠짐없이 상세하게 요약해주세요.
없는 내용을 만들어내지 마세요.
```

---

## E2E 파이프라인

```
오디오 → WhisperX (VAD 0.1) → 전사본 → EXAONE 3.5 → 요약
         83.5% 정확도           23초, 8개 주제 추출
```

---

## 현재 상태

| 단계 | 상태 |
|------|------|
| Phase 1: 기초 설정 | ✅ 완료 |
| Phase 2: AI 엔진 | ✅ E2E 검증 완료 |
| Phase 3: 자동화 | ⏳ 진행 중 |
| Phase 4: RAG 검색 | ⏳ 대기 |
| Phase 5: 배포 | ⏳ 대기 |

**상세 로드맵**: `task_plan.md`

---

## 주요 파일

| 파일 | 역할 |
|------|------|
| `pc_worker/whisperx_engine.py` | STT 엔진 (VAD 설정 포함) |
| `pc_worker/summarizer.py` | LLM 요약 |
| `pc_worker/config.py` | 환경 설정 |
| `pc_worker/output/` | 테스트 결과물 |
