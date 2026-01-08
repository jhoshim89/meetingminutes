# Speaker Manager Integration Guide

## Quick Start

### 1. 패키지 설치

```bash
cd flutter_app
flutter pub get
```

### 2. 필수 파일 확인

```
flutter_app/
├── lib/
│   ├── screens/
│   │   └── speaker_manager_screen.dart       # 메인 화면
│   ├── providers/
│   │   └── speaker_provider.dart             # 확장된 상태 관리
│   ├── services/
│   │   ├── audio_service.dart                # 새로운 음성 재생 서비스
│   │   └── supabase_service.dart             # 확장된 Supabase 통합
│   └── widgets/
│       ├── audio_player_control.dart         # 음성 플레이어
│       ├── unregistered_speaker_tile.dart    # 화자 카드
│       └── speaker_input_form.dart           # 입력 폼
└── test/
    └── speaker_manager_test.dart             # 단위 테스트
```

### 3. Supabase 설정

#### 3.1 Storage Bucket 생성

```sql
-- Supabase Dashboard에서 실행
-- Storage > New bucket
CREATE BUCKET meetings;
```

#### 3.2 RLS 정책 설정

```sql
-- 사용자는 자신의 음성 샘플만 접근 가능
CREATE POLICY "Users can access their own audio samples"
ON storage.objects FOR SELECT
USING (bucket_id = 'meetings' AND auth.uid()::text = (storage.path[1]));

-- PC Worker는 모든 음성 샘플 접근 가능
CREATE POLICY "Service role can access all audio"
ON storage.objects FOR ALL
USING (bucket_id = 'meetings');
```

#### 3.3 speakers 테이블 확인

```sql
-- 테이블이 이미 존재한다고 가정
SELECT * FROM speakers LIMIT 5;

-- 필수 컬럼 확인:
-- - id (UUID)
-- - user_id (UUID)
-- - name (TEXT, nullable)
-- - is_registered (BOOLEAN, default: false)
-- - embeddings (VECTOR(384) 또는 768)
-- - sample_count (INTEGER)
-- - created_at (TIMESTAMP)
-- - updated_at (TIMESTAMP)
```

### 4. 음성 샘플 업로드

#### 방법 1: PC Worker에서 자동 업로드

```python
# pc_worker/main_worker.py에서
# 화자 분리 후 음성 샘플 저장

import supabase_flutter
from pathlib import Path

async def upload_speaker_samples(meeting_id: str, speaker_id: str, audio_path: str):
    """화자별 음성 샘플 업로드"""

    sample_path = f"audio/{user_id}/{speaker_id}_sample.wav"

    with open(audio_path, 'rb') as f:
        supabase.storage.from_('meetings').upload(
            sample_path,
            f.read(),
            file_options=FileOptions(content_type='audio/wav')
        )
```

#### 방법 2: Flutter 앱에서 수동 업로드

```dart
// 개발 중 테스트용
Future<void> uploadTestAudioSample(String speakerId, String localPath) async {
    final file = File(localPath);
    final storagePath = 'audio/$userId/${speakerId}_sample.wav';

    await Supabase.instance.client.storage
        .from('meetings')
        .upload(storagePath, file);
}
```

### 5. 앱 초기화

#### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'YOUR_SUPABASE_URL',
    anonKey: 'YOUR_ANON_KEY',
  );

  runApp(const MyApp());
}
```

### 6. 화면 네비게이션

```dart
// main.dart의 MainNavigator에서
final List<Widget> _screens = const [
  HomeScreen(),
  RecorderScreen(),
  SpeakerManagerScreen(),  // 추가됨
  SettingsScreen(),
];

// BottomNavigationBar
BottomNavigationBar(
  items: const [
    BottomNavigationBarItem(
      icon: Icon(Icons.home),
      label: 'Home',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.mic),
      label: 'Recorder',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.person),
      label: 'Speakers',  // 새로운 탭
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.settings),
      label: 'Settings',
    ),
  ],
)
```

## Feature Usage

### 1. 미등록 화자 조회

```dart
final provider = context.read<SpeakerProvider>();

// 미등록 화자 목록 조회
await provider.fetchUnregisteredSpeakers();

// 모든 화자 조회
await provider.fetchSpeakers();

// 미등록 화자 리스트 접근
print(provider.unregisteredSpeakers); // List<SpeakerModel>
```

### 2. 화자 등록

```dart
final success = await provider.registerSpeaker(
  'speaker-uuid-123',
  'John Doe',
);

