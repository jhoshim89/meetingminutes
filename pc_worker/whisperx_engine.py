"""
WhisperX STT Engine Module
Handles audio transcription using WhisperX with Korean language support
"""

# Import config first to apply PyTorch 2.6+ compatibility patch
from config import WHISPERX_MODEL, ENABLE_GPU, CUDA_DEVICE, MODEL_CACHE_DIR

import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import torch
import whisperx
import soundfile as sf
from dataclasses import dataclass

from models import TranscriptSegment
from exceptions import TranscriptionError
from logger import get_logger

logger = get_logger("whisperx_engine")


@dataclass
class WhisperXConfig:
    """Configuration for WhisperX engine"""
    model_size: str = "large-v2"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type: str = "float16" if torch.cuda.is_available() else "int8"
    language: str = "ko"  # Korean
    batch_size: int = 16
    confidence_threshold: float = 0.4  # 한국어는 0.4 권장 (영어 대비 신뢰도 낮게 나옴)
    chunk_length_seconds: int = 30
    # VAD (Voice Activity Detection) options
    # WhisperX 기본값: onset=0.5, offset=0.363
    # ⚠️ pyannote.audio 버전 불일치(0.0.1 vs 3.4.0)로 낮은 VAD 값이 오작동할 수 있음
    # 권장: 기본값(0.5) 사용, 조용한 오디오는 0.3으로 테스트
    vad_onset: float = 0.3  # Speech start threshold (0.3으로 낮춰서 조용한 음성도 감지)
    vad_offset: float = 0.363  # Speech end threshold (기본값 0.363 권장)
    vad_chunk_size: int = 30  # VAD chunk size in seconds (silero/pyannote용)

    def __post_init__(self):
        """Validate configuration"""
        if not ENABLE_GPU and self.device == "cuda":
            logger.warning("GPU disabled in config, forcing CPU mode")
            self.device = "cpu"
            self.compute_type = "int8"


