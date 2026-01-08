"""
Example Usage: STT + Speaker Diarization Pipeline
Quick start guide with practical examples
"""

import asyncio
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from stt_pipeline import get_stt_pipeline
from audio_processor import get_audio_processor
from logger import get_logger

logger = get_logger("example")


async def example_1_basic_transcription():
    """
    Example 1: Basic transcription with speaker diarization
    """
    print("\n=== Example 1: Basic Transcription ===\n")

    # Initialize pipeline
    pipeline = get_stt_pipeline(
        enable_preprocessing=True,
        enable_noise_reduction=True
    )

    print("Initializing models (this may take a few minutes on first run)...")
    await pipeline.initialize()

    # Process audio file
    audio_path = Path("sample_meeting.wav")  # Replace with your audio file

    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        print("Please provide a valid audio file path")
        await pipeline.cleanup()
        return

    print(f"Processing audio: {audio_path}")

    result = await pipeline.process_audio(
        audio_path=audio_path,
        meeting_id="example-meeting-001",
        language="ko",
        enhance_audio=True
    )

    # Display results
    print(f"\n=== Processing Complete ===")
    print(f"Processing time: {result.processing_time_seconds:.2f} seconds")
    print(f"Audio duration: {result.audio_metadata.duration_seconds:.2f} seconds")
    print(f"Real-time factor: {result.processing_time_seconds / result.audio_metadata.duration_seconds:.2f}x")
    print(f"\nTranscription: {len(result.transcript.segments)} segments")
    print(f"Speakers detected: {result.num_speakers_detected}")
    print(f"Average confidence: {result.average_confidence:.2%}" if result.average_confidence else "N/A")
    print(f"Alignment rate: {result.alignment_rate:.2%}")

    # Print transcript with speakers
    print(f"\n=== Transcript ===\n")
    for i, segment in enumerate(result.transcript.segments[:10], 1):  # First 10 segments
        speaker = segment.speaker_label or "Unknown"
        timestamp = f"[{segment.start_time:.1f}s - {segment.end_time:.1f}s]"
        print(f"{i}. {timestamp} [{speaker}]: {segment.text}")

    if len(result.transcript.segments) > 10:
        print(f"\n... and {len(result.transcript.segments) - 10} more segments")

    # Cleanup
    await pipeline.cleanup()


async def example_2_audio_preprocessing():
    """
    Example 2: Audio preprocessing and enhancement
    """
    print("\n=== Example 2: Audio Preprocessing ===\n")

    processor = get_audio_processor(
        target_sample_rate=16000,
        normalize=True,
        remove_silence=False
    )

    audio_path = Path("sample_meeting.wav")

    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        return

    print("Loading audio...")
    audio_data, sample_rate = await processor.load_audio(audio_path)

    print(f"Original sample rate: {sample_rate} Hz")
    print(f"Audio duration: {len(audio_data) / sample_rate:.2f} seconds")

    # Detect voice activity
    print("\nDetecting voice activity...")
    voice_segments = await processor.detect_voice_activity(
        audio_data,
        sample_rate,
        aggressiveness=2
    )

    print(f"Found {len(voice_segments)} voice segments:")
    for i, (start, end) in enumerate(voice_segments[:5], 1):
        print(f"  {i}. {start:.2f}s - {end:.2f}s ({end - start:.2f}s)")

    # Apply enhancements
    print("\nApplying audio enhancements...")
    enhanced = await processor.enhance_audio_for_stt(audio_data, sample_rate)

    # Save enhanced audio
    output_path = Path("enhanced_audio.wav")
    await processor.save_processed_audio(
        enhanced,
        processor.target_sample_rate,
        output_path
    )

    print(f"\nEnhanced audio saved to: {output_path}")


async def example_3_batch_processing():
    """
    Example 3: Batch processing multiple audio files
    """
    print("\n=== Example 3: Batch Processing ===\n")

    pipeline = get_stt_pipeline()

    print("Initializing pipeline...")
    await pipeline.initialize()

    # List of audio files to process
    audio_files = [
        Path("meeting1.wav"),
        Path("meeting2.wav"),
        Path("meeting3.wav")
    ]

    meeting_ids = [f"meeting-{i:03d}" for i in range(1, len(audio_files) + 1)]

    # Filter only existing files
    existing_files = [(path, mid) for path, mid in zip(audio_files, meeting_ids) if path.exists()]

    if not existing_files:
        print("No audio files found. Please add audio files to process.")
        await pipeline.cleanup()
        return

    paths, ids = zip(*existing_files)

    print(f"Processing {len(paths)} audio files...")

    results = await pipeline.process_batch(
        audio_paths=list(paths),
        meeting_ids=list(ids),
        language="ko"
    )

    # Display summary
    print(f"\n=== Batch Processing Summary ===")
    for result in results:
        print(f"\n{result.meeting_id}:")
        print(f"  Segments: {len(result.transcript.segments)}")
        print(f"  Speakers: {result.num_speakers_detected}")
        print(f"  Duration: {result.audio_metadata.duration_seconds:.2f}s")
        print(f"  Processing time: {result.processing_time_seconds:.2f}s")

    await pipeline.cleanup()


