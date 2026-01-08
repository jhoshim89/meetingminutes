# PC Worker Core Implementation - Task 1.3

## Overview
This is the complete implementation of Task 1.3 (PC Worker Core) for the Meeting Automation MVP. The PC Worker polls Supabase for pending meetings, downloads audio files, preprocesses them, and prepares them for AI processing in Phase 2.

## Architecture

### Components

#### 1. **exceptions.py**
Custom exception hierarchy for structured error handling:
- `PCWorkerException` - Base exception
- `SupabaseError` - Database/storage errors
- `AudioProcessingError` - Audio processing failures
- `RetryExhaustedError` - Retry logic failures

#### 2. **logger.py**
Structured logging with rotation and multiple handlers:
- Console output for real-time monitoring
- File logging with rotation (10MB, 5 backups)
- Separate error log for critical issues
- Structured data support for contextual logging
- Operation lifecycle logging (start, success, failure)

#### 3. **models.py**
Pydantic models for data validation:
- `Meeting` - Meeting metadata with status tracking
- `TranscriptSegment` - Individual transcript segments
- `Transcript` - Complete transcript with segments
- `Speaker` - Speaker profiles with embeddings
- `MeetingSummary` - AI-generated summaries
- `AudioMetadata` - Audio file information
- `SystemInfo` - Worker system information

#### 4. **utils.py**
Utility functions for common operations:
- `get_system_info()` - CPU/GPU availability
- `cleanup_temp_files()` - Remove old temporary files
- `format_timestamp()` - Consistent timestamp formatting
- `validate_audio_file()` - Basic audio validation
- `retry_with_backoff()` - Decorator for retry logic
- File path helpers for audio storage

#### 5. **supabase_client.py**
Singleton Supabase client with comprehensive functionality:
- `get_pending_meetings()` - Query meetings with status='pending'
- `update_meeting_status()` - Update processing status
- `get_meeting_audio_url()` - Get audio file URL
- `download_audio_file()` - Download audio with progress
- `save_transcript()` - Store transcript segments
- `save_speakers()` - Store speaker data
- `save_summary()` - Store AI summaries
- `health_check()` - Connection health monitoring
- Built-in retry logic with exponential backoff

#### 6. **audio_processor.py**
Audio processing pipeline:
- `download_audio()` - Download from Supabase Storage
- `load_audio()` - Load audio with librosa
- `preprocess_audio()` - Resample to 16kHz, normalize
- `validate_audio_format()` - Format validation
- `get_audio_duration()` - Duration extraction
- Supports silence removal (configurable)

#### 7. **main_worker.py**
Main worker orchestration:
- Polling loop for pending meetings
- Status management (pending → processing → completed/failed)
- Complete processing pipeline orchestration
- Graceful shutdown with signal handling
- Automatic temp file cleanup
- Health checks on startup

## Processing Pipeline

### Current Implementation (Phase 1)
1. Poll Supabase for pending meetings
2. Update status to 'processing'
3. Download audio from Supabase Storage
4. Preprocess audio (resample, normalize)
5. Update status to 'completed'
6. Cleanup temporary files

### Future Implementation (Phase 2)
5. Run WhisperX transcription
6. Perform speaker diarization
7. Extract speaker embeddings
8. Match speakers to registered users
9. Generate AI summary with Ollama
10. Save all results to Supabase
11. Update status to 'completed'

## Configuration

### Environment Variables (.env)
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Worker Configuration
WORKER_ID=professor-pc-01
WORKER_NAME=Professor PC Worker
LOG_LEVEL=INFO

# Model Configuration
ENABLE_GPU=true
CUDA_DEVICE=0

# Storage Configuration
AUDIO_TEMP_DIR=./temp_audio
MODEL_CACHE_DIR=./models

# Performance Configuration
MAX_CONCURRENT_JOBS=1
POLLING_INTERVAL_SECONDS=60
```

## Database Schema Requirements

### meetings table
```sql
CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  audio_url TEXT,
  audio_storage_path TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE,
  user_id UUID NOT NULL,
  duration_seconds FLOAT,
  error_message TEXT,
  processed_by TEXT,
  CONSTRAINT meetings_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);
```

### transcript_segments table
```sql
CREATE TABLE transcript_segments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  start_time FLOAT NOT NULL,
  end_time FLOAT NOT NULL,
  speaker_id UUID,
  speaker_label TEXT,
  text TEXT NOT NULL,
  confidence FLOAT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### speakers table
