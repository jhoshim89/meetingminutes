# Meeting Minutes MVP

**Voice Asset MVP** for automated meeting transcription and management.

**Components**: Flutter Web (PWA) + Python PC Worker (STT, speaker diarization)
**Timeline**: 3-4 months MVP with 5-10 beta users
**Tech**: Flutter + Python + Supabase (PostgreSQL + pgvector) + WhisperX + Ollama
**Environment**: **PWA Only** (No Native iOS/Android builds)

---

## Project Structure

| 디렉토리 | 용도 |
|---------|------|
| `flutter_app/` | Flutter Web PWA 소스 (모델, 상태관리, UI 화면) |
| `pc_worker/` | 파이썬 워커 (오디오 처리, STT, DB 연동) |
| `task_plan.md` | 개발 로드맵 (5단계, 상세 내용) |

---

## 개발 환경 설정

### Flutter

```bash
cd flutter_app
flutter pub get
flutter run -d chrome
```

**주요 파일**: `lib/main.dart` (진입점), `lib/providers/` (상태관리), `lib/screens/` (UI)

### PC Worker

```bash
cd pc_worker
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 설정값 입력
python main_worker.py
```

**핵심 흐름**: Supabase 폴링 → 오디오 다운로드 → WhisperX 처리 → 결과 저장
**환경 변수**: `pc_worker/.env.example` 참조

---

## 핵심 정보

| 항목 | 상세 |
|------|------|
| **DB 테이블** | `meetings`, `speakers`, `transcripts`, `templates` (RLS 적용) |
| **백터 검색** | pgvector 확장 사용 |
| **보안** | Supabase RLS + 환경변수 관리 (`.env` 커밋 금지) |
| **현재 단계** | Phase 1.2 (Flutter UI + PC Worker 구조 작성 중) |

---

## 작업 시 참고

**Flutter 화면 추가**: `lib/screens/` → `main.dart` 네비게이션 업데이트
**상태 관리**: `lib/providers/` 수정
**워커 로직**: `pc_worker/audio_processor.py` 수정
**로그 확인**: `pc_worker/logs/`

**상세 정보**:
- 아키텍처, 성능 목표, 테스트 방법 → `task_plan.md`
- 각 모듈의 역할, 의존성 → 파일 주석 참조
