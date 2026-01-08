# PC Worker Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PC Worker System                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────────────────────────────┐
│   Supabase   │◄────────┤         main_worker.py               │
│   Database   │         │  ┌──────────────────────────────┐    │
│              │         │  │     PCWorker Class           │    │
│  - meetings  │         │  │  ┌────────────────────────┐  │    │
│  - segments  │         │  │  │   Polling Loop         │  │    │
│  - speakers  │         │  │  │  - Get pending         │  │    │
│  - summaries │         │  │  │  - Process each        │  │    │
│              │         │  │  │  - Update status       │  │    │
└──────────────┘         │  │  └────────────────────────┘  │    │
                         │  │                              │    │
┌──────────────┐         │  │  ┌────────────────────────┐  │    │
│   Supabase   │◄────────┤  │  │   Process Pipeline     │  │    │
│   Storage    │         │  │  │  1. Download audio     │  │    │
│              │         │  │  │  2. Preprocess         │  │    │
│  meeting-    │         │  │  │  3. [Phase 2: AI]      │  │    │
│  audio/      │         │  │  │  4. Update status      │  │    │
│              │         │  │  │  5. Cleanup            │  │    │
└──────────────┘         │  │  └────────────────────────┘  │    │
                         │  │                              │    │
                         │  │  ┌────────────────────────┐  │    │
                         │  │  │   Error Handling       │  │    │
                         │  │  │  - Retry logic         │  │    │
                         │  │  │  - Status updates      │  │    │
                         │  │  │  - Cleanup             │  │    │
                         │  │  └────────────────────────┘  │    │
                         │  └──────────────────────────────┘    │
                         └──────────────────────────────────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Module Structure                            │
└─────────────────────────────────────────────────────────────────┘

main_worker.py
    │
    ├── Uses: config.py (configuration)
    ├── Uses: logger.py (logging)
    ├── Uses: supabase_client.py (database)
    ├── Uses: audio_processor.py (audio)
    ├── Uses: models.py (data structures)
    ├── Uses: exceptions.py (errors)
    └── Uses: utils.py (helpers)

supabase_client.py
    │
    ├── Implements: SupabaseClient (singleton)
    ├── Methods:
    │   ├── get_pending_meetings()
    │   ├── update_meeting_status()
    │   ├── get_meeting_audio_url()
    │   ├── download_audio_file()
    │   ├── save_transcript()
    │   ├── save_speakers()
    │   └── save_summary()
    └── Features:
        ├── Retry logic (3 attempts)
        ├── Error handling
        └── Health checks

audio_processor.py
    │
    ├── Implements: AudioProcessor
    ├── Methods:
    │   ├── download_audio()
    │   ├── load_audio()
    │   ├── preprocess_audio()
    │   ├── validate_audio_format()
    │   └── get_audio_duration()
    └── Features:
        ├── Resample to 16kHz
        ├── Normalize audio
        ├── Mono conversion
        └── Optional silence removal

models.py
    │
    ├── Pydantic Models:
    │   ├── Meeting
    │   ├── MeetingStatus (enum)
    │   ├── TranscriptSegment
    │   ├── Transcript
    │   ├── Speaker
    │   ├── SpeakerEmbedding
    │   ├── MeetingSummary
    │   ├── AudioMetadata
    │   ├── SystemInfo
    │   └── ProcessingResult
    └── Features:
        ├── Automatic validation
        ├── Type safety
        └── Serialization

logger.py
    │
    ├── Implements: StructuredLogger
    ├── Outputs:
    │   ├── Console (colored)
    │   ├── File (rotated)
    │   └── Error log (separate)
    └── Features:
        ├── Structured data
        ├── Operation tracking
        └── Meeting events

utils.py
    │
    ├── System:
    │   ├── get_system_info()
    │   └── validate_audio_file()
    ├── Files:
    │   ├── cleanup_temp_files()
    │   ├── sanitize_filename()
    │   └── ensure_directory()
    ├── Formatting:
    │   ├── format_timestamp()
    │   └── format_duration()
    └── Async:
        └── retry_with_backoff()