if (success) {
  print('Speaker registered!');
  // UI가 자동으로 업데이트됨 (notifyListeners)
} else {
  print('Error: ${provider.error}');
}
```

### 3. 음성 샘플 재생

```dart
// Option 1: UnregisteredSpeakerTile 사용 (권장)
UnregisteredSpeakerTile(
  speaker: speaker,
  index: index,
  audioSampleUrl: audioUrl,
  onRegisterPressed: () { ... },
)

// Option 2: AudioPlayerControl 직접 사용
AudioPlayerControl(
  audioUrl: 'https://storage.url/audio/user/speaker_sample.wav',
  showWaveform: true,
)
```

### 4. 자동 화자 매칭

```dart
// Phase 3에서 사용 (현재는 PC Worker에서만)
final embedding = [0.1, 0.2, 0.3, ...]; // 384 or 768 차원

final matchedSpeaker = await provider.autoMatchSpeaker(
  embedding: embedding,
  confidenceThreshold: 0.85, // 85% 이상 신뢰도
);

if (matchedSpeaker != null) {
  print('Matched: ${matchedSpeaker.displayName}');
} else {
  print('No match found, register as new speaker');
}
```

### 5. 신뢰도 점수 계산

```dart
final confidence = await provider.getSpeakerConfidence(
  speakerId: 'speaker-uuid',
  embedding: [0.1, 0.2, 0.3, ...],
);

print('Confidence: $confidence%');
```

## UI Components

### SpeakerManagerScreen

**책임**: 미등록 화자 목록 관리 및 표시

```dart
SpeakerManagerScreen()
  ├── Loading State
  │   └── CircularProgressIndicator
  ├── Error State
  │   ├── Error Icon
  │   ├── Error Message
  │   └── Retry Button
  ├── Empty State
  │   ├── Success Icon
  │   └── "All speakers registered" Message
  └── List State
      └── UnregisteredSpeakerTile (repeated)
```

**Props**: 없음 (stateful)

**Usage**:
```dart
SpeakerManagerScreen()
```

### UnregisteredSpeakerTile

**책임**: 각 미등록 화자 정보 및 음성 샘플 표시

```dart
UnregisteredSpeakerTile(
  speaker: SpeakerModel(...),
  index: 0,
  audioSampleUrl: 'https://...',
  isLoading: false,
  onRegisterPressed: () { ... },
)
```

**Features**:
- Avatar 표시 (S1, S2, ... 숫자)
- 샘플 수 표시
- 음성 샘플 플레이어
- "Register Name" 버튼
- 진입 애니메이션

### AudioPlayerControl

**책임**: 음성 샘플 재생 제어

```dart
AudioPlayerControl(
  audioUrl: 'https://storage.url/audio/speaker.wav',
  showWaveform: true,
  onPlayStateChanged: () { ... },
)
```

**Features**:
- Play/Pause 버튼
- 진행 바 (드래그 가능)
- 시간 표시 (mm:ss)
- Waveform 시각화 (선택사항)
- Stream 기반 상태 업데이트

### SpeakerInputForm

**책임**: 화자 이름 입력 폼

```dart
SpeakerInputForm(
  nameController: TextEditingController(),
  isLoading: false,
  onSave: () { ... },
  onCancel: () { ... },
)
```

**Features**:
- TextFormField (최소 2자, 최대 50자)
- Clear 버튼
- Save/Cancel 버튼
- 유효성 검사
- 로딩 상태 표시

## Error Handling

### 일반적인 에러 케이스

#### 1. 네트워크 에러

```dart
try {
  await provider.fetchUnregisteredSpeakers();
} catch (e) {
  // provider.error에 자동 저장됨
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('Network error: ${provider.error}'),
      backgroundColor: Colors.red,
    ),
  );
}
```

#### 2. 음성 샘플 로딩 실패

```dart
final audioUrl = await provider.getAudioSampleUrl(speakerId);

if (audioUrl == null) {
  // 로딩 실패 또는 중복 요청
  setState(() {
    _audioSampleUrl = null;
  });
}
```

#### 3. 등록 실패

```dart
final success = await provider.registerSpeaker(speakerId, name);

