# Flutter Meeting Minutes App - Implementation Guide

## Overview
This is a professional Flutter mobile application for recording, transcribing, and managing meeting minutes with AI-powered speaker identification. The app integrates with Supabase for backend services and uses Provider for state management.

## Project Structure

```
lib/
├── main.dart                           # App entry point with provider setup
├── models/                             # Data models
│   ├── meeting_model.dart              # Meeting entity
│   ├── speaker_model.dart              # Speaker entity
│   └── transcript_model.dart           # Transcript line entity
├── providers/                          # State management
│   ├── auth_provider.dart              # JWT auth & user session
│   ├── meeting_provider.dart           # Meetings CRUD operations
│   ├── recorder_provider.dart          # Recording state & progress
│   ├── search_provider.dart            # Search functionality
│   └── speaker_provider.dart           # Speaker management
├── services/                           # Business logic
│   ├── supabase_service.dart           # Supabase API client
│   └── recording_service.dart          # Audio recording service
└── screens/                            # UI screens
    ├── home_screen.dart                # Meetings list
    ├── recorder_screen.dart            # Recording interface
    ├── meeting_detail_screen.dart      # Meeting details & transcript
    ├── speaker_manager_screen.dart     # Speaker registration
    └── settings_screen.dart            # App settings
```

## Features Implemented

### 1. State Management (Provider)
- **AuthProvider**: Manages JWT tokens and user authentication
- **MeetingProvider**: Handles meeting CRUD operations
- **RecorderProvider**: Manages recording state, duration, and audio amplitude
- **SearchProvider**: Implements debounced search with real-time results
- **SpeakerProvider**: Manages speaker registration and unregistered speakers

### 2. Data Models
- **MeetingModel**: Complete meeting data structure with helpers for formatting
- **SpeakerModel**: Speaker data with embeddings and registration status
- **TranscriptModel**: Transcript line with speaker identification and timestamps

### 3. Supabase Integration
- **Authentication**: Anonymous sign-in support
- **Database Operations**: Full CRUD for meetings, speakers, and transcripts
- **Storage**: Audio file upload to Supabase Storage
- **RLS Support**: Row-level security with user context
- **Error Handling**: Comprehensive error handling with retry logic

### 4. Recording Service
- **Audio Recording**: High-quality audio recording (128 kbps AAC)
- **Real-time Monitoring**: Duration tracking and amplitude visualization
- **Pause/Resume**: Full control over recording state
- **File Management**: Automatic file path generation and cleanup

### 5. User Interface
- **Home Screen**:
  - Meetings list with search functionality
  - Pull-to-refresh
  - Status badges (recording, processing, completed, failed)
  - Navigation to meeting details

- **Recorder Screen**:
  - Visual recording indicator with amplitude animation
  - Title input for meetings
  - Pause/resume/cancel controls
  - Upload progress indicator
  - Success/error feedback

- **Meeting Detail Screen**:
  - Meeting metadata (date, duration, speakers)
  - AI-generated summary
  - Full transcript with speaker identification
  - Delete meeting functionality

- **Speaker Manager Screen**:
  - List of unregistered speakers
  - Speaker registration with name input
  - Real-time feedback
  - Empty state when all speakers registered

- **Settings Screen**:
  - User profile display
  - Meeting templates (coming soon)
  - Audio quality settings
  - About information
  - Sign out functionality

## Setup Instructions

### 1. Prerequisites
- Flutter SDK 3.0.0 or higher
- Dart SDK
- Android Studio / Xcode for mobile development
- Supabase account and project

### 2. Install Dependencies
```bash
cd flutter_app
flutter pub get
```

### 3. Configure Supabase
Update `lib/main.dart` with your Supabase credentials:

```dart
await Supabase.initialize(
  url: 'YOUR_SUPABASE_URL',
  anonKey: 'YOUR_ANON_KEY',
);
```

### 4. Database Schema
Create the following tables in Supabase:

#### meetings
```sql
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
```

#### speakers
```sql
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
```

#### transcripts
```sql
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
```

### 5. Storage Bucket
Create a storage bucket named `meetings` for audio files:
- Make it public if you want direct access
- Configure RLS policies for user-specific access

### 6. Run the App
```bash
flutter run
```

## Best Practices Implemented

### Code Quality
- Const constructors where possible
- Proper null safety
- Type-safe models with fromJson/toJson
- Clean separation of concerns

### State Management
- Provider pattern for reactive UI updates
- Proper state initialization in initState
- Resource cleanup in dispose methods
- Stream-based updates for real-time data

### Error Handling
- Try-catch blocks in all async operations
- User-friendly error messages
- Retry logic for failed operations
- SnackBar notifications for feedback

### Performance
- Debounced search (500ms delay)
- Efficient list rendering with ListView.builder
- Proper async/await usage
- Stream subscriptions cleanup

### User Experience
- Loading indicators during async operations
- Empty states with helpful messages
- Confirmation dialogs for destructive actions
- Pull-to-refresh functionality
- Visual feedback for recording state

## API Usage Examples

### Creating a Meeting
```dart
final meeting = await context.read<MeetingProvider>().createMeeting(
  title: 'My Meeting',
  audioUrl: 'https://...',
);
```

### Starting Recording
```dart
await context.read<RecorderProvider>().startRecording(
  title: 'Meeting Title',
);
```

### Searching Meetings
```dart
context.read<SearchProvider>().setQuery('search term');
```

### Registering a Speaker
```dart
await context.read<SpeakerProvider>().registerSpeaker(
  speakerId,
  'John Doe',
);
```

## Known Limitations

1. **Audio Format**: Currently only supports AAC/M4A format
2. **Anonymous Auth**: Only anonymous authentication is implemented
3. **Offline Support**: No offline mode yet
4. **Background Recording**: Recording stops when app is backgrounded
5. **Audio Processing**: Backend processing is required for transcription

## Next Steps

### Priority Features
1. Implement email/social authentication
2. Add background recording support
3. Implement offline mode with local database
4. Add audio playback controls
5. Implement meeting export (PDF, TXT)

### Future Enhancements
1. Real-time transcription during recording
2. Multi-language support
3. Meeting templates with custom fields
4. Calendar integration
5. Push notifications for processing completion

## Troubleshooting

### Permission Issues
- Ensure microphone permissions are granted in device settings
- Check AndroidManifest.xml / Info.plist for permission declarations

### Supabase Connection Errors
- Verify URL and anon key are correct
- Check internet connectivity
- Verify RLS policies allow user access

### Recording Issues
- Test on physical device (emulators may have limited audio support)
- Check storage permissions
- Verify sufficient storage space

## Support

For issues or questions:
1. Check the error messages in console
2. Verify Supabase setup is complete
3. Ensure all dependencies are installed
4. Review the implementation documentation

## License

This is an MVP project for Voice Asset - Meeting Automation.
