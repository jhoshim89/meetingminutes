# Task Plan: Voice Asset MVP 개발

## Goal
**3-4개월 내에 완전한 회의 자동화 MVP를 배포하여 대학 내 베타 사용자 5-10명으로 검증**

---

## Phases

### Phase 1: 기초 설정 (2-3주) ✅ 완료
- [x] **Supabase 데이터베이스 초기화** ✅
- [x] **Flutter UI 뼈대 구축** ✅ (5,000+ LOC, 30+ 파일)
- [x] **PC Worker 골격 생성** ✅ (2,400+ LOC)

**Agent**: frontend-architect (Sonnet)
**Sub-agent**: devops-architect (Sonnet)
**기간**: 2-3주

---

### Phase 2: AI 엔진 구축 (4-5주) 🔄 80% 완료
- [x] **WhisperX STT + 화자 분리 통합** ✅ (whisperx_engine.py, speaker_diarization.py)
- [x] **음성 임베딩 및 화자 매칭 구현** ✅ (pyannote embedding 추출)
- [x] **모바일-PC Worker 엔드투엔드 연동** ✅ (realtime_worker.py)
- [ ] **정확도 검증 (90%+)** ⏳ 실제 테스트 필요

**Agent**: python-expert (Sonnet) → ai-engineer (Opus)
**Sub-agents**: backend-architect, performance-engineer
**기간**: 4-5주

---

### Phase 3: 자동화 & 템플릿 (2-3주) ✅ 90% 완료
- [x] **회의 템플릿 기능 구현** ✅ (Template API, migrations, CRUD 완료)
- [x] **자동 요약 생성 (Gemma 2)** ✅ (summarizer.py - Ollama + LangChain)
- [x] **Speaker Manager UI 연동** ✅ (speaker_provider.dart, speaker_manager_screen.dart)

**Agent**: backend-architect (Sonnet) + flutter-expert (Sonnet)
**기간**: 2-3주

---

### Phase 4: RAG 검색 (3-4주) ✅ 완료
- [x] **텍스트 청킹 및 임베딩 (BGE-M3)** ✅ (text_chunker.py, embedding_engine.py)
- [x] **pgvector 하이브리드 검색 구현** ✅ (rag_search.py, migrations/002_*)
- [x] **LangChain 재순위화 통합** ✅ (reranker.py)
- [x] **모바일 검색 UI 구현** ✅ (search_screen.dart, search_provider.dart)
- [ ] **검색 정확도 검증 (85%+)** ⏳ 실제 테스트 필요

**Agent**: ai-engineer (Opus)
**Sub-agents**: system-architect, performance-engineer
**기간**: 3-4주

---

### Phase 5: 테스트 & 배포 (2-3주) ⏳ 대기 중
- [ ] **베타 사용자 5-10명 모집** ⏳
- [ ] **TestFlight/Google Play Beta 배포** ⏳
- [ ] **피드백 수집 및 버그 수정** ⏳
- [ ] **App Store/Play Store 정식 배포** ⏳

**Agent**: quality-engineer (Sonnet)
**Sub-agents**: security-engineer, root-cause-analyst
**기간**: 2-3주

---

## Key Questions
1. **WhisperX 정확도**: 한국어 회의 STT 정확도를 90% 이상으로 달성 가능한가?
2. **화자 인식 정확도**: 음성 임베딩으로 80%+ 정확도 달성 가능한가?
3. **RAG 검색 품질**: LangChain 재순위화로 의미 검색 정확도 85% 이상 가능한가?
4. **성능**: 10분 오디오 처리를 2-3분 내에 완료 가능한가?
5. **비용**: Supabase Free tier로 충분한가? (월 2GB, 50K 쿼리)

---

## Decisions Made
- **프론트엔드**: Flutter (Cross-platform 지원)
- **백엔드**: Python + Ollama (로컬 LLM 비용 0원)
- **DB**: Supabase PostgreSQL + pgvector (RLS로 보안)
- **AI 모델**: WhisperX (STT) + Gemma 2 (요약) + BGE-M3 (검색)
- **초기 타겟**: 개인용 1인 (팀 기능은 V2)
- **배포 방식**: 교수님 PC 기반 Worker (클라우드 비용 0원)

---

## Errors Encountered
(작업 진행 중 업데이트)

---

## Status
**🔄 Phase 2-3 거의 완료, 통합 테스트 필요**

