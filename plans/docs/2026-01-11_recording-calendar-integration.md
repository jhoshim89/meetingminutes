# Task Plan: 녹음 파일 캘린더 연동 및 관리 기능

## Goal
녹음 완료 시 캘린더에 자동 추가, 홈/검색에서 녹음 파일 조회, 삭제 기능 구현

## Phases
- [ ] Phase 1: SupabaseService 수정 - createAppointment 파라미터 추가
- [ ] Phase 2: AppointmentProvider 수정 - 새 메서드 추가
- [ ] Phase 3: RecorderProvider 수정 - 녹음 완료 시 캘린더 자동 추가
- [ ] Phase 4: MeetingProvider 수정 - 완전 삭제 로직 구현
- [ ] Phase 5: SchedulerScreen 수정 - "녹음됨" 배지 UI
- [ ] Phase 6: MeetingDetailScreen 수정 - 삭제 다이얼로그 개선
- [ ] Phase 7: HomeScreen 수정 - 스와이프 삭제 추가
- [ ] Phase 8: 통합 테스트 및 검증

## Key Questions
1. ~~캘린더에 어떤 정보를 표시할지?~~ → **녹음 제목 + 녹음 시간**
2. ~~기존 예약 일정에서 녹음 시 중복 처리?~~ → **모든 녹음을 캘린더에서 확인 가능하게**

## Requirements Summary
| 기능 | 현재 상태 | 필요 작업 |
|------|----------|----------|
| 녹음 → 캘린더 추가 | 예약 일정만 연결됨 | 모든 녹음에 appointment 자동 생성 |
| 홈에서 녹음 목록 | 이미 구현됨 | 없음 |
| 검색에서 회의 조회 | 이미 구현됨 | 없음 |
| 녹음 파일 삭제 | 부분적 (DB만 삭제) | Storage + Appointment 함께 삭제 |

## Critical Files

### 수정 대상 파일
| 파일 경로 | 수정 내용 |
|----------|----------|
| `lib/providers/recorder_provider.dart` | stopRecording()에 자동 appointment 생성 로직 (라인 182-189) |
| `lib/providers/appointment_provider.dart` | createAppointmentFromMeeting(), deleteAppointmentByMeetingId() 추가 |
| `lib/providers/meeting_provider.dart` | deleteMeetingComplete() 추가 (라인 200 이후) |
| `lib/services/supabase_service.dart` | createAppointment()에 status, meetingId 파라미터 추가 |
| `lib/screens/scheduler_screen.dart` | _AppointmentCard에 녹음됨 배지 UI |
| `lib/screens/meeting_detail_screen.dart` | 삭제 다이얼로그 → deleteMeetingComplete 호출 |
| `lib/screens/home_screen.dart` | MeetingCard → Dismissible로 감싸기 |

## Implementation Details

### Phase 1: SupabaseService 수정
```dart
Future<AppointmentModel?> createAppointment({
  // 기존 파라미터...
  String status = 'pending',  // 추가
  String? meetingId,          // 추가
}) async {
  // insert 시 status, meeting_id 포함
}
```

### Phase 2: AppointmentProvider 수정
```dart
/// 녹음 완료된 meeting으로부터 캘린더 항목 생성
Future<AppointmentModel?> createAppointmentFromMeeting({
  required MeetingModel meeting,
}) async {
  return await _supabaseService.createAppointment(
    title: meeting.title,
    scheduledAt: meeting.createdAt,
    durationMinutes: (meeting.durationSeconds / 60).ceil(),
    status: 'completed',
    meetingId: meeting.id,
    autoRecord: false,
  );
}

/// meeting_id로 appointment 삭제
Future<bool> deleteAppointmentByMeetingId(String meetingId) async {
  final appointment = _appointments.firstWhereOrNull(
    (a) => a.meetingId == meetingId
  );
  if (appointment != null) {
    return await deleteAppointment(appointment.id);
  }
  return true;
}
```

### Phase 3: RecorderProvider 수정
```dart
// stopRecording() 라인 182-189 수정
if (_currentAppointmentId != null && appointmentProvider != null) {
  await appointmentProvider.markAsCompleted(_currentAppointmentId!, meetingId: meeting.id);
} else if (appointmentProvider != null) {
  // 새 녹음인 경우 - 캘린더에 자동 추가
  await appointmentProvider.createAppointmentFromMeeting(meeting: meeting);
}
```

