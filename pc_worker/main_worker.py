#!/usr/bin/env python3
"""
PC Worker Main Loop
Polls Supabase for pending meetings and processes audio
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import time

from config import (
    WORKER_ID,
    WORKER_NAME,
    POLLING_INTERVAL_SECONDS,
    AUDIO_TEMP_DIR,
    MAX_CONCURRENT_JOBS,
    SUMMARIZATION_ENABLED
)
from logger import get_logger
from supabase_client import get_supabase_client
from audio_processor import get_audio_processor
from stt_pipeline import get_stt_pipeline, STTPipeline
from summarizer import get_summarizer
from realtime_worker import get_realtime_worker
from models import MeetingStatus, Meeting, Transcript
from exceptions import (
    PCWorkerException,
    AudioDownloadError,
    AudioPreprocessingError,
    TranscriptionError,
    DiarizationError,
    SupabaseQueryError,
    SummaryGenerationError
)
from utils import (
    cleanup_temp_files,
    get_system_info,
    get_audio_temp_path,
    get_processed_audio_path,
    cleanup_single_file
)

# Initialize logger
logger = get_logger("pc_worker", level="INFO")


class PCWorker:
    """
    PC Worker for processing meeting audio
    Polls Supabase for pending meetings and orchestrates the processing pipeline
    """

    def __init__(self):
        self.worker_id = WORKER_ID
        self.worker_name = WORKER_NAME
        self.is_running = False
        self.current_jobs = 0
        self.supabase = get_supabase_client()
        self.audio_processor = get_audio_processor(
            target_sample_rate=16000,
            normalize=True,
            remove_silence=False
        )
        self.stt_pipeline: Optional[STTPipeline] = None  # Lazy initialization
        self.summarizer = get_summarizer() if SUMMARIZATION_ENABLED else None
        self.realtime = get_realtime_worker(self.supabase.client)

        # Log system info at startup
        system_info = get_system_info(self.worker_id, self.worker_name)
        logger.info(
            f"Worker initialized",
            worker_id=self.worker_id,
            gpu_available=system_info.gpu_available,
            gpu_name=system_info.gpu_name or "N/A",
            memory_gb=f"{system_info.memory_available_gb:.2f}",
            summarization_enabled=SUMMARIZATION_ENABLED
        )

    async def _ensure_stt_pipeline(self) -> STTPipeline:
        """Ensure STT pipeline is initialized (lazy loading)"""
        if self.stt_pipeline is None:
            logger.info("Initializing STT pipeline (WhisperX + Speaker Diarization)...")
            self.stt_pipeline = get_stt_pipeline(
                enable_preprocessing=False,  # Audio already preprocessed by audio_processor
                enable_noise_reduction=False  # Noise reduction already applied
            )
            await self.stt_pipeline.initialize()
            logger.info("STT pipeline initialized successfully")
        return self.stt_pipeline

    async def start(self):
        """Start the worker main loop"""
        self.is_running = True
        logger.info(f"Starting {self.worker_name}...")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Health check
        if not await self.supabase.health_check():
            logger.error("Supabase health check failed. Exiting.")
            return

        # Cleanup old temp files on startup
        cleanup_count = cleanup_temp_files(AUDIO_TEMP_DIR, max_age_hours=24)
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} old temp files")

        try:
            while self.is_running:
                await self.poll_pending_meetings()
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            await self.stop()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False

    async def poll_pending_meetings(self):
        """Poll Supabase for pending meetings and process them"""
        try:
            # Check if we can take more jobs
            if self.current_jobs >= MAX_CONCURRENT_JOBS:
                logger.debug("Max concurrent jobs reached, skipping poll")
                return

            # Query for pending meetings
            pending_meetings = await self.supabase.get_pending_meetings(
                limit=MAX_CONCURRENT_JOBS - self.current_jobs
            )

            if not pending_meetings:
                logger.debug("No pending meetings found")
                return

            logger.info(f"Found {len(pending_meetings)} pending meeting(s)")

            # Process each meeting
            for meeting in pending_meetings:
                if not self.is_running:
                    break

                # Process meeting (currently synchronous, can be made concurrent)
                await self.process_meeting(meeting.id)

        except SupabaseQueryError as e:
            logger.error(f"Database error polling meetings: {e}")
        except Exception as e:
            logger.error(f"Unexpected error polling meetings: {e}", exc_info=True)

    async def process_meeting(self, meeting_id: str):
        """
        Process a single meeting through the complete pipeline

        Steps:
        1. Update status to 'processing'
        2. Fetch meeting and apply template tags (auto-tagging)
        3. Get audio URL from meeting record
        4. Download audio from Supabase Storage
        5. Preprocess audio (resample, normalize)
        6. [Phase 2] Run WhisperX STT + Diarization
        7. [Phase 2] Extract speaker embeddings
        8. [Phase 2] Match speakers to registered speakers
        9. [Phase 3] Generate summary with Ollama + Gemma 2
        10. [Phase 2] Store results in Supabase
        11. Update meeting status to 'completed'

        Args:
            meeting_id: Meeting identifier
        """
        start_time = time.time()
        self.current_jobs += 1

        logger.log_meeting_event(meeting_id, "processing_started")

        temp_audio_path: Optional[Path] = None
        processed_audio_path: Optional[Path] = None

        try:
            # Step 1: Update status to processing
            await self.supabase.update_meeting_status(
                meeting_id=meeting_id,
                status=MeetingStatus.PROCESSING,
                processed_by=self.worker_id
            )

            # Step 2: Fetch meeting and apply template tags (auto-tagging)
            meeting = await self.supabase.get_meeting_by_id(meeting_id)
            if not meeting:
                raise Exception("Meeting not found")

            user_id = meeting.user_id

            # Notify mobile: processing started
            await self.realtime.notify_processing_started(
                user_id=user_id,
                meeting_id=meeting_id
            )

            if meeting:
                await self._apply_template_tags(meeting_id, meeting.user_id)

            # Step 3: Get audio URL
            audio_url = await self.supabase.get_meeting_audio_url(meeting_id)
            if not audio_url:
                raise AudioDownloadError("No audio URL found for meeting")

            # Step 4: Download audio
            temp_audio_path = get_audio_temp_path(meeting_id, AUDIO_TEMP_DIR)
            await self.audio_processor.download_audio(
                url=audio_url,
                destination=temp_audio_path,
                meeting_id=meeting_id
            )

            # Step 5: Preprocess audio
            processed_audio_path = get_processed_audio_path(meeting_id, AUDIO_TEMP_DIR)
            audio_metadata = await self.audio_processor.preprocess_audio(
                input_path=temp_audio_path,
                output_path=processed_audio_path,
                meeting_id=meeting_id
            )

            logger.log_meeting_event(
                meeting_id,
                "audio_preprocessed",
                duration_s=f"{audio_metadata.duration_seconds:.2f}",
                sample_rate=audio_metadata.sample_rate
            )

            # Step 6: Run STT + Speaker Diarization pipeline
            stt_pipeline = await self._ensure_stt_pipeline()

            logger.log_meeting_event(meeting_id, "stt_started")
            pipeline_result = await stt_pipeline.process_audio(
                audio_path=processed_audio_path,
                meeting_id=meeting_id,
                language="ko",  # Korean (can be made configurable)
                num_speakers=None,  # Auto-detect
                enhance_audio=False  # Already preprocessed
            )

            logger.log_meeting_event(
                meeting_id,
                "stt_completed",
                segments=len(pipeline_result.transcript.segments),
                speakers=pipeline_result.num_speakers_detected,
                transcription_time=f"{pipeline_result.transcription_time:.2f}s",
                diarization_time=f"{pipeline_result.diarization_time:.2f}s",
                avg_confidence=f"{pipeline_result.average_confidence:.2f}" if pipeline_result.average_confidence else "N/A"
            )

            # Step 7: Save transcript to Supabase
            if pipeline_result.transcript.segments:
                await self.supabase.save_transcript(meeting_id, pipeline_result.transcript)
                logger.log_meeting_event(
                    meeting_id,
                    "transcript_saved",
                    segment_count=len(pipeline_result.transcript.segments)
                )

            # Step 8: Save speakers to Supabase
            if pipeline_result.speakers:
                await self.supabase.save_speakers(meeting_id, pipeline_result.speakers)
                logger.log_meeting_event(
                    meeting_id,
                    "speakers_saved",
                    speaker_count=len(pipeline_result.speakers)
                )

            # Step 9: Generate summary with Ollama + Gemma 2
            summary = None
            if SUMMARIZATION_ENABLED and self.summarizer:
                if pipeline_result.transcript.segments:
                    try:
                        summary = await self.summarizer.summarize_with_retry(
                            segments=pipeline_result.transcript.segments,
                            meeting_id=meeting_id,
                            extract_details=True
                        )

                        if summary:
                            await self.supabase.save_summary(meeting_id, summary)
                            logger.log_meeting_event(
                                meeting_id,
                                "summary_generated",
                                summary_length=len(summary.summary),
                                key_points=len(summary.key_points),
                                action_items=len(summary.action_items)
                            )
                        else:
                            logger.warning(f"Summarization failed for {meeting_id} after retries")

                    except SummaryGenerationError as e:
                        # Log but don't fail the entire meeting if summary fails
                        logger.warning(f"Summary generation error for {meeting_id}: {e}")

            processing_time = time.time() - start_time

            # Step 10: Update status to completed
            await self.supabase.update_meeting_status(
                meeting_id=meeting_id,
                status=MeetingStatus.COMPLETED,
                processed_by=self.worker_id
            )

            # Notify mobile: processing completed
            await self.realtime.notify_processing_completed(
                user_id=user_id,
                meeting_id=meeting_id,
                result_data={
                    'processing_time': processing_time,
                    'duration': audio_metadata.duration_seconds,
                    'transcript_segments': len(pipeline_result.transcript.segments),
                    'speakers_detected': pipeline_result.num_speakers_detected,
                    'summary_generated': summary is not None
                }
            )

            logger.log_meeting_event(
                meeting_id,
                "processing_completed",
                duration_s=f"{processing_time:.2f}",
                summary_generated=summary is not None
            )

        except AudioDownloadError as e:
            await self._handle_processing_error(meeting_id, "Audio download failed", e)
        except AudioPreprocessingError as e:
            await self._handle_processing_error(meeting_id, "Audio preprocessing failed", e)
        except TranscriptionError as e:
            await self._handle_processing_error(meeting_id, "Transcription failed", e)
        except DiarizationError as e:
            await self._handle_processing_error(meeting_id, "Speaker diarization failed", e)
        except PCWorkerException as e:
            await self._handle_processing_error(meeting_id, "Processing failed", e)
        except Exception as e:
            await self._handle_processing_error(meeting_id, "Unexpected error", e)
        finally:
            # Cleanup temporary files
            if temp_audio_path:
                cleanup_single_file(temp_audio_path)
            if processed_audio_path:
                cleanup_single_file(processed_audio_path)

            self.current_jobs -= 1

    async def _apply_template_tags(self, meeting_id: str, user_id: str) -> None:
        """
        Apply template tags to a meeting (auto-tagging on processing start)

        This method checks if the meeting has a template_id assigned.
        If so, it fetches the template and applies its tags to the meeting.

        This is an idempotent operation - if tags are already applied,
        they won't be overwritten if they're non-empty.

        Args:
            meeting_id: Meeting identifier
            user_id: User identifier to fetch templates
        """
        try:
            # Fetch the meeting to check for template_id and existing tags
            meeting = await self.supabase.get_meeting_by_id(meeting_id)
            if not meeting:
                logger.warning(f"Meeting {meeting_id} not found for template tagging")
                return

            # If meeting already has tags, don't overwrite them
            if meeting.tags and len(meeting.tags) > 0:
                logger.debug(f"Meeting {meeting_id} already has tags: {meeting.tags}")
                logger.log_meeting_event(
                    meeting_id,
                    "template_tagging_skipped",
                    reason="existing_tags"
                )
                return

            # Check if meeting has a template_id assigned
            if not meeting.template_id:
                logger.debug(f"Meeting {meeting_id} has no template assigned")
                logger.log_meeting_event(
                    meeting_id,
                    "template_tagging_skipped",
                    reason="no_template"
                )
                return

            # Fetch the template to get tags
            template = await self.supabase.get_template_by_id(meeting.template_id, user_id)
            if not template:
                logger.warning(f"Template {meeting.template_id} not found for meeting {meeting_id}")
                return

            # Apply template tags to the meeting
            if template.tags and len(template.tags) > 0:
                success = await self.supabase.update_meeting_tags(meeting_id, template.tags)
                if success:
                    logger.log_meeting_event(
                        meeting_id,
                        "template_tagging_completed",
                        template_name=template.name,
                        tags_applied=template.tags
                    )
                else:
                    logger.warning(f"Failed to apply template tags to meeting {meeting_id}")
            else:
                logger.debug(f"Template {template.name} has no tags to apply")
                logger.log_meeting_event(
                    meeting_id,
                    "template_tagging_skipped",
                    reason="template_has_no_tags"
                )

        except Exception as e:
            # Log but don't fail processing on tagging errors
            logger.warning(f"Failed to apply template tags to meeting {meeting_id}: {e}")

    async def _handle_processing_error(
        self,
        meeting_id: str,
        error_type: str,
        error: Exception
    ):
        """
        Handle processing errors and update meeting status

        Args:
            meeting_id: Meeting identifier
            error_type: Type of error
            error: Exception that occurred
        """
        error_message = f"{error_type}: {str(error)}"
        logger.log_meeting_event(
            meeting_id,
            "processing_failed",
            error=error_message
        )

        try:
            # Get user_id for notification
            meeting = await self.supabase.get_meeting_by_id(meeting_id)
            user_id = meeting.user_id if meeting else None

            await self.supabase.update_meeting_status(
                meeting_id=meeting_id,
                status=MeetingStatus.FAILED,
                error_message=error_message,
                processed_by=self.worker_id
            )

            # Notify mobile: processing failed
            if user_id:
                await self.realtime.notify_processing_failed(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    error_message=error_message
                )
        except Exception as e:
            logger.error(
                f"Failed to update error status for meeting {meeting_id}: {e}"
            )

    async def stop(self):
        """Stop the worker gracefully"""
        self.is_running = False

        # Wait for current jobs to complete (with timeout)
        timeout = 60  # 60 seconds
        start_wait = time.time()

        while self.current_jobs > 0 and (time.time() - start_wait) < timeout:
            logger.info(f"Waiting for {self.current_jobs} job(s) to complete...")
            await asyncio.sleep(5)

        if self.current_jobs > 0:
            logger.warning(f"Forced shutdown with {self.current_jobs} job(s) still running")

        # Cleanup STT pipeline resources (GPU memory, models)
        if self.stt_pipeline:
            logger.info("Cleaning up STT pipeline...")
            await self.stt_pipeline.cleanup()
            self.stt_pipeline = None

        # Final cleanup
        cleanup_count = cleanup_temp_files(AUDIO_TEMP_DIR, max_age_hours=0)
        if cleanup_count > 0:
            logger.info(f"Final cleanup removed {cleanup_count} temp files")

        logger.info(f"Stopped {self.worker_name}")


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("PC Worker Starting")
    logger.info("=" * 60)

    worker = PCWorker()

    try:
        await worker.start()
    except Exception as e:
        logger.critical(f"Fatal error in worker: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("PC Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