### ✅ 완료된 작업
- ✅ Supabase 데이터베이스 생성 및 초기화
- ✅ Supabase MCP 연결
- ✅ Hugging Face 토큰 발급
- ✅ GitHub 저장소 생성
- ✅ 모든 API 키 확보
- ✅ Flutter UI 전체 구현 (5,000+ LOC, 30+ 파일)
- ✅ PC Worker 전체 구현 (2,400+ LOC)
- ✅ WhisperX STT 엔진 구현
- ✅ 화자 분리 (pyannote) 구현
- ✅ 화자 임베딩 추출 구현
- ✅ Ollama 요약 생성 구현
- ✅ 회의 템플릿 CRUD 구현
- ✅ Speaker Manager UI 구현
- ✅ Realtime 알림 구현

### ⏳ 다음 작업
1. **통합 테스트** - 환경 설정 후 전체 파이프라인 테스트
2. **성능 벤치마킹** - STT 90%+, 화자인식 80%+ 검증
3. **Phase 4 시작** - RAG 검색 구현

---

## 개발 팀 배정 (Subagent + Model)

### Phase 1 (2-3주)
```
Task 1.1: Supabase DB 완성
├─ Subagent: devops-architect
├─ Model: sonnet
├─ Duration: 1주
└─ Status: ✅ 완료

Task 1.2: Flutter 프로젝트 & UI 뼈대
├─ Subagent: frontend-architect
├─ Model: sonnet
├─ Duration: 2주
├─ Deliverables:
│  ├─ main.dart (네비게이션) ✅
│  ├─ screens/home_screen.dart ✅
│  ├─ screens/recorder_screen.dart ✅
│  ├─ screens/meeting_detail_screen.dart ✅
│  ├─ screens/speaker_manager_screen.dart ✅
│  ├─ screens/settings_screen.dart ✅
│  ├─ providers/ (6개) ✅
│  ├─ services/ (5개) ✅
│  └─ widgets/ (3개) ✅
└─ Status: ✅ 완료 (5,000+ LOC)

Task 1.3: PC Worker 기본 구조
├─ Subagent: backend-architect
├─ Model: sonnet
├─ Duration: 1주
├─ Deliverables:
│  ├─ main_worker.py (메인 루프) ✅
│  ├─ config.py (환경변수) ✅
│  ├─ requirements.txt ✅
│  ├─ .env.example ✅
│  ├─ supabase_client.py ✅
│  ├─ audio_processor.py ✅
│  ├─ models.py ✅
│  ├─ logger.py ✅
│  └─ exceptions.py ✅
└─ Status: ✅ 완료 (2,400+ LOC)
```

### Phase 2 (4-5주)
```
Task 2.1: WhisperX STT + Diarization
├─ Subagent: python-expert → ai-engineer
├─ Model: sonnet (기본) → opus (복잡한 부분)
├─ Duration: 2주
├─ Subtasks:
│  ├─ 2.1.1: 오디오 전처리 (librosa) ✅
│  ├─ 2.1.2: WhisperX 모델 통합 ✅ (whisperx_engine.py)
│  ├─ 2.1.3: 화자 분리 (pyannote) ✅ (speaker_diarization.py)
│  └─ 2.1.4: 테스트 & 정확도 검증 (90%+) ⏳ 실제 테스트 필요
└─ Status: ✅ 코드 완료, 테스트 대기

Task 2.2: 화자 임베딩 및 매칭
├─ Subagent: ai-engineer
├─ Model: opus
├─ Duration: 1.5주
├─ Subtasks:
│  ├─ 2.2.1: 임베딩 모델 선택 (pyannote/embedding) ✅
│  ├─ 2.2.2: 임베딩 추출 로직 ✅ (extract_speaker_embeddings)
│  ├─ 2.2.3: 코사인 유사도 매칭 ✅ (Flutter speaker_provider.dart)
│  └─ 2.2.4: DB 저장 (speakers 테이블) ✅
└─ Status: ✅ 완료

Task 2.3: 모바일-PC Worker 연동
├─ Subagent: backend-architect
├─ Model: sonnet
├─ Duration: 1.5주
├─ Subtasks:
│  ├─ 2.3.1: 모바일 녹음 및 업로드 ✅ (recorder_provider.dart)
│  ├─ 2.3.2: Supabase Storage 통합 ✅ (storage_service.dart)
│  ├─ 2.3.3: Supabase Realtime 알림 ✅ (realtime_worker.py, realtime_service.dart)
│  └─ 2.3.4: 엔드투엔드 흐름 테스트 ⏳ 실제 테스트 필요
└─ Status: ✅ 코드 완료, 테스트 대기

Task 2.4: 성능 벤치마킹
├─ Subagent: performance-engineer
├─ Model: sonnet
├─ Duration: 1주
├─ Targets:
│  ├─ STT 정확도: 90%+ ⏳
│  ├─ 화자 인식: 80%+ ⏳
│  ├─ 처리 시간: 10분 오디오 → 2-3분 ⏳
│  └─ 메모리: 안정적 (누수 없음) ⏳
└─ Status: ⏳ 대기 중 (코드 완료 후 테스트)
```