### Phase 4: MeetingProvider 수정
```dart
Future<bool> deleteMeetingComplete(String meetingId, {AppointmentProvider? appointmentProvider}) async {
  try {
    final meeting = await _supabaseService.getMeetingById(meetingId);

    // 1. Storage 오디오 파일 삭제
    if (meeting.audioUrl != null) {
      await _supabaseService.deleteAudio(meeting.audioUrl!);
    }

    // 2. Meeting 레코드 삭제 (transcripts cascade)
    await _supabaseService.deleteMeeting(meetingId);

    // 3. 연결된 Appointment 삭제
    if (appointmentProvider != null) {
      await appointmentProvider.deleteAppointmentByMeetingId(meetingId);
    }

    // 4. 로컬 상태 업데이트
    _meetings.removeWhere((m) => m.id == meetingId);
    notifyListeners();
    return true;
  } catch (e) {
    return false;
  }
}
```

### Phase 5: SchedulerScreen "녹음됨" 배지
```dart
// _AppointmentCard 내부
if (appointment.meetingId != null)
  Container(
    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: Colors.green.withOpacity(0.1),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: Colors.green),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.mic, size: 14, color: Colors.green),
        SizedBox(width: 4),
        Text('녹음됨', style: TextStyle(fontSize: 12, color: Colors.green)),
      ],
    ),
  ),
```

## Decisions Made
- **녹음 표시 방식**: 녹음 제목 + 시간으로 표시
- **중복 처리**: 예약 일정에서 시작해도, 새 녹음이어도 모두 캘린더에서 확인 가능
- **삭제 범위**: Meeting + Storage 오디오 + Appointment 모두 삭제

## Errors Encountered
- (구현 중 추가 예정)

## Verification Plan
1. **녹음 → 캘린더 연동**: 새 녹음 → SchedulerScreen에서 해당 날짜 확인
2. **녹음됨 배지**: 캘린더 항목에 초록색 마이크 아이콘 표시 확인
3. **삭제 기능**: MeetingDetailScreen/HomeScreen에서 삭제 → 캘린더 항목도 함께 제거 확인
4. **회귀 테스트**: 기존 예약 일정에서 녹음 시작 → 완료 flow 정상 작동 확인

## Status
**COMPLETED** - 모든 구현 완료 (2026-01-11)

## Completed Changes

### Phase 1: SupabaseService ✅
- `createAppointment()`에 `status`, `meetingId` 파라미터 추가
- 파일: `lib/services/supabase_service.dart` (라인 594-622)

### Phase 2: AppointmentProvider ✅
- `createAppointmentFromMeeting()` 메서드 추가
- `deleteAppointmentByMeetingId()` 메서드 추가
- 파일: `lib/providers/appointment_provider.dart` (라인 305-363)

### Phase 3: RecorderProvider ✅
- `stopRecording()`에 캘린더 자동 추가 로직 구현
- 새 녹음 시 `createAppointmentFromMeeting()` 호출
- 파일: `lib/providers/recorder_provider.dart` (라인 182-198)

### Phase 4: MeetingProvider ✅
- `deleteMeetingComplete()` 메서드 추가
- Storage 오디오 + DB + Appointment 모두 삭제
- 파일: `lib/providers/meeting_provider.dart` (라인 218-260)

### Phase 5: SchedulerScreen ✅
- "녹음됨" 배지 UI 추가 (초록색 마이크 아이콘)
- 녹음된 일정 탭 시 MeetingDetailScreen으로 이동
- 파일: `lib/screens/scheduler_screen.dart`

### Phase 6: MeetingDetailScreen ✅
- 삭제 다이얼로그 개선 (삭제 대상 명시)
- `deleteMeetingComplete()` 사용으로 완전 삭제
- 로딩 인디케이터 추가
- 파일: `lib/screens/meeting_detail_screen.dart`

### Phase 7: HomeScreen ✅
- Dismissible 위젯으로 스와이프 삭제 추가
- 삭제 확인 다이얼로그 추가
- 파일: `lib/screens/home_screen.dart`

## Verification Needed
1. `flutter analyze` 실행하여 컴파일 오류 확인
2. 앱 실행하여 기능 테스트:
   - 새 녹음 → 캘린더에 자동 추가 확인
   - 캘린더에서 "녹음됨" 배지 표시 확인
   - 스와이프 삭제 동작 확인
   - 상세 화면에서 삭제 동작 확인
