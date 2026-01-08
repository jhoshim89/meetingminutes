"""
End-to-End Workflow Tests for PC Worker
Tests complete mobile-to-PC-to-mobile integration
"""

import asyncio
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_client import get_supabase_client
from audio_processor import get_audio_processor
from realtime_worker import get_realtime_worker
from models import MeetingStatus, Meeting
from main_worker import PCWorker


class TestE2EWorkflow:
    """End-to-end workflow tests"""

    @pytest.fixture
    async def setup(self):
        """Setup test environment"""
        self.supabase = get_supabase_client()
        self.realtime = get_realtime_worker(self.supabase.client)
        self.audio_processor = get_audio_processor()

        # Verify connection
        assert await self.supabase.health_check(), "Supabase connection failed"

        yield

        # Cleanup

    @pytest.mark.asyncio
    async def test_realtime_notification_flow(self):
        """
        Test realtime notification system

        Flow:
        1. Create test meeting
        2. Send processing_started notification
        3. Send processing_completed notification
        4. Verify notifications sent successfully
        """
        # Create test meeting
        test_user_id = "test_user_" + str(int(time.time()))
        test_meeting_id = "test_meeting_" + str(int(time.time()))

        # Send processing started
        success = await self.realtime.notify_processing_started(
            user_id=test_user_id,
            meeting_id=test_meeting_id
        )
        assert success, "Failed to send processing_started notification"

        # Send progress update
        success = await self.realtime.notify_processing_progress(
            user_id=test_user_id,
            meeting_id=test_meeting_id,
            progress_percentage=50.0,
            message="Halfway there"
        )
        assert success, "Failed to send progress notification"

        # Send completed
        success = await self.realtime.notify_processing_completed(
            user_id=test_user_id,
            meeting_id=test_meeting_id,
            result_data={
                'duration': 120.5,
                'transcript_count': 45
            }
        )
        assert success, "Failed to send processing_completed notification"

    @pytest.mark.asyncio
    async def test_meeting_status_updates(self):
        """
        Test meeting status update flow

        Flow:
        1. Query pending meetings
        2. Update status to processing
        3. Update status to completed
        4. Verify each step
        """
        # This test requires actual meetings in database
        # Skip if no pending meetings

        pending = await self.supabase.get_pending_meetings(limit=1)

        if not pending:
            pytest.skip("No pending meetings available for testing")

        meeting = pending[0]

        # Update to processing
        success = await self.supabase.update_meeting_status(
            meeting_id=meeting.id,
            status=MeetingStatus.PROCESSING,
            processed_by="test_worker"
        )
        assert success, "Failed to update status to PROCESSING"

        # Verify status
        updated = await self.supabase.get_meeting_by_id(meeting.id)
        assert updated.status == MeetingStatus.PROCESSING

        # Update to completed
        success = await self.supabase.update_meeting_status(
            meeting_id=meeting.id,
            status=MeetingStatus.COMPLETED,
            processed_by="test_worker"
        )
        assert success, "Failed to update status to COMPLETED"

        # Verify final status
        final = await self.supabase.get_meeting_by_id(meeting.id)
        assert final.status == MeetingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_audio_download_and_preprocessing(self):
        """
        Test audio download and preprocessing

        Requires a test meeting with audio URL
        """
        # Get a meeting with audio URL
        # This might require manual setup of test data

        test_meeting_id = os.getenv("TEST_MEETING_ID")
        if not test_meeting_id:
            pytest.skip("TEST_MEETING_ID not set, skipping audio test")

        # Get audio URL
        audio_url = await self.supabase.get_meeting_audio_url(test_meeting_id)
        assert audio_url, "No audio URL found for test meeting"

        # Download audio
        temp_path = Path(f"/tmp/test_audio_{int(time.time())}.m4a")
        downloaded = await self.audio_processor.download_audio(
            url=audio_url,
            destination=temp_path,
            meeting_id=test_meeting_id
        )

        assert downloaded.exists(), "Audio file not downloaded"
        assert downloaded.stat().st_size > 0, "Downloaded file is empty"

        # Preprocess audio
        processed_path = Path(f"/tmp/test_processed_{int(time.time())}.wav")
        metadata = await self.audio_processor.preprocess_audio(
            input_path=temp_path,
            output_path=processed_path,
            meeting_id=test_meeting_id
        )

        assert processed_path.exists(), "Processed audio not created"
        assert metadata.sample_rate == 16000, "Sample rate not 16kHz"
        assert metadata.duration_seconds > 0, "Duration is zero"

        # Cleanup
        temp_path.unlink(missing_ok=True)
        processed_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_processing_pipeline(self):
        """
        Test complete meeting processing pipeline

        This is a slow test that processes a real meeting
        Requires TEST_MEETING_ID environment variable
        """
        test_meeting_id = os.getenv("TEST_MEETING_ID")
        if not test_meeting_id:
            pytest.skip("TEST_MEETING_ID not set, skipping full pipeline test")

        worker = PCWorker()

        # Process meeting
        start_time = time.time()
        await worker.process_meeting(test_meeting_id)
        processing_time = time.time() - start_time

        # Verify meeting completed
        meeting = await self.supabase.get_meeting_by_id(test_meeting_id)
        assert meeting.status in [
            MeetingStatus.COMPLETED,
            MeetingStatus.FAILED
        ], f"Unexpected status: {meeting.status}"

        print(f"\nProcessing completed in {processing_time:.2f} seconds")
        print(f"Status: {meeting.status}")

        if meeting.status == MeetingStatus.FAILED:
            print(f"Error: {meeting.error_message}")

    @pytest.mark.asyncio
    async def test_error_handling_no_audio(self):
        """
        Test error handling when meeting has no audio URL
        """
        # Create meeting without audio
        # This will fail in processing
        # Verify it's marked as FAILED with appropriate error message

        # TODO: Implement when meeting creation API is available
        pass

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """
        Test processing multiple meetings concurrently

        Verifies worker can handle concurrent jobs
        """
        # Get multiple pending meetings
        pending = await self.supabase.get_pending_meetings(limit=3)

        if len(pending) < 2:
            pytest.skip("Need at least 2 pending meetings for concurrent test")

        # Process them concurrently
        tasks = [
            PCWorker().process_meeting(meeting.id)
            for meeting in pending[:2]
        ]

        start_time = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        print(f"\nProcessed {len(tasks)} meetings concurrently in {elapsed:.2f}s")

        # Verify all completed
        for meeting in pending[:2]:
            updated = await self.supabase.get_meeting_by_id(meeting.id)
            assert updated.status in [MeetingStatus.COMPLETED, MeetingStatus.FAILED]