class WhisperXEngine:
    """
    WhisperX-based Speech-to-Text engine with Korean language optimization
    Handles batch transcription with word-level timestamps
    """

    def __init__(self, config: Optional[WhisperXConfig] = None):
        """
        Initialize WhisperX engine

        Args:
            config: WhisperX configuration (uses defaults if None)
        """
        self.config = config or WhisperXConfig()
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self._is_initialized = False

        logger.info(
            f"WhisperX Engine initialized with: "
            f"model={self.config.model_size}, "
            f"device={self.config.device}, "
            f"language={self.config.language}"
        )

    async def initialize(self) -> None:
        """
        Load WhisperX models asynchronously

        Raises:
            TranscriptionError: If model loading fails
        """
        if self._is_initialized:
            logger.debug("WhisperX already initialized")
            return

        logger.log_operation_start("initialize_whisperx_model")

        try:
            # Load main transcription model with VAD options
            logger.info(f"Loading WhisperX model: {self.config.model_size}")
            logger.info(f"VAD options: onset={self.config.vad_onset}, offset={self.config.vad_offset}")

            vad_options = {
                "vad_onset": self.config.vad_onset,
                "vad_offset": self.config.vad_offset,
                "chunk_size": self.config.vad_chunk_size
            }

            self.model = await asyncio.to_thread(
                whisperx.load_model,
                self.config.model_size,
                self.config.device,
                compute_type=self.config.compute_type,
                download_root=str(MODEL_CACHE_DIR),
                vad_options=vad_options
            )

            # Load alignment model for word-level timestamps (Korean)
            logger.info(f"Loading alignment model for language: {self.config.language}")
            self.align_model, self.align_metadata = await asyncio.to_thread(
                whisperx.load_align_model,
                language_code=self.config.language,
                device=self.config.device
            )

            self._is_initialized = True

            logger.log_operation_success(
                "initialize_whisperx_model",
                device=self.config.device,
                model_size=self.config.model_size
            )

        except Exception as e:
            logger.log_operation_failure("initialize_whisperx_model", e)
            raise TranscriptionError(f"Failed to initialize WhisperX: {e}")

    async def transcribe(
        self,
        audio_path: Path,
        meeting_id: str,
        language: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio file to text with timestamps

        Args:
            audio_path: Path to audio file (WAV format, 16kHz recommended)
            meeting_id: Meeting ID for logging and result tracking
            language: Language code (defaults to config language)

        Returns:
            List of transcript segments with timestamps and text

        Raises:
            TranscriptionError: If transcription fails
        """
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start(
            "transcribe_audio",
            meeting_id=meeting_id,
            audio_path=str(audio_path)
        )

        try:
            # Load audio using our own loader to avoid ffmpeg PATH issues
            logger.debug(f"Loading audio from {audio_path}")
            audio = await self._load_audio(audio_path)

            # Run transcription
            lang = language or self.config.language
            logger.info(f"Starting transcription (language={lang})")

            result = await asyncio.to_thread(
                self._transcribe_with_model,
                audio,
                lang
            )

            # Align transcript for word-level timestamps
            logger.debug("Aligning transcript for word-level timestamps")
            aligned_result = await asyncio.to_thread(
                whisperx.align,
                result["segments"],
                self.align_model,
                self.align_metadata,
                audio,
                self.config.device,
                return_char_alignments=False
            )

            # Convert to TranscriptSegment objects
            segments = self._convert_to_segments(
                aligned_result["segments"],
                meeting_id
            )

            # Filter by confidence threshold
            segments = [
                seg for seg in segments
                if seg.confidence is None or seg.confidence >= self.config.confidence_threshold
            ]

            logger.log_operation_success(
                "transcribe_audio",
                meeting_id=meeting_id,
                segment_count=len(segments),
                language=lang
            )

            return segments

        except Exception as e:
            logger.log_operation_failure(
                "transcribe_audio",
                e,
                meeting_id=meeting_id
            )
            raise TranscriptionError(f"Failed to transcribe audio: {e}")

    async def _load_audio(self, audio_path: Path) -> np.ndarray:
        """
        Load audio file in WhisperX-compatible format (float32, 16kHz, mono)

        Uses soundfile for WAV files and ffmpeg via imageio_ffmpeg for other formats.
        This avoids the PATH issues with WhisperX's internal load_audio function.

        Args:
            audio_path: Path to audio file

        Returns:
            Audio data as numpy array (float32, 16kHz)
        """
        import subprocess
        import tempfile

        audio_path = Path(audio_path)
        SAMPLE_RATE = 16000  # WhisperX requires 16kHz

        # For WAV files, try soundfile first
        if audio_path.suffix.lower() == '.wav':
            try:
                audio_data, sr = await asyncio.to_thread(sf.read, str(audio_path))
                audio_data = audio_data.astype(np.float32)

                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)

                # Resample if needed
                if sr != SAMPLE_RATE:
                    import librosa
                    audio_data = await asyncio.to_thread(
                        librosa.resample,
                        audio_data,
                        orig_sr=sr,
                        target_sr=SAMPLE_RATE
                    )

                return audio_data
            except Exception as e:
                logger.warning(f"soundfile failed to load WAV: {e}, trying ffmpeg")

        # For other formats or if soundfile failed, use ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_path = "ffmpeg"

        def _load_with_ffmpeg():
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_wav = tmp.name

            try:
                cmd = [
                    ffmpeg_path,
                    '-i', str(audio_path),
                    '-ar', str(SAMPLE_RATE),
                    '-ac', '1',
                    '-f', 'wav',
                    '-y',
                    temp_wav
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    raise Exception(f"ffmpeg error: {result.stderr}")

                audio_data, _ = sf.read(temp_wav)
                return audio_data.astype(np.float32)
            finally:
                import os
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)

        audio_data = await asyncio.to_thread(_load_with_ffmpeg)
        logger.debug(f"Loaded audio: {len(audio_data)/SAMPLE_RATE:.2f}s @ {SAMPLE_RATE}Hz")
        return audio_data

    def _transcribe_with_model(self, audio: np.ndarray, language: str) -> Dict:
        """
        Run transcription with WhisperX model (blocking operation)

        Args:
            audio: Audio data as numpy array
            language: Language code

        Returns:
            Raw transcription result from WhisperX
        """
        return self.model.transcribe(
            audio,
            batch_size=self.config.batch_size,
            language=language,
            chunk_size=self.config.chunk_length_seconds
        )

    def _convert_to_segments(
        self,
        whisperx_segments: List[Dict],
        meeting_id: str
    ) -> List[TranscriptSegment]:
        """
        Convert WhisperX segments to TranscriptSegment models

        Args:
            whisperx_segments: Raw segments from WhisperX
            meeting_id: Meeting ID

        Returns:
            List of TranscriptSegment objects
        """
        segments = []

        for seg in whisperx_segments:
            try:
                # Extract confidence if available (from words)
                confidence = None
                if "words" in seg and seg["words"]:
                    # Average confidence from words
                    word_confidences = [
                        w.get("score", 1.0) for w in seg["words"]
                        if "score" in w
                    ]
                    if word_confidences:
                        confidence = sum(word_confidences) / len(word_confidences)

                segment = TranscriptSegment(
                    meeting_id=meeting_id,
                    start_time=float(seg["start"]),
                    end_time=float(seg["end"]),
                    text=seg["text"].strip(),
                    confidence=confidence,
                    speaker_id=None,  # Will be filled by diarization
                    speaker_label=None
                )

                segments.append(segment)

            except Exception as e:
                logger.warning(f"Failed to convert segment {seg}: {e}")
                continue

        return segments

    async def transcribe_batch(
        self,
        audio_paths: List[Path],
        meeting_ids: List[str],
        language: Optional[str] = None
    ) -> Dict[str, List[TranscriptSegment]]:
        """
        Transcribe multiple audio files in batch

        Args:
            audio_paths: List of audio file paths
            meeting_ids: List of meeting IDs (must match audio_paths length)
            language: Language code (defaults to config language)

        Returns:
            Dictionary mapping meeting_id to transcript segments

        Raises:
            TranscriptionError: If batch transcription fails
            ValueError: If audio_paths and meeting_ids lengths don't match
        """
        if len(audio_paths) != len(meeting_ids):
            raise ValueError("audio_paths and meeting_ids must have same length")

        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Starting batch transcription for {len(audio_paths)} files")

        results = {}

        # Process each file (can be parallelized further if needed)
        for audio_path, meeting_id in zip(audio_paths, meeting_ids):
            try:
                segments = await self.transcribe(audio_path, meeting_id, language)
                results[meeting_id] = segments
            except Exception as e:
                logger.error(f"Failed to transcribe {meeting_id}: {e}")
                results[meeting_id] = []

        logger.info(f"Batch transcription complete: {len(results)} results")

        return results

    async def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages

        Returns:
            List of language codes
        """
        # WhisperX supports all Whisper languages
        return [
            "ko",  # Korean
            "en",  # English
            "ja",  # Japanese
            "zh",  # Chinese
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "ru",  # Russian
            # ... and 90+ more languages
        ]

    async def estimate_processing_time(
        self,
        audio_duration_seconds: float
    ) -> float:
        """
        Estimate processing time for given audio duration

        Args:
            audio_duration_seconds: Audio duration in seconds

        Returns:
            Estimated processing time in seconds
        """
        # Rough estimates based on device
        if self.config.device == "cuda":
            # GPU: approximately 0.1x-0.2x real-time
            return audio_duration_seconds * 0.15
        else:
            # CPU: approximately 0.5x-1x real-time
            return audio_duration_seconds * 0.75

    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about loaded model

        Returns:
            Dictionary with model information
        """
        return {
            "model_size": self.config.model_size,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "language": self.config.language,
            "batch_size": self.config.batch_size,
            "confidence_threshold": self.config.confidence_threshold,
            "initialized": self._is_initialized,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and unload models
        """
        logger.info("Cleaning up WhisperX resources")

        if self.model is not None:
            del self.model
            self.model = None

        if self.align_model is not None:
            del self.align_model
            self.align_model = None

        self.align_metadata = None
        self._is_initialized = False

        # Force garbage collection
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("WhisperX cleanup complete")


# Factory function
def get_whisperx_engine(
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    language: str = "ko"
) -> WhisperXEngine:
    """
    Create WhisperX engine instance

    Args:
        model_size: Model size (defaults to config)
        device: Device to use (defaults to auto-detect)
        language: Target language code

    Returns:
        WhisperXEngine instance
    """
    config = WhisperXConfig(
        model_size=model_size or WHISPERX_MODEL,
        language=language
    )

    if device:
        config.device = device

    return WhisperXEngine(config)
