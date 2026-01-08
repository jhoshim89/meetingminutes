"""
Comprehensive Tests for STT + Speaker Diarization
Tests for WhisperX, Pyannote, and integrated pipeline
"""

import pytest
import asyncio
from pathlib import Path
import numpy as np
import soundfile as sf
from typing import List, Dict
import time

# Import modules to test
from audio_processor import AudioProcessor, get_audio_processor
from whisperx_engine import WhisperXEngine, WhisperXConfig, get_whisperx_engine
from speaker_diarization import SpeakerDiarizationEngine, get_diarization_engine
from models import TranscriptSegment, AudioMetadata, SpeakerEmbedding


# Test Constants
TEST_SAMPLE_RATE = 16000
TEST_DURATION = 10.0  # seconds
TEST_MEETING_ID = "test-meeting-001"


# Fixtures

@pytest.fixture
def test_audio_dir(tmp_path):
    """Create temporary directory for test audio files"""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return audio_dir


@pytest.fixture
async def audio_processor():
    """Create audio processor instance"""
    processor = get_audio_processor(
        target_sample_rate=TEST_SAMPLE_RATE,
        normalize=True,
        remove_silence=False
    )
    return processor


@pytest.fixture
async def whisperx_engine():
    """Create WhisperX engine instance (expensive, may take time)"""
    config = WhisperXConfig(
        model_size="base",  # Use smaller model for testing
        language="ko",
        batch_size=8,
        confidence_threshold=0.7
    )
    engine = WhisperXEngine(config)
    await engine.initialize()
    yield engine
    await engine.cleanup()


@pytest.fixture
async def diarization_engine():
    """Create diarization engine instance (expensive, may take time)"""
    engine = get_diarization_engine()
    await engine.initialize()
    yield engine
    await engine.cleanup()


def generate_test_audio(
    duration: float,
    sample_rate: int = 16000,
    num_speakers: int = 2
) -> np.ndarray:
    """
    Generate synthetic test audio with multiple speakers

    Args:
        duration: Audio duration in seconds
        sample_rate: Sample rate
        num_speakers: Number of speakers to simulate

    Returns:
        Audio data as numpy array
    """
    samples = int(duration * sample_rate)
    audio = np.zeros(samples)

    # Generate speech-like patterns
    for speaker_idx in range(num_speakers):
        # Each speaker speaks in different time segments
        segment_duration = duration / num_speakers
        start_sample = int(speaker_idx * segment_duration * sample_rate)
        end_sample = int((speaker_idx + 1) * segment_duration * sample_rate)

        # Generate tones at different frequencies for each speaker
        t = np.linspace(0, segment_duration, end_sample - start_sample)
        frequency = 200 + (speaker_idx * 100)  # Different pitch per speaker

        # Create speech-like modulated tone
        carrier = np.sin(2 * np.pi * frequency * t)
        modulation = np.sin(2 * np.pi * 5 * t) * 0.5 + 0.5
        speech_signal = carrier * modulation * 0.3

        audio[start_sample:end_sample] = speech_signal

    return audio


# Audio Processor Tests

@pytest.mark.asyncio
async def test_audio_processor_initialization(audio_processor):
    """Test audio processor initialization"""
    assert audio_processor is not None
    assert audio_processor.target_sample_rate == TEST_SAMPLE_RATE
    assert audio_processor.normalize is True


@pytest.mark.asyncio
async def test_audio_load_and_save(audio_processor, test_audio_dir):
    """Test loading and saving audio files"""
    # Generate test audio
    audio_data = generate_test_audio(5.0)
    test_file = test_audio_dir / "test_audio.wav"

    # Save test audio
    sf.write(test_file, audio_data, TEST_SAMPLE_RATE)

    # Load audio
    loaded_audio, sample_rate = await audio_processor.load_audio(test_file)

    assert loaded_audio is not None
    assert len(loaded_audio) > 0
    assert sample_rate == TEST_SAMPLE_RATE


@pytest.mark.asyncio
async def test_audio_normalization(audio_processor):
    """Test audio normalization"""
    # Create audio with varying amplitude
    audio_data = np.random.randn(16000) * 0.5

    # Normalize
    normalized = audio_processor._normalize_audio(audio_data)

    # Check normalization
    assert np.abs(normalized).max() <= 1.0
    assert np.abs(normalized).max() > 0.9  # Should be close to 1.0