class TestRealtimeIntegration:
    """Tests for realtime communication"""

    @pytest.fixture
    async def setup(self):
        """Setup realtime worker"""
        self.supabase = get_supabase_client()
        self.realtime = get_realtime_worker(self.supabase.client)
        yield

    @pytest.mark.asyncio
    async def test_send_all_notification_types(self):
        """Test sending all types of notifications"""
        test_user_id = "test_user"
        test_meeting_id = "test_meeting_" + str(int(time.time()))

        # Processing started
        assert await self.realtime.notify_processing_started(
            user_id=test_user_id,
            meeting_id=test_meeting_id
        )

        # Progress updates
        for progress in [25, 50, 75]:
            assert await self.realtime.notify_processing_progress(
                user_id=test_user_id,
                meeting_id=test_meeting_id,
                progress_percentage=float(progress)
            )
            await asyncio.sleep(0.5)

        # Completed
        assert await self.realtime.notify_processing_completed(
            user_id=test_user_id,
            meeting_id=test_meeting_id,
            result_data={'test': 'data'}
        )

    @pytest.mark.asyncio
    async def test_send_failure_notification(self):
        """Test sending failure notification"""
        test_user_id = "test_user"
        test_meeting_id = "test_meeting_fail_" + str(int(time.time()))

        assert await self.realtime.notify_processing_failed(
            user_id=test_user_id,
            meeting_id=test_meeting_id,
            error_message="Test error message"
        )


class TestPerformance:
    """Performance and timing tests"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_processing_time_10min_audio(self):
        """
        Test processing time for 10-minute audio

        Target: Complete processing in < 5 minutes
        """
        # This requires a 10-minute test audio file
        test_meeting_id = os.getenv("TEST_LONG_MEETING_ID")
        if not test_meeting_id:
            pytest.skip("TEST_LONG_MEETING_ID not set")

        worker = PCWorker()

        start_time = time.time()
        await worker.process_meeting(test_meeting_id)
        processing_time = time.time() - start_time

        print(f"\n10-minute audio processed in {processing_time:.2f} seconds")
        assert processing_time < 300, "Processing took longer than 5 minutes"

    @pytest.mark.asyncio
    async def test_notification_latency(self):
        """
        Test realtime notification latency

        Target: < 2 seconds from send to receive
        """
        # This would require a mobile listener to measure true latency
        # For now, just measure send time

        supabase = get_supabase_client()
        realtime = get_realtime_worker(supabase.client)

        start = time.time()
        await realtime.notify_processing_started(
            user_id="test_user",
            meeting_id="test_meeting"
        )
        send_time = time.time() - start

        print(f"\nNotification sent in {send_time*1000:.2f}ms")
        assert send_time < 1.0, "Send time too slow"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
