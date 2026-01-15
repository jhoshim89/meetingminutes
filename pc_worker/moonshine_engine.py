"""
Moonshine STT Engine Module
Handles audio transcription using Moonshine Korean model
Optimized for Korean speech recognition with ~5.7% CER
"""

# Import config first to apply PyTorch compatibility patch
from config import ENABLE_GPU, CUDA_DEVICE, MODEL_CACHE_DIR

import asyncio
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import torch
import soundfile as sf
from dataclasses import dataclass

from pyannote.core import Annotation, Segment

from models import TranscriptSegment
from exceptions import TranscriptionError
from logger import get_logger

logger = get_logger("moonshine_engine")

# Moonshine model configuration
MOONSHINE_MODEL = "moonshine/tiny-ko"


def remove_repetition(text: str, min_pattern_len: int = 2, max_pattern_len: int = 30) -> str:
    """
    Remove repetitive patterns from transcribed text (hallucination filtering)

    Moonshine and other transformer models sometimes produce repetitive outputs
    like "그렇죠. 그렇죠. 그렇죠..." when audio is unclear or too short.

    Args:
        text: Input text to clean
        min_pattern_len: Minimum length of pattern to detect (default 2)
        max_pattern_len: Maximum length of pattern to detect (default 30)

    Returns:
        Cleaned text with repetitions removed
    """
    if not text or len(text) < min_pattern_len * 3:
        return text

    # Pattern: find 2+ consecutive repetitions of 2-30 character sequences
    pattern = rf'(.{{{min_pattern_len},{max_pattern_len}}}?)(\s*\1){{{2},}}'
    cleaned = re.sub(pattern, r'\1', text)

    # Log if significant repetition was removed
    if len(cleaned) < len(text) * 0.7:
        logger.debug(f"Removed repetition: {len(text)} -> {len(cleaned)} chars")

    return cleaned.strip()


@dataclass
class MoonshineConfig:
    """Configuration for Moonshine engine"""
    model_name: str = MOONSHINE_MODEL
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    min_segment_duration: float = 0.5  # Minimum segment length in seconds
    max_segment_duration: float = 30.0  # Maximum segment length before splitting
    sample_rate: int = 16000  # Moonshine expects 16kHz

    def __post_init__(self):
        """Validate configuration"""
        if not ENABLE_GPU and self.device == "cuda":
            logger.warning("GPU disabled in config, forcing CPU mode")
            self.device = "cpu"


