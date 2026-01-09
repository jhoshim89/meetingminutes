"""
Integrated STT + Speaker Diarization Pipeline
Combines audio processing, WhisperX transcription, and speaker diarization
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time
from dataclasses import dataclass

from audio_processor import AudioProcessor, get_audio_processor
from whisperx_engine import WhisperXEngine, get_whisperx_engine
from speaker_diarization import SpeakerDiarizationEngine, get_diarization_engine
from models import (
    TranscriptSegment,
    Transcript,
    AudioMetadata,
    Speaker,
    SpeakerEmbedding
)
from exceptions import (
    AudioPreprocessingError,
    TranscriptionError,
    DiarizationError,
    PCWorkerException
)
from logger import get_logger
from config import AUDIO_TEMP_DIR

logger = get_logger("stt_pipeline")


@dataclass
class PipelineResult:
    """Complete result from STT + Diarization pipeline"""
    meeting_id: str
    audio_metadata: AudioMetadata
    transcript: Transcript
    speakers: List[Speaker]
    speaker_embeddings: Dict[str, SpeakerEmbedding]
    processing_time_seconds: float

    # Performance metrics
    transcription_time: float
    diarization_time: float
    alignment_time: float

    # Quality metrics
    average_confidence: Optional[float] = None
    num_speakers_detected: int = 0
    alignment_rate: float = 0.0


class STTPipeline:
    """
    Integrated pipeline for speech-to-text and speaker diarization

    Pipeline stages:
    1. Audio preprocessing (noise reduction, normalization)
    2. Speech-to-text transcription (WhisperX)
    3. Speaker diarization (Pyannote)
    4. Alignment of transcript with speaker labels
    5. Speaker embedding extraction
    """

    def __init__(
        self,
        audio_processor: Optional[AudioProcessor] = None,
        whisperx_engine: Optional[WhisperXEngine] = None,
        diarization_engine: Optional[SpeakerDiarizationEngine] = None,
        enable_preprocessing: bool = True,
        enable_noise_reduction: bool = True
    ):
        """
        Initialize STT pipeline

        Args:
            audio_processor: Audio processor instance (creates default if None)
            whisperx_engine: WhisperX engine instance (creates default if None)
            diarization_engine: Diarization engine instance (creates default if None)
            enable_preprocessing: Whether to apply audio preprocessing
            enable_noise_reduction: Whether to apply noise reduction
        """
        self.audio_processor = audio_processor or get_audio_processor()
        self.whisperx_engine = whisperx_engine or get_whisperx_engine()
        self.diarization_engine = diarization_engine or get_diarization_engine()

        self.enable_preprocessing = enable_preprocessing
        self.enable_noise_reduction = enable_noise_reduction

        self._is_initialized = False

        logger.info("STT Pipeline initialized")

    async def initialize(self) -> None:
        """
        Initialize all pipeline components

        Raises:
            PCWorkerException: If initialization fails
        """
        if self._is_initialized:
            logger.debug("Pipeline already initialized")
            return

        logger.log_operation_start("initialize_stt_pipeline")

        try:
            # Initialize WhisperX (heavy operation)
            await self.whisperx_engine.initialize()

            # Initialize Diarization pipeline (heavy operation)
            await self.diarization_engine.initialize()

            self._is_initialized = True

            logger.log_operation_success("initialize_stt_pipeline")

        except Exception as e:
            logger.log_operation_failure("initialize_stt_pipeline", e)
            raise PCWorkerException(f"Failed to initialize STT pipeline: {e}")

    async def process_audio(
        self,
        audio_path: Path,
        meeting_id: str,
        language: str = "ko",
        num_speakers: Optional[int] = None,
        enhance_audio: bool = True
    ) -> PipelineResult:
        """
        Process audio file through complete STT + Diarization pipeline

        Args:
            audio_path: Path to audio file
            meeting_id: Meeting ID for tracking
            language: Language code for transcription
            num_speakers: Known number of speakers (improves accuracy if provided)
            enhance_audio: Whether to apply audio enhancement

        Returns:
            PipelineResult with transcript, speakers, and embeddings

        Raises:
            AudioPreprocessingError: If audio preprocessing fails
            TranscriptionError: If transcription fails
            DiarizationError: If diarization fails
        """
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start(
            "process_audio_pipeline",
            meeting_id=meeting_id,
            audio_path=str(audio_path)
        )

        pipeline_start_time = time.time()

        try:
            # Stage 1: Audio Preprocessing
            preprocessed_path = audio_path

            if self.enable_preprocessing or enhance_audio:
                preprocessed_path = await self._preprocess_audio(
                    audio_path,
                    meeting_id,
                    enhance_audio
                )

            # Load audio metadata
            audio_metadata = await self._get_audio_metadata(preprocessed_path)

            # Stage 2: Speech-to-Text Transcription
            transcription_start = time.time()
            transcript_segments = await self.whisperx_engine.transcribe(
                preprocessed_path,
                meeting_id,
                language=language
            )
            transcription_time = time.time() - transcription_start

            logger.info(
                f"Transcription complete: {len(transcript_segments)} segments "
                f"in {transcription_time:.2f}s"
            )

            # Stage 3: Speaker Diarization
            diarization_start = time.time()
            diarization = await self.diarization_engine.diarize(
                preprocessed_path,
                meeting_id,
                num_speakers=num_speakers,
                min_speakers=1,
                max_speakers=10
            )
            diarization_time = time.time() - diarization_start

            num_speakers_detected = len(list(diarization.labels()))
            logger.info(
                f"Diarization complete: {num_speakers_detected} speakers "
                f"in {diarization_time:.2f}s"
            )

            # Stage 4: Align transcript with speaker labels
            alignment_start = time.time()
            aligned_segments = await self.diarization_engine.align_with_transcript(
                diarization,
                transcript_segments,
                meeting_id
            )
            alignment_time = time.time() - alignment_start

            # Stage 5: Extract speaker embeddings (optional - may fail if model not available)
            speaker_embeddings = {}
            try:
                speaker_embeddings = await self.diarization_engine.extract_speaker_embeddings(
                    preprocessed_path,
                    diarization,
                    meeting_id
                )
            except Exception as e:
                logger.warning(
                    f"Speaker embedding extraction failed (optional feature): {e}. "
                    f"Continuing without embeddings."
                )

            # Stage 6: Create speaker objects
            speakers = self._create_speaker_objects(
                diarization,
                speaker_embeddings,
                meeting_id
            )

            # Create transcript object
            transcript = Transcript(
                meeting_id=meeting_id,
                segments=aligned_segments,
                language=language,
                duration=audio_metadata.duration_seconds
            )

            # Calculate metrics
            average_confidence = self._calculate_average_confidence(aligned_segments)
            alignment_rate = self._calculate_alignment_rate(aligned_segments)

            # Total processing time
            total_time = time.time() - pipeline_start_time

            # Create result
            result = PipelineResult(
                meeting_id=meeting_id,
                audio_metadata=audio_metadata,
                transcript=transcript,
                speakers=speakers,
                speaker_embeddings=speaker_embeddings,
                processing_time_seconds=total_time,
                transcription_time=transcription_time,
                diarization_time=diarization_time,
                alignment_time=alignment_time,
                average_confidence=average_confidence,
                num_speakers_detected=num_speakers_detected,
                alignment_rate=alignment_rate
            )

            logger.log_operation_success(
                "process_audio_pipeline",
                meeting_id=meeting_id,
                total_time=f"{total_time:.2f}s",
                segments=len(aligned_segments),
                speakers=num_speakers_detected,
                avg_confidence=f"{average_confidence:.2f}" if average_confidence else "N/A"
            )

            return result

        except Exception as e:
            logger.log_operation_failure(
                "process_audio_pipeline",
                e,
                meeting_id=meeting_id
            )
            raise

    async def _preprocess_audio(
        self,
        audio_path: Path,
        meeting_id: str,
        enhance: bool
    ) -> Path:
        """
        Preprocess audio file

        Args:
            audio_path: Original audio path
            meeting_id: Meeting ID
            enhance: Whether to apply enhancement

        Returns:
            Path to preprocessed audio
        """
        # Create output path
        output_path = AUDIO_TEMP_DIR / f"{meeting_id}_preprocessed.wav"

        if not enhance:
            # Just resample and normalize
            metadata = await self.audio_processor.preprocess_audio(
                audio_path,
                output_path,
                meeting_id
            )
        else:
            # Full enhancement pipeline
            audio_data, sample_rate = await self.audio_processor.load_audio(audio_path)

            # Apply enhancement
            enhanced_audio = await self.audio_processor.enhance_audio_for_stt(
                audio_data,
                sample_rate
            )

            # Save enhanced audio
            await self.audio_processor.save_processed_audio(
                enhanced_audio,
                self.audio_processor.target_sample_rate,
                output_path
            )

        return output_path

    async def _get_audio_metadata(self, audio_path: Path) -> AudioMetadata:
        """Get audio metadata"""
        duration = await self.audio_processor.get_audio_duration(audio_path)

        return AudioMetadata(
            file_path=str(audio_path),
            duration_seconds=duration,
            sample_rate=self.audio_processor.target_sample_rate,
            channels=1,
            format="WAV",
            size_bytes=audio_path.stat().st_size
        )

    def _create_speaker_objects(
        self,
        diarization,
        speaker_embeddings: Dict[str, SpeakerEmbedding],
        meeting_id: str
    ) -> List[Speaker]:
        """Create Speaker objects from diarization results"""
        speakers = []

        for speaker_label in diarization.labels():
            embedding = speaker_embeddings.get(speaker_label)

            speaker = Speaker(
                id=speaker_label,
                name=None,  # Will be assigned later by user
                user_id=None,
                embedding=embedding,
                meeting_ids=[meeting_id]
            )

            speakers.append(speaker)

        return speakers

    def _calculate_average_confidence(
        self,
        segments: List[TranscriptSegment]
    ) -> Optional[float]:
        """Calculate average confidence score"""
        confidences = [
            seg.confidence for seg in segments
            if seg.confidence is not None
        ]

        if confidences:
            return sum(confidences) / len(confidences)
        return None

    def _calculate_alignment_rate(
        self,
        segments: List[TranscriptSegment]
    ) -> float:
        """Calculate speaker alignment rate"""
        if not segments:
            return 0.0

        aligned = sum(
            1 for seg in segments
            if seg.speaker_label is not None
        )

        return aligned / len(segments)

    async def process_batch(
        self,
        audio_paths: List[Path],
        meeting_ids: List[str],
        language: str = "ko"
    ) -> List[PipelineResult]:
        """
        Process multiple audio files in batch

        Args:
            audio_paths: List of audio file paths
            meeting_ids: List of meeting IDs (must match audio_paths length)
            language: Language code

        Returns:
            List of PipelineResult objects
        """
        if len(audio_paths) != len(meeting_ids):
            raise ValueError("audio_paths and meeting_ids must have same length")

        logger.info(f"Starting batch processing for {len(audio_paths)} files")

        results = []

        # Process each file (can be parallelized with asyncio.gather)
        for audio_path, meeting_id in zip(audio_paths, meeting_ids):
            try:
                result = await self.process_audio(audio_path, meeting_id, language)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {meeting_id}: {e}")
                # Continue with other files

        logger.info(f"Batch processing complete: {len(results)}/{len(audio_paths)} successful")

        return results

    def get_pipeline_info(self) -> Dict[str, any]:
        """Get information about pipeline components"""
        return {
            "initialized": self._is_initialized,
            "preprocessing_enabled": self.enable_preprocessing,
            "noise_reduction_enabled": self.enable_noise_reduction,
            "whisperx": self.whisperx_engine.get_model_info() if self._is_initialized else {},
            "diarization": self.diarization_engine.get_pipeline_info() if self._is_initialized else {}
        }

    async def cleanup(self) -> None:
        """Clean up all pipeline resources"""
        logger.info("Cleaning up STT pipeline")

        if self.whisperx_engine:
            await self.whisperx_engine.cleanup()

        if self.diarization_engine:
            await self.diarization_engine.cleanup()

        self._is_initialized = False

        logger.info("STT pipeline cleanup complete")


# Factory function
def get_stt_pipeline(
    enable_preprocessing: bool = True,
    enable_noise_reduction: bool = True
) -> STTPipeline:
    """
    Create STT pipeline instance

    Args:
        enable_preprocessing: Whether to enable preprocessing
        enable_noise_reduction: Whether to enable noise reduction

    Returns:
        STTPipeline instance
    """
    return STTPipeline(
        enable_preprocessing=enable_preprocessing,
        enable_noise_reduction=enable_noise_reduction
    )
