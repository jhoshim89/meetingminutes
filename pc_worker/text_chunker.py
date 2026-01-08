"""
Text Chunker for RAG Search
Splits transcripts into semantic chunks for embedding and search

Chunking Strategy:
1. Target chunk duration: 5-10 seconds
2. Respect sentence boundaries (don't split mid-sentence)
3. Consider speaker changes (new speaker = new chunk)
4. Merge very short segments into adjacent chunks
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field

from models import TranscriptSegment, Transcript
from logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class ChunkingConfig(BaseModel):
    """Configuration for text chunking"""
    min_chunk_duration: float = Field(default=3.0, description="Minimum chunk duration in seconds")
    target_chunk_duration: float = Field(default=7.0, description="Target chunk duration in seconds")
    max_chunk_duration: float = Field(default=12.0, description="Maximum chunk duration in seconds")
    min_chunk_chars: int = Field(default=20, description="Minimum characters per chunk")
    respect_speaker_changes: bool = Field(default=True, description="Start new chunk on speaker change")
    respect_sentence_boundaries: bool = Field(default=True, description="Avoid splitting mid-sentence")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TranscriptChunk:
    """A chunk of transcript for embedding and search"""
    chunk_index: int
    meeting_id: str
    user_id: str
    start_time: float
    end_time: float
    text: str
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None

    @property
    def duration(self) -> float:
        """Duration of chunk in seconds"""
        return self.end_time - self.start_time

    def to_db_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        return {
            "chunk_index": self.chunk_index,
            "meeting_id": self.meeting_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "speaker_id": self.speaker_id,
        }


# =============================================================================
# Text Chunker
# =============================================================================

class TextChunker:
    """
    Splits transcript segments into chunks optimized for RAG search.

    The chunker balances multiple concerns:
    - Chunk size (5-10 seconds for good search granularity)
    - Sentence boundaries (preserve semantic meaning)
    - Speaker changes (preserve conversation context)
    """

    # Korean sentence-ending patterns
    KOREAN_SENTENCE_ENDINGS = re.compile(r'[.!?。！？](?:\s|$)|(?:다|요|죠|네|까)(?:\s|$)')

    # General sentence boundaries
    SENTENCE_BOUNDARIES = re.compile(r'[.!?。！？]\s+')

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker with configuration"""
        self.config = config or ChunkingConfig()
        logger.info(f"TextChunker initialized with config: {self.config}")

    def chunk_transcript(
        self,
        transcript: Transcript,
        user_id: str
    ) -> List[TranscriptChunk]:
        """
        Split a transcript into chunks for RAG search.

        Args:
            transcript: Complete transcript with segments
            user_id: User ID for RLS

        Returns:
            List of TranscriptChunk objects ready for embedding
        """
        if not transcript.segments:
            logger.warning(f"Empty transcript for meeting {transcript.meeting_id}")
            return []

        logger.info(f"Chunking transcript for meeting {transcript.meeting_id} "
                   f"({len(transcript.segments)} segments)")

        # Step 1: Merge very short adjacent segments from same speaker
        merged_segments = self._merge_short_segments(transcript.segments)
        logger.debug(f"After merging: {len(merged_segments)} segments")

        # Step 2: Create chunks based on time and speaker boundaries
        chunks = self._create_chunks(merged_segments, transcript.meeting_id, user_id)
        logger.info(f"Created {len(chunks)} chunks for meeting {transcript.meeting_id}")

        return chunks

    def chunk_segments(
        self,
        segments: List[TranscriptSegment],
        meeting_id: str,
        user_id: str
    ) -> List[TranscriptChunk]:
        """
        Chunk a list of transcript segments directly.

        Args:
            segments: List of transcript segments
            meeting_id: Meeting ID
            user_id: User ID for RLS

        Returns:
            List of TranscriptChunk objects
        """
        if not segments:
            return []

        # Create a temporary Transcript object
        transcript = Transcript(
            meeting_id=meeting_id,
            segments=segments
        )

        return self.chunk_transcript(transcript, user_id)

    def _merge_short_segments(
        self,
        segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """
        Merge very short segments from the same speaker.

        This prevents creating too many tiny chunks and improves
        embedding quality by providing more context.
        """
        if len(segments) <= 1:
            return segments

        merged = []
        current = segments[0]

        for next_seg in segments[1:]:
            # Check if we should merge
            same_speaker = (
                current.speaker_id == next_seg.speaker_id and
                current.speaker_label == next_seg.speaker_label
            )

            current_duration = current.end_time - current.start_time
            combined_duration = next_seg.end_time - current.start_time

            # Merge if same speaker, current is short, and combined isn't too long
            if (same_speaker and
                current_duration < self.config.min_chunk_duration and
                combined_duration <= self.config.max_chunk_duration):

                # Merge segments
                current = TranscriptSegment(
                    meeting_id=current.meeting_id,
                    start_time=current.start_time,
                    end_time=next_seg.end_time,
                    speaker_id=current.speaker_id,
                    speaker_label=current.speaker_label,
                    text=f"{current.text} {next_seg.text}".strip(),
                    confidence=min(
                        current.confidence or 1.0,
                        next_seg.confidence or 1.0
                    )
                )
            else:
                merged.append(current)
                current = next_seg

        merged.append(current)
        return merged

    def _create_chunks(
        self,
        segments: List[TranscriptSegment],
        meeting_id: str,
        user_id: str
    ) -> List[TranscriptChunk]:
        """
        Create chunks from merged segments.

        Uses a greedy algorithm that:
        1. Accumulates segments until target duration is reached
        2. Respects speaker boundaries if configured
        3. Tries to end at sentence boundaries
        """
        chunks = []
        chunk_index = 0

        # Accumulator for current chunk
        current_texts: List[str] = []
        current_start: Optional[float] = None
        current_end: float = 0.0
        current_speaker_id: Optional[str] = None
        current_speaker_label: Optional[str] = None

        for segment in segments:
            # Check for speaker change
            speaker_changed = (
                self.config.respect_speaker_changes and
                current_speaker_id is not None and
                segment.speaker_id != current_speaker_id
            )

            # Check if adding this segment would exceed max duration
            if current_start is not None:
                would_exceed_max = (
                    segment.end_time - current_start > self.config.max_chunk_duration
                )
            else:
                would_exceed_max = False

            # Check if we've reached target duration
            current_duration = current_end - (current_start or 0)
            reached_target = current_duration >= self.config.target_chunk_duration

            # Decide whether to finalize current chunk
            should_finalize = (
                current_texts and
                (speaker_changed or would_exceed_max or
                 (reached_target and self._is_sentence_end(current_texts[-1])))
            )

            if should_finalize:
                # Create chunk from accumulated data
                chunk = TranscriptChunk(
                    chunk_index=chunk_index,
                    meeting_id=meeting_id,
                    user_id=user_id,
                    start_time=current_start,
                    end_time=current_end,
                    text=" ".join(current_texts),
                    speaker_id=current_speaker_id,
                    speaker_label=current_speaker_label
                )
                chunks.append(chunk)
                chunk_index += 1

                # Reset accumulator
                current_texts = []
                current_start = None
                current_speaker_id = None
                current_speaker_label = None

            # Add segment to accumulator
            if current_start is None:
                current_start = segment.start_time
                current_speaker_id = segment.speaker_id
                current_speaker_label = segment.speaker_label

            current_texts.append(segment.text)
            current_end = segment.end_time

        # Don't forget the last chunk
        if current_texts and current_start is not None:
            chunk = TranscriptChunk(
                chunk_index=chunk_index,
                meeting_id=meeting_id,
                user_id=user_id,
                start_time=current_start,
                end_time=current_end,
                text=" ".join(current_texts),
                speaker_id=current_speaker_id,
                speaker_label=current_speaker_label
            )
            chunks.append(chunk)

        return chunks

    def _is_sentence_end(self, text: str) -> bool:
        """
        Check if text ends with a sentence boundary.

        Handles both English and Korean sentence endings.
        """
        if not text:
            return False

        text = text.strip()
        if not text:
            return False

        # Check standard punctuation
        if text[-1] in '.!?。！？':
            return True

        # Check Korean sentence endings
        if self.KOREAN_SENTENCE_ENDINGS.search(text[-2:] if len(text) > 1 else text):
            return True

        return False

    def estimate_chunk_count(self, transcript: Transcript) -> int:
        """
        Estimate the number of chunks without actually chunking.

        Useful for progress reporting.
        """
        if not transcript.segments:
            return 0

        total_duration = transcript.duration or (
            transcript.segments[-1].end_time - transcript.segments[0].start_time
        )

        # Rough estimate based on target duration
        estimated = int(total_duration / self.config.target_chunk_duration) + 1
        return max(1, estimated)


# =============================================================================
# Utility Functions
# =============================================================================

def chunk_transcript_for_rag(
    transcript: Transcript,
    user_id: str,
    config: Optional[ChunkingConfig] = None
) -> List[TranscriptChunk]:
    """
    Convenience function to chunk a transcript for RAG.

    Args:
        transcript: Complete transcript
        user_id: User ID for RLS
        config: Optional chunking configuration

    Returns:
        List of TranscriptChunk objects
    """
    chunker = TextChunker(config)
    return chunker.chunk_transcript(transcript, user_id)


def chunks_to_db_records(chunks: List[TranscriptChunk]) -> List[dict]:
    """
    Convert chunks to database record format.

    Args:
        chunks: List of TranscriptChunk objects

    Returns:
        List of dictionaries ready for database insertion
    """
    return [chunk.to_db_dict() for chunk in chunks]


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Example transcript for testing
    segments = [
        TranscriptSegment(
            meeting_id="test-meeting-123",
            start_time=0.0,
            end_time=3.5,
            speaker_id="speaker-1",
            speaker_label="SPEAKER_00",
            text="안녕하세요. 오늘 회의를 시작하겠습니다.",
            confidence=0.95
        ),
        TranscriptSegment(
            meeting_id="test-meeting-123",
            start_time=3.5,
            end_time=8.2,
            speaker_id="speaker-1",
            speaker_label="SPEAKER_00",
            text="첫 번째 안건은 프로젝트 진행 상황입니다.",
            confidence=0.92
        ),
        TranscriptSegment(
            meeting_id="test-meeting-123",
            start_time=8.2,
            end_time=15.0,
            speaker_id="speaker-2",
            speaker_label="SPEAKER_01",
            text="네, 현재 개발 진행률은 약 80% 정도입니다. 다음 주까지 완료 예정입니다.",
            confidence=0.88
        ),
        TranscriptSegment(
            meeting_id="test-meeting-123",
            start_time=15.0,
            end_time=20.5,
            speaker_id="speaker-1",
            speaker_label="SPEAKER_00",
            text="좋습니다. 일정에 문제가 없겠네요. 다음 안건으로 넘어가죠.",
            confidence=0.91
        ),
    ]

    transcript = Transcript(
        meeting_id="test-meeting-123",
        segments=segments,
        language="ko",
        duration=20.5
    )

    # Create chunker and process
    chunker = TextChunker()
    chunks = chunker.chunk_transcript(transcript, user_id="test-user-456")

    print(f"\n=== Chunking Result ===")
    print(f"Input: {len(segments)} segments")
    print(f"Output: {len(chunks)} chunks\n")

    for chunk in chunks:
        print(f"Chunk {chunk.chunk_index}:")
        print(f"  Time: {chunk.start_time:.1f}s - {chunk.end_time:.1f}s ({chunk.duration:.1f}s)")
        print(f"  Speaker: {chunk.speaker_label}")
        print(f"  Text: {chunk.text[:50]}...")
        print()