```sql
CREATE TABLE speakers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT,
  user_id UUID,
  embedding JSONB,
  audio_samples TEXT[],
  meeting_ids UUID[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE
);
```

### meeting_summaries table
```sql
CREATE TABLE meeting_summaries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  key_points TEXT[],
  action_items TEXT[],
  topics TEXT[],
  sentiment TEXT,
  model_used TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

## Running the Worker

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the worker
python main_worker.py
```

## Error Handling

### Retry Logic
- Supabase operations: 3 attempts with exponential backoff
- Network failures: Automatic retry with increasing delays
- Corrupted files: Fail immediately with detailed error

### Error Recovery
- Failed meetings marked with status='failed' and error message
- Temporary files cleaned up automatically
- Worker continues processing other meetings
- Graceful shutdown waits for current job completion (60s timeout)

### Logging
- All operations logged with structured data
- Meeting events tracked through lifecycle
- Errors logged with full stack traces
- Separate error log file for critical issues
- Log rotation prevents disk space issues

## Monitoring

### Health Checks
- Supabase connection verified on startup
- System info logged (CPU, GPU, memory)
- Periodic polling logs for activity monitoring

### Metrics (logged)
- Processing time per meeting
- Audio file sizes and durations
- Number of pending meetings found
- Success/failure rates
- Temp file cleanup counts

## Security

### Best Practices
- No hardcoded credentials
- Environment variables for all secrets
- File path sanitization
- Audio file validation before processing
- Proper error messages without exposing internals

## File Structure

```
pc_worker/
├── main_worker.py          # Main worker loop
├── config.py               # Configuration management
├── supabase_client.py      # Supabase integration
├── audio_processor.py      # Audio processing
├── models.py               # Data models
├── exceptions.py           # Custom exceptions
├── logger.py               # Structured logging
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── .env                    # Local environment (gitignored)
├── temp_audio/             # Temporary audio storage
├── models/                 # AI model cache
└── logs/                   # Application logs
```

## Future Enhancements (Phase 2)

### AI Integration
1. **WhisperX Transcription**
   - Load model from cache
   - Transcribe with timestamps
   - Handle long audio files

2. **Speaker Diarization**
   - Use pyannote.audio
   - Identify speaker segments
   - Extract voice embeddings

3. **Speaker Matching**
   - Compare embeddings with registered speakers
   - Update speaker profiles
   - Handle new speakers

4. **Summary Generation**
   - Use Ollama with Gemma 2B
   - Extract key points and action items
   - Analyze sentiment

### Performance Optimizations
- Batch processing for multiple meetings
- GPU utilization for AI models
- Streaming for large audio files
- Caching for frequently accessed data

## Testing

### Manual Testing
```bash
# Test Supabase connection
python -c "from supabase_client import get_supabase_client; print(get_supabase_client().health_check())"

# Test audio processing
python -c "from audio_processor import get_audio_processor; import asyncio; asyncio.run(get_audio_processor().validate_audio_format('test.wav'))"

# Check system info
python -c "from utils import get_system_info; print(get_system_info('test', 'Test'))"
```

### Integration Testing
1. Create test meeting in Supabase with status='pending'
2. Upload test audio file to Supabase Storage
3. Run worker and monitor logs
4. Verify status updates and file cleanup

## Troubleshooting

### Common Issues

**Supabase Connection Failed**
- Check SUPABASE_URL and SUPABASE_KEY in .env
- Verify network connectivity
- Check Supabase project status

**Audio Download Failed**
- Verify audio_url or audio_storage_path in meeting record
- Check Supabase Storage permissions
- Ensure bucket exists and is accessible

**GPU Not Available**
- Install CUDA toolkit
- Verify PyTorch CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
- Set ENABLE_GPU=false to use CPU

**Out of Memory**
- Reduce MAX_CONCURRENT_JOBS
- Process shorter audio files
- Enable GPU if available

## Production Deployment

### Recommendations
1. Use systemd service for auto-restart
2. Monitor logs with log aggregation service
3. Set up alerts for repeated failures
4. Use separate .env for production credentials
5. Run with appropriate resource limits
6. Enable log rotation in production

### Systemd Service Example
```ini
[Unit]
Description=PC Worker for Meeting Processing
After=network.target

[Service]
Type=simple
User=worker
WorkingDirectory=/opt/pc_worker
Environment="PATH=/opt/pc_worker/venv/bin"
ExecStart=/opt/pc_worker/venv/bin/python main_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## License
Proprietary - Meeting Automation MVP

## Support
For issues and questions, contact the development team.
