"""
Speaker Diarization Module
Handles speaker identification and segmentation using pyannote.audio
"""

# Import config first to apply PyTorch 2.6+ compatibility patch
from config import DIARIZATION_MODEL, ENABLE_GPU, CUDA_DEVICE, MODEL_CACHE_DIR, HUGGINGFACE_TOKEN

import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import torch
import numpy as np

from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from pyannote.core import Annotation, Segment

from models import TranscriptSegment, SpeakerEmbedding
from exceptions import DiarizationError
from logger import get_logger

logger = get_logger("speaker_diarization")


class SpeakerDiarizationEngine:
    """
    Speaker diarization engine using pyannote.audio
    Identifies and separates different speakers in audio
    """

    def __init__(
        self,
        model_name: str = DIARIZATION_MODEL,
        use_auth_token: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Initialize speaker diarization engine

        Args:
            model_name: Pretrained model name from HuggingFace
            use_auth_token: HuggingFace authentication token (required for some models)
            device: Device to use (cuda/cpu), auto-detects if None
        """
        self.model_name = model_name
        self.use_auth_token = use_auth_token
        self.device = device or ("cuda" if ENABLE_GPU and torch.cuda.is_available() else "cpu")
        self.pipeline = None
        self._is_initialized = False

        logger.info(
            f"Speaker Diarization Engine initialized: "
            f"model={model_name}, device={self.device}"
        )

    async def initialize(self) -> None:
        """
        Load diarization pipeline asynchronously

        Raises:
            DiarizationError: If pipeline loading fails
        """
        if self._is_initialized:
            logger.debug("Diarization pipeline already initialized")
            return

        logger.log_operation_start("initialize_diarization_pipeline")

        try:
            # Load pretrained pipeline from HuggingFace
            logger.info(f"Loading diarization model: {self.model_name}")

            self.pipeline = await asyncio.to_thread(
                Pipeline.from_pretrained,
                self.model_name,
                use_auth_token=self.use_auth_token,
                cache_dir=str(MODEL_CACHE_DIR)
            )

            # Move to appropriate device
            if self.device == "cuda":
                await asyncio.to_thread(self.pipeline.to, torch.device(f"cuda:{CUDA_DEVICE}"))

            self._is_initialized = True

            logger.log_operation_success(
                "initialize_diarization_pipeline",
                device=self.device,
                model=self.model_name
            )

        except Exception as e:
            logger.log_operation_failure("initialize_diarization_pipeline", e)
            raise DiarizationError(f"Failed to initialize diarization pipeline: {e}")

    async def diarize(
        self,
        audio_path: Path,
        meeting_id: str,
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 10
    ) -> Annotation:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to audio file (WAV format recommended)
            meeting_id: Meeting ID for logging
            num_speakers: Number of speakers (if known, improves accuracy)
            min_speakers: Minimum number of speakers to detect
            max_speakers: Maximum number of speakers to detect

        Returns:
            Pyannote Annotation object with speaker segments

        Raises:
            DiarizationError: If diarization fails
        """
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start(
            "diarize_audio",
            meeting_id=meeting_id,
            audio_path=str(audio_path)
        )

        try:
            # Prepare diarization parameters
            params = {
                "min_speakers": min_speakers,
                "max_speakers": max_speakers
            }
            if num_speakers is not None:
                params["num_speakers"] = num_speakers

            logger.info(
                f"Starting diarization with params: {params}"
            )

            # Run diarization
            diarization = await asyncio.to_thread(
                self._run_diarization,
                str(audio_path),
                params
            )

            # Log statistics
            speakers = list(diarization.labels())
            total_speech_duration = sum(
                segment.duration for segment, _ in diarization.itertracks()
            )

            logger.log_operation_success(
                "diarize_audio",
                meeting_id=meeting_id,
                num_speakers=len(speakers),
                total_speech_duration=f"{total_speech_duration:.2f}s"
            )

            return diarization

        except Exception as e:
            logger.log_operation_failure(
                "diarize_audio",
                e,
                meeting_id=meeting_id
            )
            raise DiarizationError(f"Failed to diarize audio: {e}")

    def _run_diarization(self, audio_path: str, params: Dict) -> Annotation:
        """
        Run diarization pipeline (blocking operation)

        Args:
            audio_path: Path to audio file
            params: Diarization parameters

        Returns:
            Annotation object
        """
        return self.pipeline(audio_path, **params)

    async def align_with_transcript(
        self,
        diarization: Annotation,
        transcript_segments: List[TranscriptSegment],
        meeting_id: str
    ) -> List[TranscriptSegment]:
        """
        Align diarization results with transcript segments

        Args:
            diarization: Diarization annotation from pyannote
            transcript_segments: List of transcript segments from WhisperX
            meeting_id: Meeting ID for logging

        Returns:
            Updated transcript segments with speaker labels

        Raises:
            DiarizationError: If alignment fails
        """
        logger.log_operation_start(
            "align_diarization_transcript",
            meeting_id=meeting_id
        )

        try:
            aligned_segments = []

            for segment in transcript_segments:
                # Find overlapping speaker segments
                segment_duration = segment.end_time - segment.start_time
                segment_midpoint = segment.start_time + (segment_duration / 2)

                # Create pyannote Segment for overlap calculation
                pyannote_segment = Segment(segment.start_time, segment.end_time)

                # Find best matching speaker
                best_speaker = None
                best_overlap = 0.0

                for track, speaker_label in diarization.itertracks():
                    # Calculate overlap
                    overlap_segment = track & pyannote_segment  # Intersection
                    if overlap_segment:
                        overlap_duration = overlap_segment.duration
                        overlap_ratio = overlap_duration / segment_duration

                        if overlap_ratio > best_overlap:
                            best_overlap = overlap_ratio
                            best_speaker = speaker_label

                # Update segment with speaker information
                updated_segment = TranscriptSegment(
                    meeting_id=segment.meeting_id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=segment.text,
                    confidence=segment.confidence,
                    speaker_label=best_speaker,
                    speaker_id=None  # Will be mapped later
                )

                aligned_segments.append(updated_segment)

            # Calculate alignment statistics
            segments_with_speaker = sum(
                1 for seg in aligned_segments if seg.speaker_label is not None
            )
            alignment_rate = segments_with_speaker / len(aligned_segments) if aligned_segments else 0

            logger.log_operation_success(
                "align_diarization_transcript",
                meeting_id=meeting_id,
                total_segments=len(aligned_segments),
                aligned_segments=segments_with_speaker,
                alignment_rate=f"{alignment_rate*100:.1f}%"
            )

            return aligned_segments

        except Exception as e:
            logger.log_operation_failure(
                "align_diarization_transcript",
                e,
                meeting_id=meeting_id
            )
            raise DiarizationError(f"Failed to align diarization with transcript: {e}")

    async def extract_speaker_embeddings(
        self,
        audio_path: Path,
        diarization: Annotation,
        meeting_id: str
    ) -> Dict[str, SpeakerEmbedding]:
        """
        Extract voice embeddings for each speaker

        Args:
            audio_path: Path to audio file
            diarization: Diarization annotation
            meeting_id: Meeting ID for logging

        Returns:
            Dictionary mapping speaker_label to SpeakerEmbedding

        Raises:
            DiarizationError: If embedding extraction fails
        """
        logger.log_operation_start(
            "extract_speaker_embeddings",
            meeting_id=meeting_id
        )

        try:
            from pyannote.audio import Model
            from pyannote.audio.pipelines.utils import get_devices
            import torchaudio

            # Load embedding model
            embedding_model = await asyncio.to_thread(
                Model.from_pretrained,
                "pyannote/embedding",
                use_auth_token=self.use_auth_token,
                cache_dir=str(MODEL_CACHE_DIR)
            )

            if self.device == "cuda":
                embedding_model = embedding_model.to(torch.device(f"cuda:{CUDA_DEVICE}"))

            # Load audio
            waveform, sample_rate = await asyncio.to_thread(
                torchaudio.load,
                str(audio_path)
            )

            if self.device == "cuda":
                waveform = waveform.to(torch.device(f"cuda:{CUDA_DEVICE}"))

            speaker_embeddings = {}

            # Extract embeddings for each speaker
            for speaker_label in diarization.labels():
                # Get all segments for this speaker
                speaker_timeline = diarization.label_timeline(speaker_label)

                embeddings_list = []
                sample_count = 0

                # Extract embeddings from each segment
                for segment in speaker_timeline:
                    try:
                        # Extract audio chunk
                        start_sample = int(segment.start * sample_rate)
                        end_sample = int(segment.end * sample_rate)

                        if start_sample >= waveform.shape[1] or end_sample > waveform.shape[1]:
                            continue

                        chunk = waveform[:, start_sample:end_sample]

                        # Skip very short segments (< 0.5 seconds)
                        if chunk.shape[1] < sample_rate * 0.5:
                            continue

                        # Extract embedding
                        with torch.no_grad():
                            embedding = await asyncio.to_thread(
                                embedding_model,
                                chunk.unsqueeze(0)
                            )
                            embeddings_list.append(embedding.cpu().numpy().flatten())
                            sample_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to extract embedding for segment {segment}: {e}")
                        continue

                # Average embeddings for this speaker
                if embeddings_list:
                    avg_embedding = np.mean(embeddings_list, axis=0)

                    speaker_embeddings[speaker_label] = SpeakerEmbedding(
                        speaker_id=speaker_label,
                        embedding=avg_embedding.tolist(),
                        sample_count=sample_count,
                        confidence=None  # Could calculate variance as confidence
                    )

            logger.log_operation_success(
                "extract_speaker_embeddings",
                meeting_id=meeting_id,
                num_speakers=len(speaker_embeddings)
            )

            return speaker_embeddings

        except Exception as e:
            logger.log_operation_failure(
                "extract_speaker_embeddings",
                e,
                meeting_id=meeting_id
            )
            raise DiarizationError(f"Failed to extract speaker embeddings: {e}")

    async def get_speaker_statistics(
        self,
        diarization: Annotation
    ) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for each speaker

        Args:
            diarization: Diarization annotation

        Returns:
            Dictionary mapping speaker_label to statistics
        """
        stats = {}

        for speaker_label in diarization.labels():
            timeline = diarization.label_timeline(speaker_label)

            # Calculate statistics
            total_duration = sum(segment.duration for segment in timeline)
            num_segments = len(list(timeline))
            avg_segment_duration = total_duration / num_segments if num_segments > 0 else 0

            stats[speaker_label] = {
                "total_duration_seconds": total_duration,
                "num_segments": num_segments,
                "avg_segment_duration": avg_segment_duration,
                "speech_ratio": 0.0  # Will be calculated with total audio duration
            }

        return stats

    def get_pipeline_info(self) -> Dict[str, any]:
        """
        Get information about loaded pipeline

        Returns:
            Dictionary with pipeline information
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "initialized": self._is_initialized,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }

    async def cleanup(self) -> None:
        """
        Clean up resources and unload models
        """
        logger.info("Cleaning up diarization resources")

        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None

        self._is_initialized = False

        # Force garbage collection
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Diarization cleanup complete")


# Factory function
def get_diarization_engine(
    model_name: Optional[str] = None,
    use_auth_token: Optional[str] = None,
    device: Optional[str] = None
) -> SpeakerDiarizationEngine:
    """
    Create speaker diarization engine instance

    Args:
        model_name: Model name (defaults to config)
        use_auth_token: HuggingFace auth token
        device: Device to use (defaults to auto-detect)

    Returns:
        SpeakerDiarizationEngine instance
    """
    # Use provided token, or fall back to config
    auth_token = use_auth_token or HUGGINGFACE_TOKEN

    return SpeakerDiarizationEngine(
        model_name=model_name or DIARIZATION_MODEL,
        use_auth_token=auth_token,
        device=device
    )