### Phase 3 (2-3주)
```
Task 3.1: 회의 템플릿 기능
├─ Subagent: backend-architect + flutter-expert
├─ Model: sonnet
├─ Duration: 1주
├─ Deliverables:
│  ├─ Backend: /templates CRUD API ✅ (supabase_client.py)
│  ├─ DB: templates 테이블 + RLS ✅ (migrations/001_create_templates_table.sql)
│  ├─ Mobile: Template Manager UI ✅ (settings_screen.dart)
│  ├─ Filter: 템플릿별 회의 필터링 ⏳
│  └─ Auto-tagging: 녹음 시 자동 태깅 ⏳ (통합 점 준비됨)
└─ Status: ✅ 90% 완료 (필터링만 남음)

Task 3.2: 자동 요약 생성
├─ Subagent: ai-engineer
├─ Model: opus
├─ Duration: 1주
├─ Subtasks:
│  ├─ 3.2.1: Ollama + Gemma 2 설정 ✅
│  ├─ 3.2.2: 프롬프트 템플릿 작성 ✅ (한국어 최적화)
│  ├─ 3.2.3: LangChain 요약 체인 ✅ (Map-Reduce)
│  └─ 3.2.4: 품질 검증 ⏳ 실제 테스트 필요
└─ Status: ✅ 코드 완료 (summarizer.py)

Task 3.3: Speaker Manager 완성
├─ Subagent: flutter-expert
├─ Model: sonnet
├─ Duration: 1주
├─ Deliverables:
│  ├─ 미등록 화자 리스트 ✅
│  ├─ 음성 샘플 재생 ✅ (audio_player_control.dart)
│  ├─ 이름 입력 및 저장 ✅ (speaker_input_form.dart)
│  └─ 다음 회의 자동 인식 ✅ (autoMatchSpeaker)
└─ Status: ✅ 완료
```

### Phase 4 (3-4주)
```
Task 4.1: RAG 하이브리드 검색
├─ Subagent: ai-engineer
├─ Model: opus
├─ Duration: 1.5주
├─ Subtasks:
│  ├─ 4.1.1: 텍스트 청킹 (5-10초 단위)
│  ├─ 4.1.2: BGE-M3 임베딩
│  ├─ 4.1.3: pgvector 저장 및 IVFFlat 인덱싱
│  ├─ 4.1.4: 키워드 + 의미 검색
│  └─ 4.1.5: 결과 병합 및 정렬
└─ Status: ⏳ 준비 중

Task 4.2: LangChain 재순위화
├─ Subagent: ai-engineer
├─ Model: opus
├─ Duration: 1.5주
├─ Subtasks:
│  ├─ 4.2.1: LangChain Retriever 설정
│  ├─ 4.2.2: Gemma 2 재순위화 로직
│  ├─ 4.2.3: 최종 점수 계산
│  └─ 4.2.4: 정확도 검증 (85%+)
└─ Status: ⏳ 준비 중

Task 4.3: 모바일 검색 UI
├─ Subagent: flutter-expert
├─ Model: sonnet
├─ Duration: 1주
├─ Deliverables:
│  ├─ 검색창 입력
│  ├─ 결과 목록 (관련도 점수 표시)
│  ├─ 음성 재생 버튼
│  └─ 타임스탐프 클릭
└─ Status: ⏳ 준비 중

Task 4.4: 성능 최적화
├─ Subagent: performance-engineer
├─ Model: sonnet
├─ Duration: 1주
├─ Targets:
│  ├─ 검색 응답: 1초 내
│  ├─ 벡터 검색: O(log n) 성능
│  ├─ 메모리: <500MB
│  └─ CPU 사용: <30%
└─ Status: ⏳ 준비 중
```

