import asyncio
import os
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

from supabase_client import get_supabase_client
from summarizer import get_summarizer
from models import TranscriptSegment, Transcript
from logger import get_logger

logger = get_logger("backfill_summaries")


async def backfill_summaries():
    """
    Backfill summaries for meetings that have transcripts but no summary.
    """
    supabase = get_supabase_client()
    summarizer = get_summarizer()

    # 1. Check Ollama health
    logger.info("Checking Ollama health...")
    if not await summarizer.health_check():
        logger.error("Ollama server is not healthy. Please start Ollama first.")
        return

    # 2. Find meetings with transcripts
    logger.info("Fetching meetings with transcripts...")
    try:
        # We need to find meetings that have transcripts but NOT in meeting_summaries
        # 1. Get all meetings with transcripts
        # Since Supabase join query might be complex via client, we'll do it in two steps or use a raw query if possible,
        # but let's stick to client methods for safety.

        # Get all meetings that are 'completed'
        meetings_response = (
            supabase.client.table("meetings")
            .select("id, title")
            .eq("status", "completed")
            .execute()
        )
        completed_meetings = meetings_response.data

        logger.info(f"Found {len(completed_meetings)} completed meetings.")

        for meeting in completed_meetings:
            meeting_id = meeting["id"]
            meeting_title = meeting["title"]

            # Check if summary exists
            summary_response = (
                supabase.client.table("meeting_summaries")
                .select("id")
                .eq("meeting_id", meeting_id)
                .execute()
            )
            if summary_response.data:
                logger.info(
                    f"Meeting '{meeting_title}' ({meeting_id}) already has a summary. Skipping."
                )
                continue

            logger.info(f"Processing meeting '{meeting_title}' ({meeting_id})...")

            # Fetch transcript
            transcript_response = (
                supabase.client.table("transcripts")
                .select("*")
                .eq("meeting_id", meeting_id)
                .order("start_time")
                .execute()
            )
            segments_data = transcript_response.data

            if not segments_data:
                logger.warning(
                    f"Meeting '{meeting_title}' ({meeting_id}) has no transcript segments. Skipping."
                )
                continue

            # Convert to TranscriptSegment objects
            segments = []
            for seg in segments_data:
                try:
                    segments.append(TranscriptSegment(**seg))
                except Exception as e:
                    logger.warning(f"Error parsing segment: {e}")

            if not segments:
                continue

            # Generate summary
            logger.info(
                f"Generating summary for '{meeting_title}' ({len(segments)} segments)..."
            )
            try:
                summary = await summarizer.summarize_with_retry(
                    segments=segments, meeting_id=meeting_id, extract_details=True
                )

                if summary:
                    # Save summary
                    await supabase.save_summary(meeting_id, summary)
                    logger.info(f"Successfully saved summary for '{meeting_title}'")
                else:
                    logger.error(f"Failed to generate summary for '{meeting_title}'")

            except Exception as e:
                logger.error(f"Error processing meeting '{meeting_title}': {e}")

            # Sleep briefly to avoid overwhelming Ollama
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Unexpected error during backfill: {e}")


if __name__ == "__main__":
    asyncio.run(backfill_summaries())