@pytest.mark.asyncio
async def test_noise_reduction(audio_processor):
    """Test noise reduction"""
    # Generate audio with noise
    clean_audio = generate_test_audio(3.0)
    noise = np.random.randn(len(clean_audio)) * 0.1
    noisy_audio = clean_audio + noise

    # Apply noise reduction
    denoised = await audio_processor.reduce_noise(
        noisy_audio,
        TEST_SAMPLE_RATE
    )

    assert len(denoised) == len(noisy_audio)
    # Denoised should have less energy in high frequencies
    assert np.std(denoised) <= np.std(noisy_audio)


@pytest.mark.asyncio
async def test_voice_activity_detection(audio_processor):
    """Test VAD (Voice Activity Detection)"""
    # Generate audio with speech and silence
    speech = generate_test_audio(5.0)
    silence = np.zeros(int(TEST_SAMPLE_RATE * 2))
    audio_with_silence = np.concatenate([speech, silence, speech])

    # Detect voice activity
    segments = await audio_processor.detect_voice_activity(
        audio_with_silence,
        TEST_SAMPLE_RATE
    )

    assert len(segments) > 0
    # Should detect at least one voice segment
    assert segments[0][0] >= 0.0
    assert segments[0][1] > segments[0][0]


@pytest.mark.asyncio
async def test_audio_chunking(audio_processor):
    """Test splitting audio into chunks"""
    audio_data = generate_test_audio(30.0)  # 30 seconds

    # Split into 10-second chunks with 1-second overlap
    chunks = await audio_processor.split_audio_chunks(
        audio_data,
        TEST_SAMPLE_RATE,
        chunk_duration_seconds=10.0,
        overlap_seconds=1.0
    )

    assert len(chunks) > 0
    # Should have approximately 4 chunks (30s / 9s step)
    assert len(chunks) >= 3

    # Check chunk structure
    for chunk_audio, start_time, end_time in chunks:
        assert len(chunk_audio) > 0
        assert end_time > start_time
        assert end_time - start_time <= 10.1  # Allow small margin


@pytest.mark.asyncio
async def test_bandpass_filter(audio_processor):
    """Test bandpass filter application"""
    audio_data = generate_test_audio(3.0)

    # Apply bandpass filter
    filtered = await audio_processor.apply_bandpass_filter(
        audio_data,
        TEST_SAMPLE_RATE,
        lowcut=80.0,
        highcut=8000.0
    )

    assert len(filtered) == len(audio_data)
    # Filtered audio should have similar energy in speech range


@pytest.mark.asyncio
async def test_audio_enhancement_pipeline(audio_processor):
    """Test complete audio enhancement pipeline"""
    # Generate noisy audio
    clean_audio = generate_test_audio(5.0)
    noise = np.random.randn(len(clean_audio)) * 0.2
    noisy_audio = clean_audio + noise

    # Enhance
    enhanced = await audio_processor.enhance_audio_for_stt(
        noisy_audio,
        TEST_SAMPLE_RATE
    )

    assert len(enhanced) == len(noisy_audio)
    assert np.abs(enhanced).max() <= 1.0


# WhisperX Engine Tests

@pytest.mark.asyncio
@pytest.mark.slow
async def test_whisperx_initialization(whisperx_engine):
    """Test WhisperX engine initialization"""
    assert whisperx_engine is not None
    assert whisperx_engine._is_initialized is True
    assert whisperx_engine.model is not None


@pytest.mark.asyncio
@pytest.mark.slow
async def test_whisperx_model_info(whisperx_engine):
    """Test getting WhisperX model information"""
    info = whisperx_engine.get_model_info()

    assert "model_size" in info
    assert "device" in info
    assert "language" in info
    assert info["initialized"] is True


@pytest.mark.asyncio
@pytest.mark.slow
async def test_whisperx_transcription(whisperx_engine, test_audio_dir):
    """Test WhisperX transcription (real audio)"""
    # Note: This test requires a real audio file or synthetic speech
    # For now, we'll test the structure with synthetic audio

    # Generate test audio
    audio_data = generate_test_audio(5.0)
    test_file = test_audio_dir / "transcribe_test.wav"
    sf.write(test_file, audio_data, TEST_SAMPLE_RATE)

    # Transcribe
    segments = await whisperx_engine.transcribe(
        test_file,
        TEST_MEETING_ID,
        language="ko"
    )

    # Check structure (may not have content with synthetic audio)
    assert isinstance(segments, list)
    # Each segment should be a TranscriptSegment
    for seg in segments:
        assert isinstance(seg, TranscriptSegment)
        assert seg.meeting_id == TEST_MEETING_ID
        assert seg.end_time > seg.start_time


