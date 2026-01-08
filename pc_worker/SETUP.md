# PC Worker Setup Guide

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Git (optional)
- CUDA-capable GPU (optional, for faster processing)

### Step 1: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and add your Supabase credentials
notepad .env  # Windows
# nano .env    # Linux/Mac
```

Required environment variables:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
WORKER_ID=professor-pc-01
WORKER_NAME=Professor PC Worker
```

### Step 3: Test Components

```bash
# Run component tests
python test_components.py
```

This will verify:
- All dependencies are installed
- Configuration is valid
- Modules can be imported
- System capabilities (CPU/GPU)

### Step 4: Setup Supabase Database

Run the SQL schema from `README_IMPLEMENTATION.md` in your Supabase SQL editor to create the required tables:
- meetings
- transcript_segments
- speakers
- meeting_summaries

### Step 5: Create Storage Bucket

In Supabase Dashboard:
1. Go to Storage
2. Create a new bucket called `meeting-audio`
3. Set appropriate access policies

### Step 6: Run the Worker

```bash
# Make sure virtual environment is activated
python main_worker.py
```

The worker will:
- Start polling for pending meetings every 60 seconds (configurable)
- Process meetings found in the database
- Log all activities to `logs/` directory

## Configuration Options

### Worker Settings
- `WORKER_ID` - Unique identifier for this worker instance
- `WORKER_NAME` - Human-readable name
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `POLLING_INTERVAL_SECONDS` - How often to check for new meetings (default: 60)
- `MAX_CONCURRENT_JOBS` - Maximum meetings to process simultaneously (default: 1)

### GPU Settings
- `ENABLE_GPU` - Enable GPU acceleration (default: true)
- `CUDA_DEVICE` - CUDA device index to use (default: 0)

### Storage Settings
- `AUDIO_TEMP_DIR` - Temporary directory for audio files (default: ./temp_audio)
- `MODEL_CACHE_DIR` - Directory for AI model cache (default: ./models)

## Troubleshooting

### "Module not found" errors
```bash
# Make sure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### "SUPABASE_URL and SUPABASE_KEY must be set"
```bash
# Check that .env file exists and has correct values
# Values should not have quotes
# Example:
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_KEY=eyJhbGc...
```

### GPU not detected
```bash
# Check PyTorch CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# If False, worker will use CPU (slower but functional)
# Or install CUDA toolkit and reinstall PyTorch with CUDA support
```

### Connection to Supabase fails
- Verify SUPABASE_URL is correct
- Check that SUPABASE_KEY is the anon/public key (not service key)
- Ensure internet connection is active
- Check Supabase project is not paused

### No meetings being processed
- Verify meetings exist in database with status='pending'
- Check that audio_url or audio_storage_path is set
- Review logs in `logs/pc_worker.log` for errors

## Testing with Sample Meeting

### Create Test Meeting in Supabase

```sql
-- Insert a test meeting
INSERT INTO meetings (title, status, audio_url, user_id)
VALUES (
  'Test Meeting',
  'pending',
  'https://example.com/test-audio.wav',
  'your-user-id'
);
```

Or upload audio to Supabase Storage and use storage path:

```sql
INSERT INTO meetings (title, status, audio_storage_path, user_id)
VALUES (
  'Test Meeting',
  'pending',
  'meeting-audio/test-audio.wav',
  'your-user-id'
);
```

### Monitor Processing

Watch the logs:
```bash
# Real-time log monitoring
# Windows:
Get-Content logs\pc_worker.log -Wait
# Linux/Mac:
tail -f logs/pc_worker.log
```

Check meeting status in Supabase:
```sql
SELECT id, title, status, error_message, processed_by
FROM meetings
ORDER BY created_at DESC
LIMIT 10;
```

## Directory Structure

After setup, your directory should look like:
```
pc_worker/
├── venv/                   # Virtual environment (created)
├── temp_audio/             # Temporary audio files (auto-created)
├── models/                 # AI model cache (auto-created)
├── logs/                   # Application logs (auto-created)
│   ├── pc_worker.log      # Main log file
│   └── pc_worker_errors.log  # Error-only log
├── main_worker.py
├── config.py
├── supabase_client.py
├── audio_processor.py
├── models.py
├── exceptions.py
├── logger.py
├── utils.py
├── test_components.py
├── requirements.txt
├── .env                    # Your configuration (create from .env.example)
├── .env.example
├── README_IMPLEMENTATION.md
└── SETUP.md               # This file
```

## Next Steps

After successful setup:

1. **Run in Production**
   - Set up as a systemd service (Linux) or Windows Service
   - Configure automatic restarts
   - Set up log monitoring/alerts

2. **Phase 2 Integration**
   - Add WhisperX transcription
   - Implement speaker diarization
   - Add AI summary generation
   - Connect to speaker identification system

3. **Monitoring**
   - Set up metrics collection
   - Configure error alerting
   - Monitor disk space for temp files
   - Track processing times

## Support

For issues or questions:
1. Check logs in `logs/pc_worker.log` and `logs/pc_worker_errors.log`
2. Run `python test_components.py` to verify setup
3. Review README_IMPLEMENTATION.md for detailed documentation
4. Contact development team

## Security Notes

- Never commit `.env` file to version control
- Keep SUPABASE_KEY secure
- Use service key only in secure environments
- Regularly rotate API keys
- Monitor for unauthorized access in Supabase dashboard
