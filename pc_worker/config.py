import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PyTorch 2.6+ compatibility: Patch torch.load to use weights_only=False
# This is needed because pyannote/whisperx models use pickle serialization
# Must be done early before any torch imports
try:
    import torch
    _original_torch_load = torch.load

    def _patched_torch_load(*args, **kwargs):
        """Patched torch.load with weights_only=False for model compatibility"""
        kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)

    torch.load = _patched_torch_load
except ImportError:
    pass

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Worker Configuration
WORKER_ID = os.getenv("WORKER_ID", "default-worker")
WORKER_NAME = os.getenv("WORKER_NAME", "Default Worker")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Use StructuredLogger for meeting event logging support
from logger import get_logger
logger = get_logger("pc_worker", level=LOG_LEVEL)

# GPU Configuration
ENABLE_GPU = os.getenv("ENABLE_GPU", "true").lower() == "true"
CUDA_DEVICE = int(os.getenv("CUDA_DEVICE", "0"))

# HuggingFace Configuration (for pyannote diarization models)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")

# Storage Configuration
# Use absolute paths to avoid issues when working directory changes during model loading
_BASE_DIR = Path(__file__).parent.resolve()
AUDIO_TEMP_DIR = Path(os.getenv("AUDIO_TEMP_DIR", str(_BASE_DIR / "temp_audio"))).resolve()
MODEL_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", str(_BASE_DIR / "models"))).resolve()

# Create directories if they don't exist
AUDIO_TEMP_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Performance Configuration
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", "60"))

# Folder Monitoring Configuration
WATCH_FOLDER_PATH = os.getenv("WATCH_FOLDER_PATH", "")
AUDIO_EXTENSIONS = [".m4a", ".wav", ".mp3", ".mp4", ".webm"]
FILE_STABLE_CHECK_INTERVAL = float(os.getenv("FILE_STABLE_CHECK_INTERVAL", "2.0"))  # seconds
FILE_STABLE_CHECK_COUNT = int(os.getenv("FILE_STABLE_CHECK_COUNT", "3"))  # number of checks

# Word Document Output Configuration
WORD_OUTPUT_PATH = os.getenv("WORD_OUTPUT_PATH", "./output")

# Model Configuration
WHISPERX_MODEL = "large-v2"
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.0"
EMBEDDING_MODEL = "speechbrain/spkrec-ecapa-tdnn"

# Ollama Configuration for Summarization
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:7b")
SUMMARIZATION_ENABLED = os.getenv("SUMMARIZATION_ENABLED", "true").lower() == "true"
SUMMARIZATION_TIMEOUT = int(os.getenv("SUMMARIZATION_TIMEOUT", "300"))  # 5 minutes
SUMMARIZATION_MAX_RETRIES = int(os.getenv("SUMMARIZATION_MAX_RETRIES", "3"))

# Summarization Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "4000"))  # Characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # Overlap between chunks
SUMMARY_LENGTH_MIN = int(os.getenv("SUMMARY_LENGTH_MIN", "100"))  # Minimum summary length
SUMMARY_LENGTH_MAX = int(os.getenv("SUMMARY_LENGTH_MAX", "1000"))  # Maximum summary length

# Validation
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

logger.info(f"Worker initialized: {WORKER_NAME} ({WORKER_ID})")
logger.info(f"GPU enabled: {ENABLE_GPU}")
logger.info(f"Polling interval: {POLLING_INTERVAL_SECONDS}s")
logger.info(f"Summarization enabled: {SUMMARIZATION_ENABLED}")
if SUMMARIZATION_ENABLED:
    logger.info(f"Ollama URL: {OLLAMA_BASE_URL}")
    logger.info(f"Ollama model: {OLLAMA_MODEL}")