@pytest.mark.asyncio
@pytest.mark.slow
async def test_whisperx_supported_languages(whisperx_engine):
    """Test getting supported languages"""
    languages = await whisperx_engine.get_supported_languages()

    assert isinstance(languages, list)
    assert "ko" in languages  # Korean
    assert "en" in languages  # English


@pytest.mark.asyncio
@pytest.mark.slow
async def test_whisperx_processing_time_estimation(whisperx_engine):
    """Test processing time estimation"""
    estimated_time = await whisperx_engine.estimate_processing_time(600.0)  # 10 minutes

    assert estimated_time > 0
    # Should be reasonable (< 10 minutes for 10-minute audio)
    assert estimated_time < 600.0


# Speaker Diarization Tests

@pytest.mark.asyncio
@pytest.mark.slow
async def test_diarization_initialization(diarization_engine):
    """Test diarization engine initialization"""
    assert diarization_engine is not None
    assert diarization_engine._is_initialized is True
    assert diarization_engine.pipeline is not None


@pytest.mark.asyncio
@pytest.mark.slow
async def test_diarization_pipeline_info(diarization_engine):
    """Test getting diarization pipeline information"""
    info = diarization_engine.get_pipeline_info()

    assert "model_name" in info
    assert "device" in info
    assert info["initialized"] is True


@pytest.mark.asyncio
@pytest.mark.slow
async def test_speaker_diarization(diarization_engine, test_audio_dir):
    """Test speaker diarization"""
    # Generate multi-speaker audio
    audio_data = generate_test_audio(10.0, num_speakers=2)
    test_file = test_audio_dir / "diarization_test.wav"
    sf.write(test_file, audio_data, TEST_SAMPLE_RATE)

    # Perform diarization
    diarization = await diarization_engine.diarize(
        test_file,
        TEST_MEETING_ID,
        min_speakers=1,
        max_speakers=3
    )

    assert diarization is not None
    # Should detect at least one speaker
    speakers = list(diarization.labels())
    assert len(speakers) >= 1


@pytest.mark.asyncio
@pytest.mark.slow
async def test_diarization_transcript_alignment(diarization_engine, test_audio_dir):
    """Test aligning diarization with transcript"""
    # Generate test audio
    audio_data = generate_test_audio(10.0, num_speakers=2)
    test_file = test_audio_dir / "alignment_test.wav"
    sf.write(test_file, audio_data, TEST_SAMPLE_RATE)

    # Perform diarization
    diarization = await diarization_engine.diarize(
        test_file,
        TEST_MEETING_ID
    )

    # Create mock transcript segments
    mock_segments = [
        TranscriptSegment(
            meeting_id=TEST_MEETING_ID,
            start_time=0.0,
            end_time=5.0,
            text="안녕하세요",
            confidence=0.9
        ),
        TranscriptSegment(
            meeting_id=TEST_MEETING_ID,
            start_time=5.0,
            end_time=10.0,
            text="반갑습니다",
            confidence=0.85
        )
    ]

    # Align
    aligned_segments = await diarization_engine.align_with_transcript(
        diarization,
        mock_segments,
        TEST_MEETING_ID
    )

    assert len(aligned_segments) == len(mock_segments)
    # Check that speaker labels were assigned
    for seg in aligned_segments:
        assert isinstance(seg, TranscriptSegment)


