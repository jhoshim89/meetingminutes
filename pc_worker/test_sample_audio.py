#!/usr/bin/env python3
"""
Test WhisperX + Speaker Diarization with sample audio
"""

import asyncio
from pathlib import Path
import time

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import config first to apply PyTorch 2.6+ compatibility patch
import config

from stt_pipeline import get_stt_pipeline
from logger import get_logger

logger = get_logger("test_sample")

SAMPLE_AUDIO = Path("D:/Productions/meetingminutes/data/sampledata.m4a")
TEST_MEETING_ID = "test-sample-001"


async def main():
    print("=" * 60)
    print("WhisperX + Speaker Diarization Test")
    print("=" * 60)
    print(f"Audio file: {SAMPLE_AUDIO}")
    print(f"File size: {SAMPLE_AUDIO.stat().st_size / 1024 / 1024:.2f} MB")
    print()

    # Initialize pipeline
    print("Initializing STT pipeline...")
    start_init = time.time()
    pipeline = get_stt_pipeline(
        enable_preprocessing=True,
        enable_noise_reduction=True
    )
    await pipeline.initialize()
    print(f"Pipeline initialized in {time.time() - start_init:.2f}s")
    print()

    # Process audio
    print("Processing audio...")
    start_process = time.time()

    result = await pipeline.process_audio(
        audio_path=SAMPLE_AUDIO,
        meeting_id=TEST_MEETING_ID,
        language="ko",
        num_speakers=None,  # Auto-detect
        enhance_audio=True
    )

    total_time = time.time() - start_process

    # Print results
    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Audio duration: {result.audio_metadata.duration_seconds:.2f}s")
    print(f"Processing time: {total_time:.2f}s")
    print(f"Real-time factor: {total_time / result.audio_metadata.duration_seconds:.2f}x")
    print()
    print(f"Transcription time: {result.transcription_time:.2f}s")
    print(f"Diarization time: {result.diarization_time:.2f}s")
    print(f"Alignment time: {result.alignment_time:.2f}s")
    print()
    print(f"Segments: {len(result.transcript.segments)}")
    print(f"Speakers detected: {result.num_speakers_detected}")
    print(f"Average confidence: {result.average_confidence:.2f}" if result.average_confidence else "N/A")
    print(f"Alignment rate: {result.alignment_rate * 100:.1f}%")
    print()

    # Print transcript
    print("=" * 60)
    print("Transcript")
    print("=" * 60)
    for seg in result.transcript.segments[:20]:  # First 20 segments
        speaker = seg.speaker_label or "Unknown"
        confidence = f"({seg.confidence:.2f})" if seg.confidence else ""
        print(f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s] {speaker}: {seg.text} {confidence}")

    if len(result.transcript.segments) > 20:
        print(f"... and {len(result.transcript.segments) - 20} more segments")

    # Cleanup
    await pipeline.cleanup()
    print()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