class MoonshineEngine:
    """
    Moonshine-based Speech-to-Text engine optimized for Korean

    Key features:
    - 5.72% CER on Korean (vs ~11% for Whisper)
    - 5-15x faster than Whisper
    - 190MB model size (vs 1.5GB for Whisper large-v2)
    - Works with Pyannote diarization segments
    """

    def __init__(self, config: Optional[MoonshineConfig] = None):
        """
        Initialize Moonshine engine

        Args:
            config: Moonshine configuration (uses defaults if None)
        """
        self.config = config or MoonshineConfig()
        self.model = None
        self.processor = None
        self._is_initialized = False
        self._use_onnx = True  # Prefer ONNX for speed

        logger.info(
            f"Moonshine Engine initialized with: "
            f"model={self.config.model_name}, "
            f"device={self.config.device}"
        )

    async def initialize(self) -> None:
        """
        Load Moonshine model asynchronously

        Raises:
            TranscriptionError: If model loading fails
        """
        if self._is_initialized:
            logger.debug("Moonshine already initialized")
            return

        logger.log_operation_start("initialize_moonshine_model")

        try:
            # Try ONNX first (faster inference)
            try:
                await self._initialize_onnx()
                self._use_onnx = True
                logger.info("Moonshine ONNX backend initialized")
            except Exception as e:
                logger.warning(f"ONNX initialization failed: {e}, falling back to Transformers")
                await self._initialize_transformers()
                self._use_onnx = False
                logger.info("Moonshine Transformers backend initialized")

            self._is_initialized = True

            logger.log_operation_success(
                "initialize_moonshine_model",
                device=self.config.device,
                model=self.config.model_name,
                backend="onnx" if self._use_onnx else "transformers"
            )

        except Exception as e:
            logger.log_operation_failure("initialize_moonshine_model", e)
            raise TranscriptionError(f"Failed to initialize Moonshine: {e}")

    async def _initialize_onnx(self) -> None:
        """Initialize with ONNX runtime"""
        import moonshine_onnx

        # Just verify the module is available - models are loaded lazily
        self._moonshine_onnx = moonshine_onnx
        logger.debug("Moonshine ONNX module loaded")

    async def _initialize_transformers(self) -> None:
        """Initialize with HuggingFace Transformers"""
        from transformers import AutoProcessor, MoonshineForConditionalGeneration

        model_id = f"UsefulSensors/{self.config.model_name.replace('/', '-')}"

        self.processor = await asyncio.to_thread(
            AutoProcessor.from_pretrained,
            model_id,
            cache_dir=str(MODEL_CACHE_DIR)
        )

        self.model = await asyncio.to_thread(
            MoonshineForConditionalGeneration.from_pretrained,
            model_id,
            cache_dir=str(MODEL_CACHE_DIR)
        )

        if self.config.device == "cuda":
            self.model = self.model.to(self.config.device)

    async def transcribe_segment(
        self,
        audio: np.ndarray,
        start_time: float,
        end_time: float,
        meeting_id: str,
        speaker_label: Optional[str] = None
    ) -> TranscriptSegment:
        """
        Transcribe a single audio segment

        Args:
            audio: Audio data as numpy array (16kHz, mono)
            start_time: Segment start time in seconds
            end_time: Segment end time in seconds
            meeting_id: Meeting ID for tracking
            speaker_label: Optional speaker label

        Returns:
            TranscriptSegment with transcribed text
        """
        if not self._is_initialized:
            await self.initialize()

        # Skip very short segments
        duration = end_time - start_time
        if duration < self.config.min_segment_duration:
            logger.debug(f"Skipping short segment: {duration:.2f}s < {self.config.min_segment_duration}s")
            return TranscriptSegment(
                meeting_id=meeting_id,
                start_time=start_time,
                end_time=end_time,
                text="",
                confidence=None,
                speaker_label=speaker_label,
                speaker_id=None
            )

        try:
            # Transcribe
            text = await self._transcribe_audio(audio)

            return TranscriptSegment(
                meeting_id=meeting_id,
                start_time=start_time,
                end_time=end_time,
                text=remove_repetition(text.strip()),
                confidence=None,  # Moonshine doesn't provide confidence
                speaker_label=speaker_label,
                speaker_id=None
            )

        except Exception as e:
            logger.warning(f"Failed to transcribe segment {start_time:.2f}-{end_time:.2f}: {e}")
            return TranscriptSegment(
                meeting_id=meeting_id,
                start_time=start_time,
                end_time=end_time,
                text="[transcription failed]",
                confidence=0.0,
                speaker_label=speaker_label,
                speaker_id=None
            )

    async def _transcribe_audio(self, audio: np.ndarray) -> str:
        """
        Run transcription on audio data

        Args:
            audio: Audio data as numpy array (16kHz, mono, float32)

        Returns:
            Transcribed text
        """
        if self._use_onnx:
            return await self._transcribe_onnx(audio)
        else:
            return await self._transcribe_transformers(audio)

    async def _transcribe_onnx(self, audio: np.ndarray) -> str:
        """Transcribe using ONNX runtime"""
        import tempfile
        import os

        # Moonshine ONNX expects a file path, so we need to write to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            temp_path = tmp.name

        try:
            # Write audio to temp file
            await asyncio.to_thread(
                sf.write,
                temp_path,
                audio,
                self.config.sample_rate
            )

            # Transcribe
            result = await asyncio.to_thread(
                self._moonshine_onnx.transcribe,
                temp_path,
                self.config.model_name
            )

            # Result is a list of strings
            return result[0] if result else ""

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def _transcribe_transformers(self, audio: np.ndarray) -> str:
        """Transcribe using HuggingFace Transformers"""
        # Prepare input
        inputs = self.processor(
            audio,
            sampling_rate=self.config.sample_rate,
            return_tensors="pt"
        )

        if self.config.device == "cuda":
            inputs = {k: v.to(self.config.device) for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            generated_ids = await asyncio.to_thread(
                self.model.generate,
                **inputs,
                max_new_tokens=500
            )

        # Decode
        transcription = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return transcription

    async def transcribe_with_diarization(
        self,
        audio: np.ndarray,
        diarization: Annotation,
        meeting_id: str,
        sample_rate: int = 16000
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio using diarization segments

        This is the main method for the new pipeline:
        1. Diarization provides speaker segments with timestamps
        2. Each segment's audio is extracted and transcribed separately
        3. Results include both transcription and speaker labels

        Args:
            audio: Full audio data as numpy array
            diarization: Pyannote diarization annotation with speaker segments
            meeting_id: Meeting ID for tracking
            sample_rate: Audio sample rate (should be 16kHz)

        Returns:
            List of TranscriptSegment with text and speaker labels
        """
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start(
            "transcribe_with_diarization",
            meeting_id=meeting_id
        )

        segments = []

        try:
            # Get all tracks with speaker labels
            tracks = list(diarization.itertracks(yield_label=True))

            logger.info(f"Processing {len(tracks)} diarization segments")

            for i, (segment, _, speaker_label) in enumerate(tracks):
                # Extract audio chunk
                start_sample = int(segment.start * sample_rate)
                end_sample = int(segment.end * sample_rate)

                # Ensure within bounds
                start_sample = max(0, start_sample)
                end_sample = min(len(audio), end_sample)

                if start_sample >= end_sample:
                    continue

                audio_chunk = audio[start_sample:end_sample]

                # Resample if needed
                if sample_rate != self.config.sample_rate:
                    import librosa
                    audio_chunk = await asyncio.to_thread(
                        librosa.resample,
                        audio_chunk,
                        orig_sr=sample_rate,
                        target_sr=self.config.sample_rate
                    )

                # Transcribe segment
                transcript_segment = await self.transcribe_segment(
                    audio_chunk,
                    segment.start,
                    segment.end,
                    meeting_id,
                    speaker_label
                )

                # Only add non-empty segments
                if transcript_segment.text and transcript_segment.text != "[transcription failed]":
                    segments.append(transcript_segment)

                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.debug(f"Processed {i + 1}/{len(tracks)} segments")

            # Sort by start time
            segments.sort(key=lambda s: s.start_time)

            logger.log_operation_success(
                "transcribe_with_diarization",
                meeting_id=meeting_id,
                segment_count=len(segments),
                total_tracks=len(tracks)
            )

            return segments

        except Exception as e:
            logger.log_operation_failure(
                "transcribe_with_diarization",
                e,
                meeting_id=meeting_id
            )
            raise TranscriptionError(f"Failed to transcribe with diarization: {e}")

    async def transcribe(
        self,
        audio_path: Path,
        meeting_id: str,
        language: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """
        Transcribe entire audio file (without diarization)

        Note: This method transcribes the whole audio as a single segment.
        For speaker-aware transcription, use transcribe_with_diarization instead.

        Args:
            audio_path: Path to audio file
            meeting_id: Meeting ID for tracking
            language: Language code (ignored - Moonshine KR is Korean-only)

        Returns:
            List with single TranscriptSegment
        """
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start(
            "transcribe_audio",
            meeting_id=meeting_id,
            audio_path=str(audio_path)
        )

        try:
            # Load audio
            audio, sr = await asyncio.to_thread(sf.read, str(audio_path))
            audio = audio.astype(np.float32)

            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            # Resample if needed
            if sr != self.config.sample_rate:
                import librosa
                audio = await asyncio.to_thread(
                    librosa.resample,
                    audio,
                    orig_sr=sr,
                    target_sr=self.config.sample_rate
                )

            # Get duration
            duration = len(audio) / self.config.sample_rate

            # Transcribe
            text = await self._transcribe_audio(audio)

            segment = TranscriptSegment(
                meeting_id=meeting_id,
                start_time=0.0,
                end_time=duration,
                text=remove_repetition(text.strip()),
                confidence=None,
                speaker_label=None,
                speaker_id=None
            )

            logger.log_operation_success(
                "transcribe_audio",
                meeting_id=meeting_id,
                duration=f"{duration:.2f}s"
            )

            return [segment]

        except Exception as e:
            logger.log_operation_failure(
                "transcribe_audio",
                e,
                meeting_id=meeting_id
            )
            raise TranscriptionError(f"Failed to transcribe audio: {e}")

    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about loaded model

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.config.model_name,
            "device": self.config.device,
            "backend": "onnx" if self._use_onnx else "transformers",
            "initialized": self._is_initialized,
            "min_segment_duration": self.config.min_segment_duration,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and unload models
        """
        logger.info("Cleaning up Moonshine resources")

        if self.model is not None:
            del self.model
            self.model = None

        if self.processor is not None:
            del self.processor
            self.processor = None

        self._is_initialized = False

        # Force garbage collection
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Moonshine cleanup complete")


# Factory function
def get_moonshine_engine(
    model_name: Optional[str] = None,
    device: Optional[str] = None
) -> MoonshineEngine:
    """
    Create Moonshine engine instance

    Args:
        model_name: Model name (defaults to config)
        device: Device to use (defaults to auto-detect)

    Returns:
        MoonshineEngine instance
    """
    config = MoonshineConfig(
        model_name=model_name or MOONSHINE_MODEL
    )

    if device:
        config.device = device

    return MoonshineEngine(config)
