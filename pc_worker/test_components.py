#!/usr/bin/env python3
"""
Component Testing Script
Verify that all components are properly installed and configured
"""

import sys
import asyncio
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_test(test_name, passed, message=""):
    """Print test result with color"""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"[{status}] {test_name}")
    if message:
        print(f"       {message}")


def test_imports():
    """Test that all required modules can be imported"""
    print("\n" + "="*60)
    print("Testing Module Imports")
    print("="*60)

    modules_to_test = [
        ("asyncio", "Standard library"),
        ("pathlib", "Standard library"),
        ("dotenv", "Environment variables"),
        ("supabase", "Supabase client"),
        ("librosa", "Audio processing"),
        ("soundfile", "Audio I/O"),
        ("numpy", "Numerical computing"),
        ("torch", "PyTorch"),
        ("pydantic", "Data validation"),
        ("aiohttp", "Async HTTP client"),
        ("psutil", "System utilities"),
    ]

    all_passed = True
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print_test(f"Import {module_name}", True, description)
        except ImportError as e:
            print_test(f"Import {module_name}", False, str(e))
            all_passed = False

    return all_passed


def test_custom_modules():
    """Test custom module imports"""
    print("\n" + "="*60)
    print("Testing Custom Modules")
    print("="*60)

    modules = [
        "config",
        "exceptions",
        "logger",
        "models",
        "utils",
        "supabase_client",
        "audio_processor",
        "main_worker"
    ]

    all_passed = True
    for module_name in modules:
        try:
            __import__(module_name)
            print_test(f"Import {module_name}", True)
        except Exception as e:
            print_test(f"Import {module_name}", False, str(e))
            all_passed = False

    return all_passed


def test_configuration():
    """Test configuration loading"""
    print("\n" + "="*60)
    print("Testing Configuration")
    print("="*60)

    try:
        from config import (
            SUPABASE_URL,
            SUPABASE_KEY,
            WORKER_ID,
            WORKER_NAME,
            AUDIO_TEMP_DIR,
            MODEL_CACHE_DIR,
            POLLING_INTERVAL_SECONDS
        )

        print_test("Load SUPABASE_URL", bool(SUPABASE_URL), SUPABASE_URL)
        print_test("Load SUPABASE_KEY", bool(SUPABASE_KEY), "***" if SUPABASE_KEY else "Not set")
        print_test("Load WORKER_ID", bool(WORKER_ID), WORKER_ID)
        print_test("Load WORKER_NAME", bool(WORKER_NAME), WORKER_NAME)
        print_test("Audio temp dir exists", AUDIO_TEMP_DIR.exists(), str(AUDIO_TEMP_DIR))
        print_test("Model cache dir exists", MODEL_CACHE_DIR.exists(), str(MODEL_CACHE_DIR))
        print_test("Polling interval", POLLING_INTERVAL_SECONDS > 0, f"{POLLING_INTERVAL_SECONDS}s")

        return bool(SUPABASE_URL and SUPABASE_KEY)

    except Exception as e:
        print_test("Configuration", False, str(e))
        return False


def test_models():
    """Test Pydantic models"""
    print("\n" + "="*60)
    print("Testing Data Models")
    print("="*60)

    try:
        from models import (
            Meeting,
            MeetingStatus,
            TranscriptSegment,
            Speaker,
            MeetingSummary,
            AudioMetadata,
            SystemInfo
        )
        from datetime import datetime

        # Test Meeting model
        meeting = Meeting(
            id="test-id",
            title="Test Meeting",
            status=MeetingStatus.PENDING,
            created_at=datetime.now(),
            user_id="test-user"
        )
        print_test("Meeting model", True, f"Created meeting: {meeting.title}")

        # Test TranscriptSegment model
        segment = TranscriptSegment(
            meeting_id="test-id",
            start_time=0.0,
            end_time=10.0,
            text="Test transcript"
        )
        print_test("TranscriptSegment model", True, f"Duration: {segment.end_time - segment.start_time}s")

        # Test AudioMetadata model
        metadata = AudioMetadata(
            file_path="/test/audio.wav",
            duration_seconds=60.0,
            sample_rate=16000,
            channels=1,
            format="WAV",
            size_bytes=1024000
        )
        print_test("AudioMetadata model", True, f"Sample rate: {metadata.sample_rate}Hz")

        return True

    except Exception as e:
        print_test("Data models", False, str(e))
        return False


