"""
Supabase Client Integration
Singleton client for all Supabase operations with proper error handling
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import aiohttp

from supabase import create_client, Client
from postgrest.exceptions import APIError

from config import SUPABASE_URL, SUPABASE_KEY, logger
from models import (
    Meeting,
    MeetingStatus,
    TranscriptSegment,
    Transcript,
    Speaker,
    MeetingSummary,
    Template
)
from exceptions import (
    SupabaseConnectionError,
    SupabaseAuthenticationError,
    SupabaseQueryError,
    SupabaseStorageError,
    AudioDownloadError,
    RetryExhaustedError
)
from utils import retry_with_backoff


class SupabaseClient:
    """
    Singleton Supabase client for database and storage operations
    Implements retry logic and proper error handling
    """

    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None

    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Supabase client"""
        if self._client is None:
            try:
                self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise SupabaseConnectionError(f"Failed to initialize Supabase: {e}")

    @property
    def client(self) -> Client:
        """Get the underlying Supabase client"""
        if self._client is None:
            raise SupabaseConnectionError("Supabase client not initialized")
        return self._client

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def get_pending_meetings(self, limit: int = 10) -> List[Meeting]:
        """
        Query meetings with status='pending'

        Args:
            limit: Maximum number of meetings to return

        Returns:
            List of Meeting objects

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('meetings')
                .select('*')
                .eq('status', MeetingStatus.PENDING.value)
                .order('created_at', desc=False)
                .limit(limit)
                .execute()
            )

            meetings = []
            for data in response.data:
                try:
                    meeting = Meeting(**data)
                    meetings.append(meeting)
                except Exception as e:
                    logger.warning(f"Failed to parse meeting {data.get('id')}: {e}")
                    continue

            logger.debug(f"Found {len(meetings)} pending meetings")
            return meetings

        except APIError as e:
            logger.error(f"Supabase API error getting pending meetings: {e}")
            raise SupabaseQueryError(f"Failed to query pending meetings: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting pending meetings: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def get_meeting_by_id(self, meeting_id: str) -> Optional[Meeting]:
        """
        Get a specific meeting by ID

        Args:
            meeting_id: Meeting identifier

        Returns:
            Meeting object or None if not found

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('meetings')
                .select('*')
                .eq('id', meeting_id)
                .single()
                .execute()
            )

            if response.data:
                return Meeting(**response.data)
            return None

        except APIError as e:
            logger.error(f"Supabase API error getting meeting {meeting_id}: {e}")
            raise SupabaseQueryError(f"Failed to get meeting: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting meeting {meeting_id}: {e}")
            return None

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def update_meeting_status(
        self,
        meeting_id: str,
        status: MeetingStatus,
        error_message: Optional[str] = None,
        processed_by: Optional[str] = None
    ) -> bool:
        """
        Update meeting status

        Args:
            meeting_id: Meeting identifier
            status: New status
            error_message: Optional error message if status is FAILED
            processed_by: Optional worker ID that processed the meeting

        Returns:
            True if successful, False otherwise

        Raises:
            SupabaseQueryError: If update fails
        """
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.now().isoformat()
            }

            if error_message is not None:
                update_data['error_message'] = error_message

            if processed_by is not None:
                update_data['processed_by'] = processed_by

            await asyncio.to_thread(
                lambda: self.client.table('meetings')
                .update(update_data)
                .eq('id', meeting_id)
                .execute()
            )

            logger.info(f"Updated meeting {meeting_id} status to {status.value}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error updating meeting status: {e}")
            raise SupabaseQueryError(f"Failed to update meeting status: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating meeting status: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def get_meeting_audio_url(self, meeting_id: str) -> Optional[str]:
        """
        Get audio file URL from meeting record

        Args:
            meeting_id: Meeting identifier

        Returns:
            Audio URL or None if not found

        Raises:
            SupabaseQueryError: If query fails
        """
        meeting = await self.get_meeting_by_id(meeting_id)
        if meeting and meeting.audio_url:
            return meeting.audio_url

        # Try to get from storage path if audio_url is not set
        if meeting and meeting.audio_storage_path:
            try:
                # Generate signed URL from storage path
                url = await self.get_storage_signed_url(
                    bucket='meeting-audio',
                    path=meeting.audio_storage_path
                )
                return url
            except Exception as e:
                logger.error(f"Failed to get signed URL for {meeting_id}: {e}")
                return None

        return None

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def get_storage_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600
    ) -> str:
        """
        Get signed URL for file in Supabase Storage

        Args:
            bucket: Storage bucket name
            path: File path in bucket
            expires_in: URL expiration time in seconds

        Returns:
            Signed URL

        Raises:
            SupabaseStorageError: If URL generation fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.storage
                .from_(bucket)
                .create_signed_url(path, expires_in)
            )

            if response and 'signedURL' in response:
                return response['signedURL']
            else:
                raise SupabaseStorageError("No signed URL in response")

        except Exception as e:
            logger.error(f"Failed to create signed URL for {bucket}/{path}: {e}")
            raise SupabaseStorageError(f"Failed to create signed URL: {e}")

    async def download_audio_file(
        self,
        meeting_id: str,
        url: str,
        destination: Path
    ) -> Path:
        """
        Download audio file from URL to local path

        Args:
            meeting_id: Meeting identifier (for logging)
            url: Audio file URL or Storage path
            destination: Local file path to save to

        Returns:
            Path to downloaded file

        Raises:
            AudioDownloadError: If download fails
        """
        try:
            logger.info(f"Downloading audio for meeting {meeting_id}")

            # If URL is a storage path (not http/https), generate signed URL
            download_url = url
            if not url.startswith('http'):
                logger.info(f"Generating signed URL for storage path: {url}")
                try:
                    # Generate signed URL from Supabase Storage (1 hour expiry)
                    signed_result = self.client.storage.from_('recordings').create_signed_url(url, 3600)
                    download_url = signed_result.get('signedUrl') or signed_result.get('signedURL')
                    if not download_url:
                        raise AudioDownloadError(f"Failed to generate signed URL for: {url}")
                    logger.info(f"Generated signed URL successfully")
                except Exception as e:
                    logger.error(f"Failed to generate signed URL: {e}")
                    raise AudioDownloadError(f"Storage signed URL error: {e}")

            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise AudioDownloadError(
                            f"HTTP {response.status} when downloading audio"
                        )

                    # Download in chunks to handle large files
                    with open(destination, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

            if not destination.exists() or destination.stat().st_size == 0:
                raise AudioDownloadError("Downloaded file is empty or missing")

            logger.info(
                f"Successfully downloaded audio for meeting {meeting_id} "
                f"({destination.stat().st_size / 1024 / 1024:.2f} MB)"
            )
            return destination

        except aiohttp.ClientError as e:
            logger.error(f"Network error downloading audio: {e}")
            raise AudioDownloadError(f"Network error: {e}")
        except IOError as e:
            logger.error(f"File I/O error downloading audio: {e}")
            raise AudioDownloadError(f"File I/O error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading audio: {e}")
            raise AudioDownloadError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def save_transcript(
        self,
        meeting_id: str,
        transcript: Transcript
    ) -> bool:
        """
        Save transcript segments to database

        Args:
            meeting_id: Meeting identifier
            transcript: Transcript object with segments

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If save fails
        """
        try:
            # Prepare segment data for insertion
            segments_data = []
            for segment in transcript.segments:
                segment_dict = segment.dict()
                segment_dict['meeting_id'] = meeting_id
                segment_dict['created_at'] = datetime.now().isoformat()
                segments_data.append(segment_dict)

            # Insert segments in batches
            if segments_data:
                await asyncio.to_thread(
                    lambda: self.client.table('transcript_segments')
                    .insert(segments_data)
                    .execute()
                )

            logger.info(f"Saved {len(segments_data)} transcript segments for meeting {meeting_id}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error saving transcript: {e}")
            raise SupabaseQueryError(f"Failed to save transcript: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving transcript: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def save_speakers(
        self,
        meeting_id: str,
        speakers: List[Speaker]
    ) -> bool:
        """
        Save speaker data to database

        Args:
            meeting_id: Meeting identifier
            speakers: List of Speaker objects

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If save fails
        """
        try:
            speakers_data = []
            for speaker in speakers:
                speaker_dict = speaker.dict(exclude_none=True)
                if meeting_id not in speaker_dict.get('meeting_ids', []):
                    speaker_dict.setdefault('meeting_ids', []).append(meeting_id)
                speaker_dict['updated_at'] = datetime.now().isoformat()
                speakers_data.append(speaker_dict)

            if speakers_data:
                # Use upsert to handle existing speakers
                await asyncio.to_thread(
                    lambda: self.client.table('speakers')
                    .upsert(speakers_data)
                    .execute()
                )

            logger.info(f"Saved {len(speakers_data)} speakers for meeting {meeting_id}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error saving speakers: {e}")
            raise SupabaseQueryError(f"Failed to save speakers: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving speakers: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def save_summary(
        self,
        meeting_id: str,
        summary: MeetingSummary
    ) -> bool:
        """
        Save AI-generated summary to database

        Args:
            meeting_id: Meeting identifier
            summary: MeetingSummary object

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If save fails
        """
        try:
            summary_dict = summary.dict(exclude_none=True)
            summary_dict['meeting_id'] = meeting_id
            summary_dict['created_at'] = datetime.now().isoformat()

            await asyncio.to_thread(
                lambda: self.client.table('meeting_summaries')
                .insert(summary_dict)
                .execute()
            )

            logger.info(f"Saved summary for meeting {meeting_id}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error saving summary: {e}")
            raise SupabaseQueryError(f"Failed to save summary: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving summary: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def list_templates(self, user_id: str) -> List[Template]:
        """
        Get all templates for a user

        Args:
            user_id: User identifier

        Returns:
            List of Template objects

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('templates')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .execute()
            )

            templates = []
            for data in response.data:
                try:
                    template = Template(**data)
                    templates.append(template)
                except Exception as e:
                    logger.warning(f"Failed to parse template {data.get('id')}: {e}")
                    continue

            logger.debug(f"Found {len(templates)} templates for user {user_id}")
            return templates

        except APIError as e:
            logger.error(f"Supabase API error listing templates: {e}")
            raise SupabaseQueryError(f"Failed to list templates: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing templates: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def get_template_by_id(self, template_id: str, user_id: str) -> Optional[Template]:
        """
        Get a specific template by ID

        Args:
            template_id: Template identifier
            user_id: User identifier (for validation)

        Returns:
            Template object or None if not found

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('templates')
                .select('*')
                .eq('id', template_id)
                .eq('user_id', user_id)
                .single()
                .execute()
            )

            if response.data:
                return Template(**response.data)
            return None

        except APIError as e:
            logger.error(f"Supabase API error getting template {template_id}: {e}")
            raise SupabaseQueryError(f"Failed to get template: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting template {template_id}: {e}")
            return None

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def create_template(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Template]:
        """
        Create a new template

        Args:
            user_id: User identifier
            name: Template name
            description: Optional template description
            tags: Optional list of tags

        Returns:
            Created Template object or None if creation fails

        Raises:
            SupabaseQueryError: If creation fails
        """
        try:
            template_data = {
                'user_id': user_id,
                'name': name,
                'description': description,
                'tags': tags or [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            response = await asyncio.to_thread(
                lambda: self.client.table('templates')
                .insert(template_data)
                .execute()
            )

            if response.data:
                template = Template(**response.data[0])
                logger.info(f"Created template '{name}' for user {user_id}")
                return template
            return None

        except APIError as e:
            logger.error(f"Supabase API error creating template: {e}")
            raise SupabaseQueryError(f"Failed to create template: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating template: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def update_template(
        self,
        template_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing template

        Args:
            template_id: Template identifier
            user_id: User identifier (for validation)
            name: Optional new template name
            description: Optional new description
            tags: Optional new tags list

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If update fails
        """
        try:
            update_data = {
                'updated_at': datetime.now().isoformat()
            }

            if name is not None:
                update_data['name'] = name
            if description is not None:
                update_data['description'] = description
            if tags is not None:
                update_data['tags'] = tags

            await asyncio.to_thread(
                lambda: self.client.table('templates')
                .update(update_data)
                .eq('id', template_id)
                .eq('user_id', user_id)
                .execute()
            )

            logger.info(f"Updated template {template_id}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error updating template: {e}")
            raise SupabaseQueryError(f"Failed to update template: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating template: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """
        Delete a template

        Args:
            template_id: Template identifier
            user_id: User identifier (for validation)

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If deletion fails
        """
        try:
            await asyncio.to_thread(
                lambda: self.client.table('templates')
                .delete()
                .eq('id', template_id)
                .eq('user_id', user_id)
                .execute()
            )

            logger.info(f"Deleted template {template_id}")
            return True

        except APIError as e:
            logger.error(f"Supabase API error deleting template: {e}")
            raise SupabaseQueryError(f"Failed to delete template: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting template: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def health_check(self) -> bool:
        """
        Check if Supabase connection is healthy

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Try a simple query to check connection
            await asyncio.to_thread(
                lambda: self.client.table('meetings')
                .select('id')
                .limit(1)
                .execute()
            )
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """
    Get or create singleton Supabase client

    Returns:
        SupabaseClient instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
