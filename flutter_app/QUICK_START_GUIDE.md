# Quick Start Guide - Meeting Minutes App

## Prerequisites
- Flutter SDK 3.0.0+ installed
- Android Studio or Xcode configured
- Supabase account created
- Physical device (recommended for audio testing)

## Setup Steps

### 1. Install Dependencies
```bash
cd D:/Productions/meetingminutes/flutter_app
flutter pub get
```

### 2. Configure Supabase

#### A. Get Credentials
1. Go to your Supabase project dashboard
2. Navigate to Project Settings > API
3. Copy your Project URL and anon/public key

#### B. Update main.dart
Edit `lib/main.dart` (lines 15-18):
```dart
await Supabase.initialize(
  url: 'https://your-project.supabase.co',
  anonKey: 'your-anon-key-here',
);
```

### 3. Create Database Tables

Run these SQL commands in Supabase SQL Editor:

```sql
-- meetings table
CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  duration_seconds INTEGER DEFAULT 0,
  status TEXT DEFAULT 'recording',
  audio_url TEXT,
  transcript_url TEXT,
  summary TEXT,
  speaker_count INTEGER,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_meetings_user_id ON meetings(user_id);
CREATE INDEX idx_meetings_status ON meetings(status);

-- speakers table
CREATE TABLE speakers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  name TEXT,
  embeddings FLOAT[],
  sample_count INTEGER DEFAULT 0,
  is_registered BOOLEAN DEFAULT FALSE,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_speakers_user_id ON speakers(user_id);

-- transcripts table
CREATE TABLE transcripts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  speaker_id UUID REFERENCES speakers(id),
  speaker_name TEXT,
  text TEXT NOT NULL,
  start_time FLOAT NOT NULL,
  end_time FLOAT NOT NULL,
  confidence FLOAT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transcripts_meeting_id ON transcripts(meeting_id);
```

### 4. Configure RLS Policies

```sql
-- Enable RLS
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE speakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;

-- Meetings policies
CREATE POLICY "Users can view own meetings"
  ON meetings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own meetings"
  ON meetings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own meetings"
  ON meetings FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own meetings"
  ON meetings FOR DELETE
  USING (auth.uid() = user_id);

-- Speakers policies
CREATE POLICY "Users can view own speakers"
  ON speakers FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own speakers"
  ON speakers FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own speakers"
  ON speakers FOR UPDATE
  USING (auth.uid() = user_id);

-- Transcripts policies
CREATE POLICY "Users can view transcripts of own meetings"
  ON transcripts FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM meetings
      WHERE meetings.id = transcripts.meeting_id
      AND meetings.user_id = auth.uid()
    )
  );
```

### 5. Create Storage Bucket

1. Go to Storage in Supabase dashboard
2. Create a new bucket named: `meetings`
3. Make it public or configure RLS:

```sql
-- Storage RLS for meetings bucket
CREATE POLICY "Users can upload own audio"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'meetings'
    AND (storage.foldername(name))[1] = 'audio'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );

CREATE POLICY "Users can view own audio"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'meetings'
    AND (storage.foldername(name))[1] = 'audio'
    AND (storage.foldername(name))[2] = auth.uid()::text
  );
```

### 6. Enable Realtime (Optional)

1. Go to Database > Replication in Supabase
2. Enable realtime for:
   - meetings table
   - speakers table
   - transcripts table

### 7. Configure Permissions

#### Android (android/app/src/main/AndroidManifest.xml)
Add before `<application>`:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

#### iOS (ios/Runner/Info.plist)
Add inside `<dict>`:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access to record meetings</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>This app needs photo library access to save recordings</string>
```

### 8. Run the App

```bash
# Check for issues
flutter doctor

# Run on connected device
flutter run

# Or build for release
flutter build apk  # Android
flutter build ios  # iOS
```

## Testing Checklist

### Basic Flow
1. ✓ App launches successfully
2. ✓ Sign in anonymously (Settings > Sign In)
3. ✓ Navigate to Recorder tab
4. ✓ Enter meeting title
5. ✓ Tap record button (grants mic permission)
6. ✓ Recording starts (see timer and visualizer)
7. ✓ Pause and resume work
8. ✓ Stop recording
9. ✓ Upload completes successfully
10. ✓ Meeting appears in Home tab
11. ✓ Tap meeting to view details

### Advanced Features
- [ ] Search meetings
- [ ] Pull to refresh meetings list
- [ ] View meeting details
- [ ] Check speaker manager
- [ ] Register speakers
- [ ] Delete meeting
- [ ] Sign out
- [ ] Dark theme toggle

## Troubleshooting

### "Microphone permission denied"
- **Android**: Settings > Apps > Meeting Minutes > Permissions > Microphone
- **iOS**: Settings > Privacy > Microphone > Meeting Minutes

### "Supabase connection failed"
- Check URL and anon key in main.dart
- Verify internet connection
- Check Supabase project is active

### "Upload failed"
- Check storage bucket exists
- Verify RLS policies are correct
- Check storage quota

### "No meetings showing"
- Verify user is signed in
- Check RLS policies allow SELECT
- Try pull-to-refresh

### "Real-time not working"
- Enable realtime in Supabase dashboard
- Check WebSocket connection
- Verify realtime policies

## Quick Commands

```bash
# Clean build
flutter clean && flutter pub get

# Check for issues
flutter doctor -v

# Run with verbose logging
flutter run -v

# Build release APK
flutter build apk --release

# Analyze code
flutter analyze

# Format code
flutter format lib/

# Generate app bundle
flutter build appbundle
```

## Environment Variables (Optional)

Create `.env` file in root:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

Update pubspec.yaml:
```yaml
dependencies:
  flutter_dotenv: ^5.0.2
```

Update main.dart:
```dart
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await dotenv.load(fileName: ".env");

  await Supabase.initialize(
    url: dotenv.env['SUPABASE_URL']!,
    anonKey: dotenv.env['SUPABASE_ANON_KEY']!,
  );

  runApp(const MyApp());
}
```

## Next Steps

1. **Test thoroughly** on physical devices
2. **Add backend processing** for transcription
3. **Configure push notifications** for completion
4. **Set up analytics** (Firebase recommended)
5. **Prepare app store assets** (icon, screenshots, description)
6. **Submit for review** to App Store / Google Play

## Support

For issues or questions:
- Check IMPLEMENTATION.md for detailed docs
- Review COMPLETE_IMPLEMENTATION_REPORT.md
- Check Supabase logs for backend errors
- Use Flutter DevTools for debugging

## Resources

- [Flutter Docs](https://docs.flutter.dev/)
- [Supabase Docs](https://supabase.com/docs)
- [Provider Docs](https://pub.dev/packages/provider)
- [Material Design 3](https://m3.material.io/)

---

**Quick Setup Time**: ~15 minutes
**Ready to Test**: After step 8
**Production Ready**: After backend integration