exceptions.py
    │
    └── Exception Hierarchy:
        ├── PCWorkerException
        ├── SupabaseError
        │   ├── SupabaseConnectionError
        │   ├── SupabaseQueryError
        │   └── SupabaseStorageError
        ├── AudioProcessingError
        │   ├── AudioDownloadError
        │   ├── AudioCorruptedError
        │   └── AudioPreprocessingError
        └── RetryExhaustedError
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                           │
└─────────────────────────────────────────────────────────────────┘

1. POLLING
   ┌──────────────────────────────────────────────┐
   │ poll_pending_meetings()                      │
   │  └─► Supabase.get_pending_meetings()        │
   │      └─► Returns: List[Meeting]             │
   └──────────────────────────────────────────────┘
                    │
                    ▼
2. STATUS UPDATE
   ┌──────────────────────────────────────────────┐
   │ Supabase.update_meeting_status()             │
   │  └─► Status: pending → processing           │
   └──────────────────────────────────────────────┘
                    │
                    ▼
3. DOWNLOAD
   ┌──────────────────────────────────────────────┐
   │ AudioProcessor.download_audio()              │
   │  ├─► Get URL from database                  │
   │  ├─► Download to temp_audio/                │
   │  └─► Validate downloaded file               │
   └──────────────────────────────────────────────┘
                    │
                    ▼
4. PREPROCESS
   ┌──────────────────────────────────────────────┐
   │ AudioProcessor.preprocess_audio()            │
   │  ├─► Load audio with librosa                │
   │  ├─► Resample to 16kHz                      │
   │  ├─► Normalize to [-1, 1]                   │
   │  ├─► Convert to mono                        │
   │  └─► Save as WAV PCM_16                     │
   └──────────────────────────────────────────────┘
                    │
                    ▼
5. AI PROCESSING (Phase 2)
   ┌──────────────────────────────────────────────┐
   │ [TODO] WhisperX Transcription                │
   │ [TODO] Speaker Diarization                   │
   │ [TODO] Speaker Identification                │
   │ [TODO] Summary Generation                    │
   └──────────────────────────────────────────────┘
                    │
                    ▼
6. SAVE RESULTS (Phase 2)
   ┌──────────────────────────────────────────────┐
   │ Supabase.save_transcript()                   │
   │ Supabase.save_speakers()                     │
   │ Supabase.save_summary()                      │
   └──────────────────────────────────────────────┘
                    │
                    ▼
7. COMPLETION
   ┌──────────────────────────────────────────────┐
   │ Supabase.update_meeting_status()             │
   │  └─► Status: processing → completed         │
   └──────────────────────────────────────────────┘
                    │
                    ▼
8. CLEANUP
   ┌──────────────────────────────────────────────┐
   │ cleanup_single_file()                        │
   │  ├─► Remove temp audio                      │
   │  └─► Remove processed audio                 │
   └──────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Recovery                                │
└─────────────────────────────────────────────────────────────────┘

Any Error Occurs
      │
      ▼
┌──────────────────┐
│ Exception Caught │
└──────────────────┘
      │
      ├─► Retry-able? ──Yes──► Exponential Backoff ──► Retry
      │                              │
      │                              └─► Max Attempts? ──Yes──┐
      └─► No                                                   │
            │                                                  │
            ▼                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ _handle_processing_error()                                      │
│  ├─► Log error with context                                     │
│  ├─► Update meeting status to 'failed'                          │
│  ├─► Store error message in database                            │
│  └─► Cleanup temp files                                         │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
      Continue with next meeting
```

## Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration Layers                          │
└─────────────────────────────────────────────────────────────────┘

1. Environment Variables (.env)
   ├── SUPABASE_URL
   ├── SUPABASE_KEY
   ├── WORKER_ID
   ├── WORKER_NAME
   ├── LOG_LEVEL
   ├── ENABLE_GPU
   ├── CUDA_DEVICE
   ├── AUDIO_TEMP_DIR
   ├── MODEL_CACHE_DIR
   ├── MAX_CONCURRENT_JOBS
   └── POLLING_INTERVAL_SECONDS

2. Config Module (config.py)
   ├── Loads .env with python-dotenv
   ├── Validates required variables
   ├── Sets defaults for optional variables
   ├── Creates required directories
   └── Exports configuration constants

3. Runtime Configuration
   ├── System detection (CPU/GPU)
   ├── Memory availability
   ├── Model paths
   └── Worker state
```