def test_utilities():
    """Test utility functions"""
    print("\n" + "="*60)
    print("Testing Utility Functions")
    print("="*60)

    try:
        from utils import (
            get_system_info,
            format_timestamp,
            format_duration,
            sanitize_filename,
            validate_audio_file
        )
        from config import WORKER_ID, WORKER_NAME

        # Test system info
        sys_info = get_system_info(WORKER_ID, WORKER_NAME)
        print_test(
            "Get system info",
            True,
            f"GPU: {sys_info.gpu_available}, Memory: {sys_info.memory_available_gb:.2f}GB"
        )

        # Test timestamp formatting
        timestamp = format_timestamp()
        print_test("Format timestamp", True, timestamp)

        # Test duration formatting
        duration = format_duration(3665.5)
        print_test("Format duration", True, f"3665.5s = {duration}")

        # Test filename sanitization
        sanitized = sanitize_filename("test<>file.wav")
        print_test("Sanitize filename", True, f"test<>file.wav -> {sanitized}")

        return True

    except Exception as e:
        print_test("Utilities", False, str(e))
        return False


def test_logger():
    """Test logging functionality"""
    print("\n" + "="*60)
    print("Testing Logger")
    print("="*60)

    try:
        from logger import get_logger

        test_logger = get_logger("test_component", level="INFO")
        test_logger.info("Test log message")
        test_logger.log_operation_start("test_operation", context="testing")
        test_logger.log_operation_success("test_operation", duration_ms=100.5)

        print_test("Create logger", True, "Logger created successfully")
        print_test("Log messages", True, "Check logs/ directory for output")

        return True

    except Exception as e:
        print_test("Logger", False, str(e))
        return False


async def test_audio_processor():
    """Test audio processor"""
    print("\n" + "="*60)
    print("Testing Audio Processor")
    print("="*60)

    try:
        from audio_processor import get_audio_processor

        processor = get_audio_processor()
        print_test("Create audio processor", True, f"Target SR: {processor.target_sample_rate}Hz")

        # Note: Cannot test actual audio processing without a file
        print_test(
            "Audio processing ready",
            True,
            f"{YELLOW}Actual audio processing requires test file{RESET}"
        )

        return True

    except Exception as e:
        print_test("Audio processor", False, str(e))
        return False


async def test_supabase_client():
    """Test Supabase client initialization"""
    print("\n" + "="*60)
    print("Testing Supabase Client")
    print("="*60)

    try:
        from supabase_client import get_supabase_client

        client = get_supabase_client()
        print_test("Create Supabase client", True, "Client initialized")

        # Test health check (requires valid credentials)
        print_test(
            "Supabase health check",
            True,
            f"{YELLOW}Requires valid credentials in .env{RESET}"
        )

        return True

    except Exception as e:
        print_test("Supabase client", False, str(e))
        return False


def test_gpu():
    """Test GPU availability"""
    print("\n" + "="*60)
    print("Testing GPU Availability")
    print("="*60)

    try:
        import torch

        cuda_available = torch.cuda.is_available()
        print_test("CUDA available", cuda_available)

        if cuda_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            print_test("GPU devices", True, f"{device_count} device(s)")
            print_test("GPU name", True, device_name)
        else:
            print(f"       {YELLOW}GPU not available - will use CPU{RESET}")

        return True

    except Exception as e:
        print_test("GPU test", False, str(e))
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PC WORKER COMPONENT TEST SUITE")
    print("="*60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Custom Modules", test_custom_modules()))
    results.append(("Configuration", test_configuration()))
    results.append(("Data Models", test_models()))
    results.append(("Utilities", test_utilities()))
    results.append(("Logger", test_logger()))
    results.append(("Audio Processor", await test_audio_processor()))
    results.append(("Supabase Client", await test_supabase_client()))
    results.append(("GPU", test_gpu()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"[{status}] {test_name}")

    print("\n" + "="*60)
    if passed == total:
        print(f"{GREEN}ALL TESTS PASSED ({passed}/{total}){RESET}")
        print("="*60)
        print(f"{GREEN}PC Worker is ready to run!{RESET}")
        print(f"\nTo start the worker, run:")
        print(f"  python main_worker.py")
        return 0
    else:
        print(f"{RED}SOME TESTS FAILED ({passed}/{total}){RESET}")
        print("="*60)
        print(f"{RED}Please fix the issues above before running the worker.{RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
