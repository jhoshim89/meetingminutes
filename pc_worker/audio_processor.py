"""
Audio Processing Module
Handles audio download, preprocessing, and validation
"""

import asyncio
from pathlib import Path
from typing import Optional, Tuple, List
import librosa
import soundfile as sf
import numpy as np
import noisereduce as nr
from scipy import signal

from models import AudioMetadata
from exceptions import (
    AudioDownloadError,
    AudioCorruptedError,
    AudioPreprocessingError
)
from logger import get_logger
from utils import validate_audio_file, get_file_size_mb

logger = get_logger("audio_processor")


class AudioProcessor:
    """
    Handles all audio processing operations including download,
    validation, and preprocessing
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        normalize: bool = True,
        remove_silence: bool = False
    ):
        """
        Initialize audio processor

        Args:
            target_sample_rate: Target sample rate for processing (default: 16kHz for WhisperX)
            normalize: Whether to normalize audio
            remove_silence: Whether to remove silence segments
        """
        self.target_sample_rate = target_sample_rate
        self.normalize = normalize
        self.remove_silence = remove_silence

    async def download_audio(
        self,
        url: str,
        destination: Path,
        meeting_id: str
    ) -> Path:
        """
        Download audio from URL

        Args:
            url: Audio file URL
            destination: Local path to save audio
            meeting_id: Meeting ID for logging

        Returns:
            Path to downloaded audio file

        Raises:
            AudioDownloadError: If download fails
        """
        from supabase_client import get_supabase_client

        logger.log_operation_start("download_audio", meeting_id=meeting_id)

        try:
            supabase = get_supabase_client()
            audio_path = await supabase.download_audio_file(
                meeting_id=meeting_id,
                url=url,
                destination=destination
            )

            # Validate downloaded file
            if not validate_audio_file(audio_path):
                raise AudioDownloadError(
                    f"Downloaded file failed validation: {audio_path}"
                )

            logger.log_operation_success(
                "download_audio",
                meeting_id=meeting_id,
                file_size_mb=f"{get_file_size_mb(audio_path):.2f}"
            )

            return audio_path

        except Exception as e:
            logger.log_operation_failure("download_audio", e, meeting_id=meeting_id)
            raise

    async def load_audio(self, file_path: Path) -> Tuple[np.ndarray, int]:
        """
        Load audio file using librosa

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (audio_data, sample_rate)

        Raises:
            AudioCorruptedError: If audio file cannot be loaded
        """
        try:
            logger.debug(f"Loading audio file: {file_path}")

            # Load audio in a thread to avoid blocking
            audio_data, sample_rate = await asyncio.to_thread(
                librosa.load,
                file_path,
                sr=None,  # Keep original sample rate initially
                mono=True  # Convert to mono
            )

            if audio_data is None or len(audio_data) == 0:
                raise AudioCorruptedError("Audio data is empty after loading")

            logger.debug(
                f"Loaded audio: duration={len(audio_data)/sample_rate:.2f}s, "
                f"sample_rate={sample_rate}Hz"
            )

            return audio_data, sample_rate

        except Exception as e:
            logger.error(f"Failed to load audio file {file_path}: {e}")
            raise AudioCorruptedError(f"Cannot load audio file: {e}")

    async def preprocess_audio(
        self,
        input_path: Path,
        output_path: Path,
        meeting_id: str
    ) -> AudioMetadata:
        """
        Preprocess audio file: resample, normalize, and convert to WAV

        Args:
            input_path: Path to input audio file
            output_path: Path to save processed audio
            meeting_id: Meeting ID for logging

        Returns:
            AudioMetadata with processed audio information

        Raises:
            AudioPreprocessingError: If preprocessing fails
        """
        logger.log_operation_start("preprocess_audio", meeting_id=meeting_id)

        try:
            # Load audio
            audio_data, original_sr = await self.load_audio(input_path)

            # Resample if needed
            if original_sr != self.target_sample_rate:
                logger.debug(
                    f"Resampling from {original_sr}Hz to {self.target_sample_rate}Hz"
                )
                audio_data = await asyncio.to_thread(
                    librosa.resample,
                    audio_data,
                    orig_sr=original_sr,
                    target_sr=self.target_sample_rate
                )

            # Normalize audio
            if self.normalize:
                audio_data = self._normalize_audio(audio_data)

            # Remove silence if requested
            if self.remove_silence:
                audio_data = await self._remove_silence(audio_data, self.target_sample_rate)

            # Save processed audio
            await asyncio.to_thread(
                sf.write,
                output_path,
                audio_data,
                self.target_sample_rate,
                format='WAV',
                subtype='PCM_16'
            )

            # Create metadata
            duration = len(audio_data) / self.target_sample_rate
            size_bytes = output_path.stat().st_size

            metadata = AudioMetadata(
                file_path=str(output_path),
                duration_seconds=duration,
                sample_rate=self.target_sample_rate,
                channels=1,  # We convert to mono
                format='WAV',
                size_bytes=size_bytes
            )

            logger.log_operation_success(
                "preprocess_audio",
                meeting_id=meeting_id,
                duration_s=f"{duration:.2f}",
                size_mb=f"{size_bytes / 1024 / 1024:.2f}"
            )

            return metadata

        except AudioCorruptedError:
            # Re-raise audio corrupted errors
            raise
        except Exception as e:
            logger.log_operation_failure("preprocess_audio", e, meeting_id=meeting_id)
            raise AudioPreprocessingError(f"Failed to preprocess audio: {e}")

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio to [-1, 1] range

        Args:
            audio_data: Audio samples

        Returns:
            Normalized audio data
        """
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            return audio_data / max_val
        return audio_data

    async def _remove_silence(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        top_db: int = 30
    ) -> np.ndarray:
        """
        Remove silence from audio using librosa

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            top_db: Threshold for silence detection

        Returns:
            Audio with silence removed
        """
        try:
            # Split audio into non-silent intervals
            intervals = await asyncio.to_thread(
                librosa.effects.split,
                audio_data,
                top_db=top_db
            )

            # Concatenate non-silent segments
            if len(intervals) > 0:
                segments = [audio_data[start:end] for start, end in intervals]
                return np.concatenate(segments)
            else:
                # If no non-silent segments, return original
                return audio_data

        except Exception as e:
            logger.warning(f"Failed to remove silence: {e}. Using original audio.")
            return audio_data

    async def validate_audio_format(self, file_path: Path) -> bool:
        """
        Validate that audio file can be loaded and processed

        Args:
            file_path: Path to audio file

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to load a small portion of the file
            audio_data, sample_rate = await asyncio.to_thread(
                librosa.load,
                file_path,
                sr=None,
                duration=5.0  # Load only first 5 seconds
            )

            # Check basic validity
            if audio_data is None or len(audio_data) == 0:
                return False

            if sample_rate < 8000 or sample_rate > 192000:
                return False

            return True

        except Exception as e:
            logger.error(f"Audio validation failed for {file_path}: {e}")
            return False

    async def get_audio_duration(self, file_path: Path) -> float:
        """
        Get audio duration in seconds

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds

        Raises:
            AudioCorruptedError: If duration cannot be determined
        """
        try:
            duration = await asyncio.to_thread(
                librosa.get_duration,
                path=file_path
            )
            return duration

        except Exception as e:
            logger.error(f"Failed to get audio duration for {file_path}: {e}")
            raise AudioCorruptedError(f"Cannot determine audio duration: {e}")

    async def save_processed_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        output_path: Path
    ) -> Path:
        """
        Save processed audio to file

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            output_path: Path to save audio

        Returns:
            Path to saved audio file

        Raises:
            AudioPreprocessingError: If save fails
        """
        try:
            await asyncio.to_thread(
                sf.write,
                output_path,
                audio_data,
                sample_rate,
                format='WAV',
                subtype='PCM_16'
            )

            if not output_path.exists():
                raise AudioPreprocessingError("Failed to save audio file")

            return output_path

        except Exception as e:
            logger.error(f"Failed to save processed audio: {e}")
            raise AudioPreprocessingError(f"Cannot save audio: {e}")

    async def reduce_noise(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        stationary: bool = True
    ) -> np.ndarray:
        """
        Reduce noise in audio using spectral gating

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            stationary: Whether noise is stationary (True for background noise)

        Returns:
            Noise-reduced audio data
        """
        try:
            logger.debug("Applying noise reduction")

            # Use noisereduce library
            reduced_audio = await asyncio.to_thread(
                nr.reduce_noise,
                y=audio_data,
                sr=sample_rate,
                stationary=stationary,
                prop_decrease=0.8  # Aggressive noise reduction
            )

            return reduced_audio

        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}. Using original audio.")
            return audio_data

    async def detect_voice_activity(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2
    ) -> List[Tuple[float, float]]:
        """
        Detect voice activity in audio (Voice Activity Detection - VAD)

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            frame_duration_ms: Frame duration in milliseconds (10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)

        Returns:
            List of (start_time, end_time) tuples for voice segments
        """
        try:
            logger.debug("Detecting voice activity")

            # Use librosa's energy-based VAD
            # Calculate frame length in samples
            hop_length = int(sample_rate * frame_duration_ms / 1000)

            # Compute RMS energy
            rms = librosa.feature.rms(
                y=audio_data,
                frame_length=hop_length * 2,
                hop_length=hop_length
            )[0]

            # Threshold based on aggressiveness
            threshold_multiplier = 0.5 + (aggressiveness * 0.1)
            threshold = np.median(rms) * threshold_multiplier

            # Find frames above threshold
            voice_frames = rms > threshold

            # Convert frames to time segments
            segments = []
            in_segment = False
            start_time = 0.0

            for i, is_voice in enumerate(voice_frames):
                current_time = i * frame_duration_ms / 1000.0

                if is_voice and not in_segment:
                    # Start of voice segment
                    start_time = current_time
                    in_segment = True
                elif not is_voice and in_segment:
                    # End of voice segment
                    segments.append((start_time, current_time))
                    in_segment = False

            # Close final segment if needed
            if in_segment:
                segments.append((start_time, len(voice_frames) * frame_duration_ms / 1000.0))

            logger.debug(f"Detected {len(segments)} voice segments")
            return segments

        except Exception as e:
            logger.warning(f"VAD failed: {e}. Assuming entire audio is voice.")
            duration = len(audio_data) / sample_rate
            return [(0.0, duration)]

    async def split_audio_chunks(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        chunk_duration_seconds: float = 10.0,
        overlap_seconds: float = 1.0
    ) -> List[Tuple[np.ndarray, float, float]]:
        """
        Split audio into chunks for batch processing

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            chunk_duration_seconds: Duration of each chunk
            overlap_seconds: Overlap between chunks

        Returns:
            List of (chunk_audio, start_time, end_time) tuples
        """
        try:
            logger.debug(
                f"Splitting audio into {chunk_duration_seconds}s chunks "
                f"with {overlap_seconds}s overlap"
            )

            total_duration = len(audio_data) / sample_rate
            chunk_samples = int(chunk_duration_seconds * sample_rate)
            overlap_samples = int(overlap_seconds * sample_rate)
            step_samples = chunk_samples - overlap_samples

            chunks = []
            current_pos = 0

            while current_pos < len(audio_data):
                # Extract chunk
                chunk_end = min(current_pos + chunk_samples, len(audio_data))
                chunk = audio_data[current_pos:chunk_end]

                # Calculate times
                start_time = current_pos / sample_rate
                end_time = chunk_end / sample_rate

                chunks.append((chunk, start_time, end_time))

                # Move to next chunk
                current_pos += step_samples

                # Break if we've covered the entire audio
                if chunk_end >= len(audio_data):
                    break

            logger.debug(f"Created {len(chunks)} audio chunks")
            return chunks

        except Exception as e:
            logger.error(f"Failed to split audio into chunks: {e}")
            raise AudioPreprocessingError(f"Cannot split audio: {e}")

    async def apply_bandpass_filter(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        lowcut: float = 80.0,
        highcut: float = 8000.0,
        order: int = 5
    ) -> np.ndarray:
        """
        Apply bandpass filter to focus on speech frequencies

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            lowcut: Low cutoff frequency (Hz)
            highcut: High cutoff frequency (Hz)
            order: Filter order

        Returns:
            Filtered audio data
        """
        try:
            logger.debug(f"Applying bandpass filter: {lowcut}-{highcut} Hz")

            # Calculate normalized frequencies
            nyquist = 0.5 * sample_rate
            low = lowcut / nyquist
            high = highcut / nyquist

            # Design Butterworth bandpass filter
            b, a = await asyncio.to_thread(
                signal.butter,
                order,
                [low, high],
                btype='band'
            )

            # Apply filter
            filtered_audio = await asyncio.to_thread(
                signal.filtfilt,
                b, a,
                audio_data
            )

            return filtered_audio

        except Exception as e:
            logger.warning(f"Bandpass filter failed: {e}. Using original audio.")
            return audio_data

    async def enhance_audio_for_stt(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> np.ndarray:
        """
        Apply comprehensive audio enhancement for STT

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate

        Returns:
            Enhanced audio data
        """
        logger.debug("Enhancing audio for STT")

        try:
            # Step 1: Noise reduction
            audio_data = await self.reduce_noise(audio_data, sample_rate)

            # Step 2: Bandpass filter for speech frequencies
            audio_data = await self.apply_bandpass_filter(audio_data, sample_rate)

            # Step 3: Normalize
            audio_data = self._normalize_audio(audio_data)

            logger.debug("Audio enhancement complete")
            return audio_data

        except Exception as e:
            logger.warning(f"Audio enhancement failed: {e}")
            return audio_data


# Factory function
def get_audio_processor(
    target_sample_rate: int = 16000,
    normalize: bool = True,
    remove_silence: bool = False
) -> AudioProcessor:
    """
    Create audio processor instance

    Args:
        target_sample_rate: Target sample rate
        normalize: Whether to normalize
        remove_silence: Whether to remove silence

    Returns:
        AudioProcessor instance
    """
    return AudioProcessor(
        target_sample_rate=target_sample_rate,
        normalize=normalize,
        remove_silence=remove_silence
    )