## Logging Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Logging System                                │
└─────────────────────────────────────────────────────────────────┘

StructuredLogger
      │
      ├─► Console Handler
      │   ├── Level: INFO
      │   ├── Format: Simple
      │   └── Output: stdout
      │
      ├─► File Handler (rotating)
      │   ├── Level: DEBUG
      │   ├── Format: Detailed
      │   ├── File: logs/pc_worker.log
      │   ├── Max Size: 10MB
      │   └── Backups: 5
      │
      └─► Error Handler (rotating)
          ├── Level: ERROR
          ├── Format: Detailed
          ├── File: logs/pc_worker_errors.log
          ├── Max Size: 10MB
          └── Backups: 5

Log Entry Structure:
[Timestamp] - [Logger] - [Level] - [File:Line] - Message | key=value | ...
```

## Database Schema Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    Database Schema                               │
└─────────────────────────────────────────────────────────────────┘

meetings
   │
   ├──┬── transcript_segments (FK: meeting_id)
   │  │   └── Links to speakers (FK: speaker_id)
   │  │
   │  └── meeting_summaries (FK: meeting_id)
   │
   └── processed_by: worker_id

speakers
   ├── id (UUID)
   ├── embedding (JSONB)
   ├── meeting_ids[] (Array)
   └── user_id (FK: users)

Status Flow:
pending → processing → completed
                    └→ failed
```

## Async Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Async Patterns                                │
└─────────────────────────────────────────────────────────────────┘

Main Event Loop
      │
      └─► PCWorker.start()
            │
            ├─► Polling Loop (async)
            │   ├── Sleep between polls
            │   └── Non-blocking I/O
            │
            └─► Process Meeting (async)
                ├── Download (async)
                ├── Preprocess (async)
                ├── Save Results (async)
                └── Cleanup (sync)

Thread Pool Usage:
- Supabase operations (asyncio.to_thread)
- Audio loading (asyncio.to_thread)
- Audio processing (asyncio.to_thread)
- File I/O (aiohttp for downloads)

Benefits:
- Non-blocking database queries
- Efficient network I/O
- Responsive shutdown
- Concurrent job support (configurable)
```

## Security Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Layers                               │
└─────────────────────────────────────────────────────────────────┘

1. Configuration Security
   ├── No hardcoded credentials
   ├── Environment variables only
   ├── .env in .gitignore
   └── .env.example for templates

2. Input Validation
   ├── Pydantic models for all data
   ├── Audio file validation
   ├── Filename sanitization
   └── Path traversal prevention

3. Error Handling
   ├── No sensitive data in logs
   ├── Generic error messages
   ├── Stack traces in log files only
   └── Status updates without details

4. Resource Management
   ├── Temp file cleanup
   ├── Memory limits (implicit)
   ├── File size validation
   └── Automatic retry limits

5. Network Security
   ├── HTTPS for Supabase
   ├── Signed URLs for storage
   ├── Connection timeout
   └── Retry with backoff
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Deployment                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Professor's │
│     PC       │
└──────────────┘
      │
      └─► PC Worker (systemd service)
            ├── Virtual Environment
            ├── Configuration (.env)
            ├── Logs (rotated)
            ├── Temp Storage
            └── Model Cache
                  │
                  └─► Network Connection
                        │
                        └─► Supabase Cloud
                              ├── Database
                              └── Storage

Multiple Workers Supported:
Worker-01 (Professor PC) ─┐
Worker-02 (Lab PC)        ├─► Supabase
Worker-03 (Server)        ┘
(Each with unique WORKER_ID)
```

---

**Architecture Design:** Modular, async, production-ready
**Error Handling:** Comprehensive with retry logic
**Scalability:** Multiple workers, configurable concurrency
**Maintainability:** Clean separation of concerns, well-documented
**Security:** Environment-based configuration, input validation
**Monitoring:** Structured logging, health checks, metrics
