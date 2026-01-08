# PC Worker Quick Start Guide

## 5-Minute Setup

### Prerequisites
```bash
# Verify Python 3.9+
python --version

# Verify pip
pip --version
```

### Step 1: Install Dependencies (2 minutes)
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment (1 minute)
```bash
# Copy template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and set:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-anon-key
```

### Step 3: Test Setup (1 minute)
```bash
python test_components.py
```

Expected output:
```
============================================================
PC WORKER COMPONENT TEST SUITE
============================================================

[PASS] Imports
[PASS] Custom Modules
[PASS] Configuration
[PASS] Data Models
[PASS] Utilities
[PASS] Logger
[PASS] Audio Processor
[PASS] Supabase Client
[PASS] GPU

============================================================
ALL TESTS PASSED (9/9)
============================================================
PC Worker is ready to run!
```

### Step 4: Setup Database (1 minute)

In Supabase SQL Editor, run:
```sql
-- Create meetings table
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

-- Create transcript_segments table (Phase 2)
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

-- Create index for queries
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_transcript_meeting_id ON transcript_segments(meeting_id);
```

In Supabase Storage:
1. Go to Storage
2. Create bucket: `meeting-audio`
3. Make it public or set appropriate policies

### Step 5: Run Worker
```bash
python main_worker.py
```

Expected output:
```
============================================================
PC Worker Starting
============================================================
2026-01-08 10:00:00 - INFO - Worker initialized | worker_id=professor-pc-01 | gpu_available=True | gpu_name=NVIDIA RTX 3090 | memory_gb=12.34
2026-01-08 10:00:00 - INFO - Starting Professor PC Worker...
2026-01-08 10:00:00 - DEBUG - No pending meetings found
```

## Test with Sample Meeting

### Create Test Meeting
```sql
-- Insert test meeting
INSERT INTO meetings (title, status, audio_url, user_id)
VALUES (
  'Test Meeting',
  'pending',
  'https://example.com/test-audio.wav',
  'your-user-id'
);
```

### Monitor Processing
Watch logs:
```bash
# Windows PowerShell
Get-Content logs\pc_worker.log -Wait

# Linux/Mac
tail -f logs/pc_worker.log
```

Check status:
```sql
SELECT id, title, status, error_message
FROM meetings
WHERE title = 'Test Meeting';
```

## Common Commands

### Start Worker
```bash
python main_worker.py
```

### Stop Worker
```bash
# Press Ctrl+C (graceful shutdown)
```

### Check Logs
```bash
# Main log
cat logs/pc_worker.log

# Errors only
cat logs/pc_worker_errors.log

# Live monitoring
tail -f logs/pc_worker.log  # Linux/Mac
Get-Content logs\pc_worker.log -Wait  # Windows
```

### Run Tests
```bash
python test_components.py
```

### Clean Temp Files
```bash
# Automatic on worker start/stop
# Manual cleanup:
# Windows
del /q temp_audio\*.*
# Linux/Mac
rm -f temp_audio/*
```

## Configuration Quick Reference

### .env Variables
```bash
# Required
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_KEY=eyJhbGc...

# Optional (with defaults)
WORKER_ID=professor-pc-01
WORKER_NAME=Professor PC Worker
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=60
MAX_CONCURRENT_JOBS=1
ENABLE_GPU=true
CUDA_DEVICE=0
AUDIO_TEMP_DIR=./temp_audio
MODEL_CACHE_DIR=./models
```

### Adjusting Settings

**Faster Polling:**
```bash
POLLING_INTERVAL_SECONDS=30
```

**More Concurrent Jobs:**
```bash
MAX_CONCURRENT_JOBS=3
```

**Debug Logging:**
```bash
LOG_LEVEL=DEBUG
```

**CPU Only:**
```bash
ENABLE_GPU=false
```

## Troubleshooting Quick Fixes

### "Module not found"
```bash
pip install -r requirements.txt --force-reinstall
```

### "SUPABASE_URL must be set"
```bash
# Check .env file exists and has correct format
# No quotes around values!
```

### "Connection refused"
```bash
# Check Supabase URL is correct
# Check internet connection
# Verify Supabase project is not paused
```

### "No meetings found"
```bash
# Check meetings exist with status='pending'
SELECT * FROM meetings WHERE status='pending';
```

### GPU not detected
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# If False, worker will use CPU (slower but works)
```

## File Structure Quick Reference

```
pc_worker/
├── main_worker.py          # Start here
├── config.py               # Configuration
├── supabase_client.py      # Database
├── audio_processor.py      # Audio processing
├── models.py               # Data structures
├── logger.py               # Logging
├── utils.py                # Utilities
├── exceptions.py           # Errors
├── test_components.py      # Tests
├── requirements.txt        # Dependencies
├── .env                    # Your config
└── .env.example            # Template
```

## Next Steps After Setup

1. **Run First Test**
   - Create test meeting in Supabase
   - Upload test audio
   - Monitor worker logs
   - Verify status updates

2. **Configure for Production**
   - Set up systemd service (Linux)
   - Configure log monitoring
   - Set up error alerts
   - Test auto-restart

3. **Phase 2 Integration**
   - Add WhisperX transcription
   - Add speaker diarization
   - Add summary generation
   - Test end-to-end pipeline

## Support & Documentation

- **Full Documentation**: `README_IMPLEMENTATION.md`
- **Setup Guide**: `SETUP.md`
- **Architecture**: `ARCHITECTURE.md`
- **Completion Summary**: `TASK_1.3_COMPLETION_SUMMARY.md`
- **Checklist**: `CHECKLIST.md`

## Quick Health Check

```bash
# 1. Test imports
python -c "from main_worker import PCWorker; print('OK')"

# 2. Test configuration
python -c "from config import SUPABASE_URL; print(SUPABASE_URL)"

# 3. Test Supabase connection
python -c "from supabase_client import get_supabase_client; import asyncio; asyncio.run(get_supabase_client().health_check())"

# 4. Test system info
python -c "from utils import get_system_info; print(get_system_info('test', 'Test'))"

# 5. Run full test suite
python test_components.py
```

## Production Deployment Checklist

- [ ] Install dependencies
- [ ] Configure .env with production credentials
- [ ] Run test_components.py
- [ ] Create database tables
- [ ] Create storage bucket
- [ ] Test with sample meeting
- [ ] Set up systemd service
- [ ] Configure log monitoring
- [ ] Set up error alerts
- [ ] Document operations procedures
- [ ] Test graceful shutdown
- [ ] Monitor first production run

---

**Ready in 5 minutes. Production-ready. Phase 2 prepared.**

For detailed documentation, see `README_IMPLEMENTATION.md`