if (!success) {
  // provider.error 확인
  print('Registration error: ${provider.error}');

  // Retry 옵션 제공
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Registration Failed'),
      content: Text(provider.error ?? 'Unknown error'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            _showRegistrationDialog(context, speaker);
            Navigator.pop(context);
          },
          child: const Text('Retry'),
        ),
      ],
    ),
  );
}
```

## Performance Optimization

### 1. 음성 샘플 캐싱

```dart
// 자동으로 캐시됨
final url1 = await provider.getAudioSampleUrl(speakerId); // 네트워크 요청
final url2 = await provider.getAudioSampleUrl(speakerId); // 캐시에서 반환
```

### 2. 중복 로딩 방지

```dart
// 이미 로딩 중인 경우 null 반환
if (provider.isLoadingAudioSample(speakerId)) {
  return null;
}
```

### 3. 메모리 최적화

```dart
// dispose에서 리소스 정리
@override
void dispose() {
  _nameController.dispose();
  super.dispose();
}
```

### 4. 이미지 캐싱 (선택사항)

```dart
// pubspec.yaml에 cached_network_image 추가
import 'package:cached_network_image/cached_network_image.dart';

CachedNetworkImage(
  imageUrl: audioThumbnailUrl,
  cacheManager: CacheManager.instance,
)
```

## Testing

### 단위 테스트 실행

```bash
cd flutter_app
flutter test test/speaker_manager_test.dart
```

### 테스트 커버리지

```bash
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

### 주요 테스트 항목

- [x] 코사인 유사도 계산
- [x] 자동 화자 매칭
- [x] 음성 샘플 URL 캐싱
- [x] 화자 이름 검증
- [x] SpeakerModel JSON 변환
- [x] Provider 상태 관리

## Accessibility Compliance

### WCAG 2.1 AA 준수

- [x] **1.4.3 Contrast (Minimum)**: 텍스트 대비율 4.5:1 (일반 텍스트), 3:1 (큰 텍스트)
- [x] **2.1.1 Keyboard**: 모든 기능 키보드로 접근 가능
- [x] **2.5.5 Target Size**: 최소 44x44px (터치 대상)
- [x] **3.2.2 On Input**: 입력 시 예상 가능한 동작
- [x] **3.3.1 Error Identification**: 에러 메시지 명확함
- [x] **3.3.2 Labels or Instructions**: 필드 레이블 제공
- [x] **4.1.3 Status Messages**: 상태 변화 공지

### Screen Reader 지원

```dart
// Semantic 라벨 추가
Tooltip(
  message: 'Play audio sample',
  child: IconButton(
    icon: const Icon(Icons.play_arrow),
    onPressed: () { ... },
  ),
)

// Meaningful text
Text(
  'Speaker ID: ${speaker.id}',
  semanticsLabel: 'Speaker identifier ${speaker.id}',
)
```

## Troubleshooting

### Issue 1: 음성 샘플이 재생되지 않음

**원인**: Storage path가 잘못되었거나 권한 문제

**해결책**:
1. Supabase Dashboard에서 파일 존재 확인
2. Path 형식 확인: `audio/{user_id}/{speaker_id}_sample.wav`
3. RLS 정책 확인

### Issue 2: 화자 목록이 비어있음

**원인**: Supabase 쿼리 실패 또는 네트워크 문제

**해결책**:
1. `provider.error` 확인
2. Supabase credentials 확인
3. 인터넷 연결 확인
4. Refresh 버튼 클릭

### Issue 3: Dark mode에서 텍스트가 보이지 않음

**원인**: 색상 대비 부족

**해결책**:
1. `Theme.of(context).brightness` 확인
2. Colors.grey 대신 Colors.grey[300] 사용
3. 명시적으로 색상 지정

## Future Enhancements

### Phase 3+

1. **Auto-Confirm Dialog**
   - 80%+ 신뢰도일 때 자동 제안
   - "Confirm" 버튼으로 즉시 등록

2. **Batch Operations**
   ```dart
   await provider.registerMultipleSpeakers([
     (speakerId1, 'John'),
     (speakerId2, 'Jane'),
   ]);
   ```

3. **Speaker History**
   - 등록 히스토리 표시
   - 이전 이름 제안

4. **Voice Print Visualization**
   - 스펙트로그램 표시
   - 음성 특성 시각화

5. **Offline Support**
   - 로컬 캐시
   - 동기화 큐

## Resources

- [Flutter Docs](https://flutter.dev)
- [Provider Package](https://pub.dev/packages/provider)
- [just_audio](https://pub.dev/packages/just_audio)
- [Supabase Flutter](https://supabase.com/docs/reference/dart)
- [Material Design 3](https://m3.material.io/)

## Support

문제가 발생하면:

1. 로그 확인: `flutter logs`
2. Supabase 상태 확인
3. 캐시 정리: `flutter clean && flutter pub get`
4. 장치 재시작