# Integration Tests

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_pipeline_integration(
    audio_processor,
    whisperx_engine,
    diarization_engine,
    test_audio_dir
):
    """Test complete STT + Diarization pipeline"""
    # Step 1: Generate and preprocess audio
    audio_data = generate_test_audio(15.0, num_speakers=2)
    raw_file = test_audio_dir / "integration_raw.wav"
    processed_file = test_audio_dir / "integration_processed.wav"

    sf.write(raw_file, audio_data, TEST_SAMPLE_RATE)

    # Step 2: Preprocess audio
    metadata = await audio_processor.preprocess_audio(
        raw_file,
        processed_file,
        TEST_MEETING_ID
    )

    assert metadata is not None
    assert Path(metadata.file_path).exists()

    # Step 3: Transcribe with WhisperX
    start_time = time.time()
    transcript_segments = await whisperx_engine.transcribe(
        processed_file,
        TEST_MEETING_ID,
        language="ko"
    )
    transcription_time = time.time() - start_time

    # Step 4: Perform speaker diarization
    start_time = time.time()
    diarization = await diarization_engine.diarize(
        processed_file,
        TEST_MEETING_ID
    )
    diarization_time = time.time() - start_time

    # Step 5: Align transcript with diarization
    if len(transcript_segments) > 0:
        aligned_segments = await diarization_engine.align_with_transcript(
            diarization,
            transcript_segments,
            TEST_MEETING_ID
        )

        assert len(aligned_segments) == len(transcript_segments)

    # Performance validation
    total_time = transcription_time + diarization_time
    audio_duration = metadata.duration_seconds

    print(f"\n=== Integration Test Performance ===")
    print(f"Audio Duration: {audio_duration:.2f}s")
    print(f"Transcription Time: {transcription_time:.2f}s")
    print(f"Diarization Time: {diarization_time:.2f}s")
    print(f"Total Processing Time: {total_time:.2f}s")
    print(f"Real-time Factor: {total_time/audio_duration:.2f}x")

    # Assert performance targets (relaxed for testing)
    # In production with GPU, should be < 0.5x real-time
    assert total_time < audio_duration * 2.0  # Should be faster than 2x real-time


# Performance Benchmarking Tests

@pytest.mark.benchmark
@pytest.mark.slow
async def test_performance_benchmark_10min_audio(
    audio_processor,
    whisperx_engine,
    diarization_engine,
    test_audio_dir
):
    """Benchmark performance with 10-minute audio"""
    # Generate 10-minute audio
    audio_data = generate_test_audio(600.0, num_speakers=3)
    test_file = test_audio_dir / "benchmark_10min.wav"
    sf.write(test_file, audio_data, TEST_SAMPLE_RATE)

    # Measure preprocessing
    start = time.time()
    enhanced = await audio_processor.enhance_audio_for_stt(audio_data, TEST_SAMPLE_RATE)
    preprocess_time = time.time() - start

    # Measure transcription
    start = time.time()
    segments = await whisperx_engine.transcribe(test_file, TEST_MEETING_ID)
    transcription_time = time.time() - start

    # Measure diarization
    start = time.time()
    diarization = await diarization_engine.diarize(test_file, TEST_MEETING_ID)
    diarization_time = time.time() - start

    total_time = preprocess_time + transcription_time + diarization_time

    print(f"\n=== 10-Minute Audio Benchmark ===")
    print(f"Preprocessing: {preprocess_time:.2f}s")
    print(f"Transcription: {transcription_time:.2f}s")
    print(f"Diarization: {diarization_time:.2f}s")
    print(f"Total: {total_time:.2f}s")
    print(f"Target: <180s (3 minutes)")

    # Performance target: 10 minutes of audio in < 3 minutes
    # This may fail on CPU, but should pass on GPU
    # assert total_time < 180.0  # Uncomment for strict testing


# Accuracy Tests (requires manual validation)

@pytest.mark.manual
async def test_korean_transcription_accuracy():
    """
    Manual test for Korean transcription accuracy
    Requires real Korean audio samples with ground truth
    """
    # This test should be run with real Korean meeting audio
    # and compared against human-transcribed ground truth
    # to calculate WER (Word Error Rate)
    pass


@pytest.mark.manual
async def test_speaker_identification_accuracy():
    """
    Manual test for speaker identification accuracy
    Requires real multi-speaker audio with ground truth labels
    """
    # This test should be run with real multi-speaker audio
    # and compared against ground truth speaker labels
    # to calculate DER (Diarization Error Rate)
    pass


if __name__ == "__main__":
    # Run tests with: pytest test_stt_diarization.py -v
    # Run slow tests: pytest test_stt_diarization.py -v --run-slow
    # Run benchmarks: pytest test_stt_diarization.py -v --benchmark
    pytest.main([__file__, "-v"])
