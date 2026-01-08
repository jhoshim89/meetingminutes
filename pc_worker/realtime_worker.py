"""
Realtime Worker Module
Sends processing status updates to mobile clients via Supabase Realtime
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from supabase import Client
from config import logger
from exceptions import SupabaseRealtimeError


class RealtimeWorker:
    """
    Manages realtime communication with mobile clients
    Sends processing status updates via Supabase Realtime broadcast
    """

    def __init__(self, supabase_client: Client):
        """
        Initialize RealtimeWorker

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client
        logger.info("RealtimeWorker initialized")

    async def send_processing_update(
        self,
        user_id: str,
        meeting_id: str,
        status: str,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send processing status update to mobile client

        Args:
            user_id: User identifier for routing
            meeting_id: Meeting being processed
            status: Processing status ('pending', 'processing', 'completed', 'failed')
            message: Optional status message
            data: Optional additional data payload

        Returns:
            True if successful, False otherwise
        """
        try:
            channel_name = f"user:{user_id}:meetings"

            payload = {
                'meeting_id': meeting_id,
                'status': status,
                'timestamp': datetime.now().isoformat(),
            }

            if message:
                payload['message'] = message

            if data:
                payload['data'] = data

            logger.info(
                f"Sending realtime update",
                channel=channel_name,
                meeting_id=meeting_id,
                status=status
            )

            # Send broadcast message
            # Note: Supabase Python SDK doesn't directly support broadcast yet
            # We'll use REST API approach or database triggers as fallback
            await self._send_via_rest_api(channel_name, payload)

            logger.debug(f"Realtime update sent successfully for meeting {meeting_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send realtime update: {e}", exc_info=True)
            return False

    async def _send_via_rest_api(self, channel: str, payload: Dict[str, Any]):
        """
        Send broadcast via Supabase REST API

        This is a workaround since Python SDK doesn't fully support realtime broadcast yet.
        Alternative: Use database triggers to send notifications.

        Args:
            channel: Channel name
            payload: Payload to broadcast
        """
        try:
            # For now, we'll use database updates as triggers
            # Mobile clients will listen to database changes via Realtime
            # This is more reliable than direct broadcast in current Python SDK

            # Store notification in a notifications table
            await asyncio.to_thread(
                lambda: self.client.table('processing_updates').insert({
                    'channel': channel,
                    'event': 'processing_update',
                    'payload': payload,
                    'created_at': datetime.now().isoformat()
                }).execute()
            )

            logger.debug(f"Stored processing update in database for channel {channel}")

        except Exception as e:
            logger.error(f"Failed to send via REST API: {e}")
            raise SupabaseRealtimeError(f"Failed to send realtime update: {e}")

    async def notify_processing_started(
        self,
        user_id: str,
        meeting_id: str
    ) -> bool:
        """
        Notify that meeting processing has started

        Args:
            user_id: User identifier
            meeting_id: Meeting identifier

        Returns:
            True if successful
        """
        return await self.send_processing_update(
            user_id=user_id,
            meeting_id=meeting_id,
            status='processing',
            message='Processing started'
        )

    async def notify_processing_progress(
        self,
        user_id: str,
        meeting_id: str,
        progress_percentage: float,
        message: Optional[str] = None
    ) -> bool:
        """
        Notify processing progress

        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
            progress_percentage: Progress percentage (0-100)
            message: Optional progress message

        Returns:
            True if successful
        """
        return await self.send_processing_update(
            user_id=user_id,
            meeting_id=meeting_id,
            status='processing',
            message=message or f'Processing {progress_percentage:.1f}% complete',
            data={'progress': progress_percentage}
        )

    async def notify_processing_completed(
        self,
        user_id: str,
        meeting_id: str,
        result_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Notify that meeting processing completed successfully

        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
            result_data: Optional result data (transcript count, speaker count, etc.)

        Returns:
            True if successful
        """
        return await self.send_processing_update(
            user_id=user_id,
            meeting_id=meeting_id,
            status='completed',
            message='Processing completed successfully',
            data=result_data
        )

    async def notify_processing_failed(
        self,
        user_id: str,
        meeting_id: str,
        error_message: str
    ) -> bool:
        """
        Notify that meeting processing failed

        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
            error_message: Error description

        Returns:
            True if successful
        """
        return await self.send_processing_update(
            user_id=user_id,
            meeting_id=meeting_id,
            status='failed',
            message=f'Processing failed: {error_message}',
            data={'error': error_message}
        )


# Singleton instance
_realtime_worker: Optional[RealtimeWorker] = None


def get_realtime_worker(supabase_client: Client) -> RealtimeWorker:
    """
    Get or create singleton RealtimeWorker instance

    Args:
        supabase_client: Supabase client instance

    Returns:
        RealtimeWorker instance
    """
    global _realtime_worker
    if _realtime_worker is None:
        _realtime_worker = RealtimeWorker(supabase_client)
    return _realtime_worker
