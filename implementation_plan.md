# Implementation Plan - 임시 파일 정리 (Cleanup)

## 문제 정의
프로젝트 루트 디렉토리에 이전 작업의 결과물로 생성된 다수의 Markdown 보고서 및 요약 파일들이 쌓여 있어 디렉토리 구조가 복잡해 보입니다.

## 목표
- 더 이상 필요하지 않은 임시 파일 및 이전 작업 리포트를 삭제하여 프로젝트 루트를 정리합니다.
- `CLAUDE.md`, `task_plan.md` 등 프로젝트 유지에 필수적인 문서는 보존합니다.

## Proposed Changes
### 삭제 대상 파일
다음 파일들을 삭제합니다:
- `CHANGES_SUMMARY.md`
- `FCM_IMPLEMENTATION_SUMMARY.md`
- `FCM_SETUP.md`
- `IMPLEMENTATION_COMPLETE.txt`
- `IMPLEMENTATION_SUMMARY.md`
- `QUICK_REFERENCE.md`
- `QUICK_START_FCM.md`
- `SPEAKER_MANAGER_IMPLEMENTATION.md`
- `SPEAKER_MANAGER_INTEGRATION_GUIDE.md`
- `TASK_2.3_IMPLEMENTATION_REPORT.md`
- `TASK_3_1_COMPLETION_SUMMARY.md`
- `nul` (빈 파일로 보임)

### 보존 (삭제하지 않음)
- `CLAUDE.md` (프로젝트 핵심 문서)
- `task_plan.md` (전체 로드맵)
- `build.sh`, `vercel.json` (배포 설정)
- `.env*`, `.git*` (설정 파일)
- **Current Artifacts**: `implementation_plan.md`, `task.md`, `walkthrough.md` (현재 세션용 - 완료 후 삭제 원하시면 말씀해주세요)


## Verification Plan
- 파일 삭제 명령 실행 후 `ls`를 통해 삭제 여부 확인.

# [Emergent Task] Search & Database Schema Restoration
## 문제 정의
- 사용자 확인 결과 ("하나도 생성안되어있음") 및 코드 분석 결과, 앱 구동에 필수적인 `meetings`, `transcripts`, `speakers` 테이블 및 검색 관련 함수(`hybrid_search_chunks_simple`)를 정의하는 Database Migration 파일이 `supabase/migrations`에 존재하지 않습니다.
- 이로 인해 검색 탭 진입 시 데이터가 없거나 에러가 발생합니다.

## 목표
- 소실된(또는 누락된) Database Schema를 복원합니다. `SupabaseService` 코드에서 참조하는 모든 테이블과 함수를 포함하는 Migration SQL 파일을 생성합니다.

## Proposed Changes
### `d:\Productions\meetingminutes\supabase\migrations\20260111_init_schema.sql` [NEW]
- **Extension**: `vector` 활성화 (Embeddings용)
- **Tables**:
    - `meetings`: 회의 메타데이터
    - `speakers`: 화자 정보
    - `transcripts`: 전체 스크립트
    - `transcript_chunks`: 검색용 청크 (Vector Embedding 포함)
    - `templates`: 회의 템플릿
- **Functions**:
    - `hybrid_search_chunks_simple`: 키워드 + 시맨틱 하이브리드 검색 RPC (또는 초기 텍스트 검색 버전)

## Verification Plan (Search)
- SQL 파일 생성 후 사용자가 Supabase 대시보드에서 쿼리를 실행하거나 로컬에서 마이그레이션을 적용합니다.
- 앱에서 검색 탭 진입 시 "검색 결과 없음"이 정상적으로 뜨는지(에러 없이) 확인합니다.
