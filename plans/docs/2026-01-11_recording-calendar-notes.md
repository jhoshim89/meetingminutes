# Notes: 녹음 파일 캘린더 연동 분석

## 코드베이스 분석 결과

### RecorderProvider 분석
- **파일**: `flutter_app/lib/providers/recorder_provider.dart`
- **핵심 메서드**: `stopRecording()` (라인 150-200)
- **현재 동작**:
  - 기존 appointment가 있을 때만 `markAsCompleted()` 호출
  - 새 녹음의 경우 캘린더에 추가되지 않음
- **수정 포인트**: 라인 182-189에 else 분기 추가

### AppointmentProvider 분석
- **파일**: `flutter_app/lib/providers/appointment_provider.dart`
- **기존 메서드**:
  - `createAppointment()` - 새 일정 생성
  - `markAsCompleted()` - 일정 완료 처리 (meetingId 연결)
  - `deleteAppointment()` - 일정 삭제
- **추가 필요**:
  - `createAppointmentFromMeeting()` - 녹음 완료 후 자동 생성
  - `deleteAppointmentByMeetingId()` - meeting 삭제 시 연결된 appointment 삭제

### MeetingProvider 분석
- **파일**: `flutter_app/lib/providers/meeting_provider.dart`
- **기존 메서드**: `deleteMeeting()` (라인 200-215) - DB만 삭제
- **문제점**: Storage 오디오 파일, 연결된 appointment 미삭제
- **추가 필요**: `deleteMeetingComplete()` - 완전 삭제 로직

### SchedulerScreen 분석
- **파일**: `flutter_app/lib/screens/scheduler_screen.dart`
- **핵심 위젯**: `_AppointmentCard`
- **현재 표시**: 시간, 제목, 설명, 알림 상태
- **추가 필요**: `meetingId != null` 체크 후 "녹음됨" 배지 표시

## 데이터베이스 구조

### appointments 테이블 주요 필드
```sql
- id (UUID, PK)
- title (VARCHAR 255)
- scheduled_at (TIMESTAMPTZ)
- duration_minutes (INT)
- status (VARCHAR) - 'pending' | 'recording' | 'completed' | 'cancelled' | 'missed'
- meeting_id (UUID, FK meetings) - 녹음된 회의 연결
```

### meetings 테이블 주요 필드
```sql
- id (UUID, PK)
- title (String)
- duration_seconds (int)
- status (String) - 'recording' | 'processing' | 'completed' | 'failed'
- audio_url (String?) - Storage URL
- created_at (TIMESTAMPTZ)
```

## 데이터 흐름

### 현재 흐름 (예약 일정에서 녹음 시작)
```
1. SchedulerScreen에서 일정 선택 → RecorderScreen으로 appointmentId 전달
2. RecorderProvider.startRecording(appointmentId: xxx)
3. 녹음 완료 → stopRecording() → markAsCompleted()
4. appointment.status = 'completed', appointment.meeting_id = meeting.id
```

### 추가할 흐름 (새 녹음)
```
1. RecorderScreen에서 직접 녹음 시작 (appointmentId 없음)
2. RecorderProvider.startRecording()
3. 녹음 완료 → stopRecording()
4. appointmentId가 없으면 → createAppointmentFromMeeting()
5. 새 appointment 생성 (status: 'completed', meeting_id: meeting.id)
```

## UI 참고사항

### 녹음됨 배지 디자인
- 색상: 초록색 (#4CAF50)
- 아이콘: Icons.mic
- 크기: 12-14pt
- 위치: 제목 오른쪽 또는 상태 영역