async def example_4_custom_configuration():
    """
    Example 4: Custom configuration for specific use cases
    """
    print("\n=== Example 4: Custom Configuration ===\n")

    from whisperx_engine import WhisperXEngine, WhisperXConfig
    from speaker_diarization import get_diarization_engine
    from stt_pipeline import STTPipeline

    # Custom WhisperX configuration
    whisperx_config = WhisperXConfig(
        model_size="base",  # Smaller model for faster processing
        device="cuda",  # Use GPU
        compute_type="float16",  # Mixed precision
        language="ko",
        batch_size=16,
        confidence_threshold=0.85,  # Higher confidence threshold
        chunk_length_seconds=30
    )

    print("Creating custom pipeline...")
    print(f"  Model: {whisperx_config.model_size}")
    print(f"  Device: {whisperx_config.device}")
    print(f"  Batch size: {whisperx_config.batch_size}")
    print(f"  Confidence threshold: {whisperx_config.confidence_threshold}")

    whisperx = WhisperXEngine(whisperx_config)
    diarization = get_diarization_engine()

    pipeline = STTPipeline(
        whisperx_engine=whisperx,
        diarization_engine=diarization,
        enable_preprocessing=True,
        enable_noise_reduction=False  # Disable noise reduction for speed
    )

    await pipeline.initialize()

    # Get pipeline info
    info = pipeline.get_pipeline_info()
    print(f"\nPipeline info:")
    print(f"  Initialized: {info['initialized']}")
    print(f"  WhisperX device: {info['whisperx'].get('device', 'N/A')}")
    print(f"  WhisperX model: {info['whisperx'].get('model_size', 'N/A')}")

    await pipeline.cleanup()


async def example_5_performance_monitoring():
    """
    Example 5: Performance monitoring and metrics
    """
    print("\n=== Example 5: Performance Monitoring ===\n")

    import time

    pipeline = get_stt_pipeline()

    # Monitor initialization time
    init_start = time.time()
    await pipeline.initialize()
    init_time = time.time() - init_start

    print(f"Initialization time: {init_time:.2f}s")

    audio_path = Path("sample_meeting.wav")

    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        await pipeline.cleanup()
        return

    # Monitor processing with detailed metrics
    result = await pipeline.process_audio(
        audio_path=audio_path,
        meeting_id="performance-test",
        language="ko",
        enhance_audio=True
    )

    # Detailed performance breakdown
    print(f"\n=== Performance Breakdown ===")
    print(f"Audio duration: {result.audio_metadata.duration_seconds:.2f}s")
    print(f"\nProcessing stages:")
    print(f"  1. Transcription: {result.transcription_time:.2f}s ({result.transcription_time / result.audio_metadata.duration_seconds:.2f}x)")
    print(f"  2. Diarization: {result.diarization_time:.2f}s ({result.diarization_time / result.audio_metadata.duration_seconds:.2f}x)")
    print(f"  3. Alignment: {result.alignment_time:.2f}s")
    print(f"\nTotal: {result.processing_time_seconds:.2f}s ({result.processing_time_seconds / result.audio_metadata.duration_seconds:.2f}x real-time)")

    # Quality metrics
    print(f"\n=== Quality Metrics ===")
    print(f"Segments: {len(result.transcript.segments)}")
    print(f"Speakers: {result.num_speakers_detected}")
    print(f"Average confidence: {result.average_confidence:.2%}" if result.average_confidence else "N/A")
    print(f"Alignment rate: {result.alignment_rate:.2%}")

    # Memory info (if available)
    try:
        import torch
        if torch.cuda.is_available():
            print(f"\n=== GPU Memory ===")
            print(f"Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            print(f"Cached: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
    except Exception as e:
        pass

    await pipeline.cleanup()


async def main():
    """
    Main function - run all examples or specific one
    """
    print("=" * 60)
    print("STT + Speaker Diarization Pipeline - Examples")
    print("=" * 60)

    examples = {
        "1": ("Basic Transcription", example_1_basic_transcription),
        "2": ("Audio Preprocessing", example_2_audio_preprocessing),
        "3": ("Batch Processing", example_3_batch_processing),
        "4": ("Custom Configuration", example_4_custom_configuration),
        "5": ("Performance Monitoring", example_5_performance_monitoring)
    }

    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  0. Run all examples")

    choice = input("\nSelect example (0-5): ").strip()

    if choice == "0":
        # Run all examples
        for name, func in examples.values():
            try:
                await func()
            except Exception as e:
                print(f"\nError in {name}: {e}")
                import traceback
                traceback.print_exc()
    elif choice in examples:
        # Run selected example
        name, func = examples[choice]
        try:
            await func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Invalid choice")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