### Phase 5 (2-3주)
```
Task 5.1: 베타 테스트
├─ Subagent: quality-engineer
├─ Model: sonnet
├─ Duration: 1.5주
├─ Subtasks:
│  ├─ 5.1.1: TestFlight/Google Play Beta 배포
│  ├─ 5.1.2: 베타 사용자 모집 (5-10명)
│  ├─ 5.1.3: 피드백 수집 (1주)
│  └─ 5.1.4: 버그 분류 (긴급/개선)
└─ Status: ⏳ 준비 중

Task 5.2: 버그 수정 & 안정화
├─ Subagent: root-cause-analyst
├─ Model: sonnet
├─ Duration: 1주
├─ Targets:
│  ├─ 크래시 0건
│  ├─ 데이터 손실 0건
│  ├─ 사용자 만족도: 4/5+
│  └─ 모든 긴급 버그 수정
└─ Status: ⏳ 준비 중

Task 5.3: 보안 감사
├─ Subagent: security-engineer
├─ Model: sonnet
├─ Duration: 3-4일
├─ Checks:
│  ├─ 데이터 유출 위험
│  ├─ 인증 이슈
│  ├─ API 보안
│  └─ 로컬 파일 보안
└─ Status: ⏳ 준비 중

Task 5.4: 정식 배포
├─ Subagent: devops-architect
├─ Model: sonnet
├─ Duration: 3-4일
├─ Deliverables:
│  ├─ App Store 심사 통과
│  ├─ Google Play 승인
│  ├─ PC Worker Docker 이미지
│  └─ 설치 가이드 문서화
└─ Status: ⏳ 준비 중
```

---

## 세부 개발 체크리스트 (Phase 1 시작)

### 📱 Flutter 개발 (Task 1.2)
```
[ ] pubspec.yaml 설정
    - [ ] supabase_flutter 추가
    - [ ] provider 추가
    - [ ] http 추가
    - [ ] record 라이브러리 추가

[ ] 프로젝트 구조
    - [ ] lib/screens/ 디렉토리
    - [ ] lib/providers/ 디렉토리
    - [ ] lib/services/ 디렉토리
    - [ ] lib/models/ 디렉토리

[ ] UI 화면 (5개)
    - [ ] home_screen.dart (최근 회의, 검색)
    - [ ] recorder_screen.dart (REC 버튼, 음성 레벨)
    - [ ] meeting_detail_screen.dart (회의록, 타임라인)
    - [ ] speaker_manager_screen.dart (미등록 화자)
    - [ ] settings_screen.dart (회의 템플릿 관리)

[ ] State Management
    - [ ] AuthProvider
    - [ ] MeetingProvider
    - [ ] RecorderProvider
    - [ ] SearchProvider

[ ] Supabase 통합
    - [ ] Supabase 클라이언트 초기화
    - [ ] JWT 토큰 처리
    - [ ] RLS 정책 적용 확인
```

### 💻 PC Worker 개발 (Task 1.3)
```
[ ] 프로젝트 구조
    - [ ] main_worker.py
    - [ ] config.py
    - [ ] requirements.txt
    - [ ] .env.example
    - [ ] logs/ 디렉토리
    - [ ] models/ 디렉토리

[ ] 기본 설정
    - [ ] Supabase 클라이언트 연결
    - [ ] 환경변수 로드 (.env)
    - [ ] GPU/CPU 감지
    - [ ] 로깅 설정

[ ] 메인 루프
    - [ ] 1분마다 pending 상태 회의 조회
    - [ ] 파일 다운로드 큐 구현
    - [ ] 에러 핸들링
    - [ ] 상태 업데이트 로직
```

---

## 총 예상 기간
- **Phase 1**: 2-3주
- **Phase 2**: 4-5주
- **Phase 3**: 2-3주
- **Phase 4**: 3-4주
- **Phase 5**: 2-3주
- **Total**: 13-18주 (약 3-4개월)

---

## 리소스 배정
- **Backend (Python AI)**: 1명 (python-expert, ai-engineer)
- **Frontend (Flutter)**: 1명 (flutter-expert, frontend-architect)
- **DevOps**: 0.5명 (devops-architect)
- **QA/Security**: 0.5명 (quality-engineer, security-engineer)

---

## 상태 업데이트
**🔄 Phase 3 완료 단계 - 통합 테스트 필요**

### 진행률 요약
| Phase | 상태 | 진행률 |
|-------|------|--------|
| Phase 1 | ✅ 완료 | 100% |
| Phase 2 | 🔄 거의 완료 | 80% (테스트 필요) |
| Phase 3 | ✅ 거의 완료 | 90% (필터링만 남음) |
| Phase 4 | ⏳ 대기 중 | 0% |
| Phase 5 | ⏳ 대기 중 | 0% |

### 구현된 코드량
- **Flutter App**: 5,000+ LOC, 30+ 파일
- **PC Worker**: 2,400+ LOC, 15+ 파일
- **문서**: 3,000+ LOC

### 즉시 필요한 작업
1. `.env` 파일 설정 및 환경 구성
2. `pip install -r requirements.txt` 실행
3. `flutter pub get && flutter run` 테스트
4. Supabase 테스트 데이터 생성
5. 전체 파이프라인 통합 테스트
