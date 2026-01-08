"""
Utility Functions for PC Worker
Provides helper functions for common operations
"""

import os
import sys
import psutil
import torch
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio
from functools import wraps

from models import SystemInfo
from exceptions import ConfigurationError


def get_system_info(worker_id: str, worker_name: str) -> SystemInfo:
    """
    Get current system information including CPU/GPU availability

    Args:
        worker_id: Unique worker identifier
        worker_name: Human-readable worker name

    Returns:
        SystemInfo object with current system state
    """
    # Check GPU availability
    gpu_available = torch.cuda.is_available()
    gpu_name = None
    if gpu_available:
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "Unknown GPU"

    # Get memory info
    memory = psutil.virtual_memory()
    memory_total_gb = memory.total / (1024 ** 3)
    memory_available_gb = memory.available / (1024 ** 3)

    return SystemInfo(
        worker_id=worker_id,
        worker_name=worker_name,
        cpu_available=True,
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        memory_total_gb=round(memory_total_gb, 2),
        memory_available_gb=round(memory_available_gb, 2),
        python_version=sys.version.split()[0]
    )


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format timestamp in consistent ISO format

    Args:
        dt: Datetime to format. If None, uses current time

    Returns:
        ISO formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def cleanup_temp_files(
    temp_dir: Path,
    max_age_hours: int = 24,
    pattern: str = "*"
) -> int:
    """
    Remove old temporary files from specified directory

    Args:
        temp_dir: Directory containing temporary files
        max_age_hours: Maximum age of files to keep (in hours)
        pattern: Glob pattern for files to clean (default: all files)

    Returns:
        Number of files deleted
    """
    if not temp_dir.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    deleted_count = 0

    try:
        for file_path in temp_dir.glob(pattern):
            if file_path.is_file():
                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except OSError:
                        # Skip files that can't be deleted
                        pass
    except Exception:
        # If cleanup fails, just continue
        pass

    return deleted_count


def cleanup_single_file(file_path: Path) -> bool:
    """
    Remove a single file safely

    Args:
        file_path: Path to file to remove

    Returns:
        True if file was deleted, False otherwise
    """
    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
    except OSError:
        pass
    return False


def ensure_directory(directory: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        directory: Path to directory

    Returns:
        Path to directory

    Raises:
        ConfigurationError: If directory cannot be created
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    except Exception as e:
        raise ConfigurationError(f"Cannot create directory {directory}: {e}")


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    if not file_path.exists():
        return 0.0
    return file_path.stat().st_size / (1024 * 1024)


def validate_audio_file(file_path: Path) -> bool:
    """
    Basic validation that audio file exists and has reasonable size

    Args:
        file_path: Path to audio file

    Returns:
        True if file appears valid, False otherwise
    """
    if not file_path.exists():
        return False

    # Check file size (should be between 1KB and 500MB)
    size_mb = get_file_size_mb(file_path)
    if size_mb < 0.001 or size_mb > 500:
        return False

    # Check file extension
    valid_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.mp4', '.webm'}
    if file_path.suffix.lower() not in valid_extensions:
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove dangerous characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace dangerous characters
    dangerous_chars = '<>:"|?*\\/\n\r\t'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Limit length
    max_length = 200
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext)]
        filename = name + ext

    return filename


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        # Last attempt failed
                        raise

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


def chunk_list(items: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def get_audio_temp_path(meeting_id: str, temp_dir: Path) -> Path:
    """
    Get temporary path for audio file

    Args:
        meeting_id: Meeting identifier
        temp_dir: Temporary directory

    Returns:
        Path to temporary audio file
    """
    ensure_directory(temp_dir)
    return temp_dir / f"{meeting_id}_audio.wav"


def get_processed_audio_path(meeting_id: str, temp_dir: Path) -> Path:
    """
    Get path for processed audio file

    Args:
        meeting_id: Meeting identifier
        temp_dir: Temporary directory

    Returns:
        Path to processed audio file
    """
    ensure_directory(temp_dir)
    return temp_dir / f"{meeting_id}_processed.wav"
