"""
RAG Search Module
Implements hybrid search (keyword + semantic) for meeting transcripts

Features:
- Save transcript chunks with embeddings
- Hybrid search combining keyword and vector similarity
- Batch embedding generation and storage
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from pydantic import BaseModel, Field

from postgrest.exceptions import APIError

from config import logger
from supabase_client import get_supabase_client
from text_chunker import TextChunker, TranscriptChunk, ChunkingConfig
from embedding_engine import get_embedding_engine, EmbeddingConfig
from models import Transcript
from exceptions import SupabaseQueryError
from utils import retry_with_backoff


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SearchResult:
    """A single search result from hybrid search"""
    chunk_id: str
    meeting_id: str
    chunk_index: int
    start_time: float
    end_time: float
    speaker_id: Optional[str]
    text: str
    keyword_score: float
    semantic_score: float
    combined_score: float

    @property
    def duration(self) -> float:
        """Duration of the chunk in seconds"""
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "meeting_id": self.meeting_id,
            "chunk_index": self.chunk_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "keyword_score": self.keyword_score,
            "semantic_score": self.semantic_score,
            "combined_score": self.combined_score
        }


class SearchConfig(BaseModel):
    """Configuration for RAG search"""
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    default_limit: int = Field(default=20, ge=1, le=100)
    min_score_threshold: float = Field(default=0.1, ge=0.0, le=1.0)


# =============================================================================
# RAG Search Engine
# =============================================================================

class RAGSearchEngine:
    """
    RAG (Retrieval-Augmented Generation) search engine for meeting transcripts.

    Provides:
    - Transcript chunking and embedding
    - Hybrid search (keyword + semantic)
    - Batch operations for efficiency
    """

    def __init__(
        self,
        chunking_config: Optional[ChunkingConfig] = None,
        embedding_config: Optional[EmbeddingConfig] = None,
        search_config: Optional[SearchConfig] = None
    ):
        """
        Initialize RAG search engine.

        Args:
            chunking_config: Configuration for text chunking
            embedding_config: Configuration for embeddings
            search_config: Configuration for search
        """
        self.chunking_config = chunking_config or ChunkingConfig()
        self.embedding_config = embedding_config or EmbeddingConfig()
        self.search_config = search_config or SearchConfig()

        self._chunker = TextChunker(self.chunking_config)
        self._embedding_engine = get_embedding_engine(self.embedding_config)
        self._supabase = get_supabase_client()

        logger.info("RAGSearchEngine initialized")

    # =========================================================================
    # Indexing Operations
    # =========================================================================

    async def index_transcript(
        self,
        transcript: Transcript,
        user_id: str,
        batch_size: int = 32
    ) -> int:
        """
        Index a transcript for RAG search.

        This method:
        1. Chunks the transcript into searchable segments
        2. Generates embeddings for each chunk
        3. Stores chunks with embeddings in the database

        Args:
            transcript: Complete transcript to index
            user_id: User ID for RLS
            batch_size: Batch size for embedding generation

        Returns:
            Number of chunks indexed

        Raises:
            SupabaseQueryError: If database operation fails
        """
        logger.info(f"Indexing transcript for meeting {transcript.meeting_id}")

        # Step 1: Chunk the transcript
        chunks = self._chunker.chunk_transcript(transcript, user_id)
        if not chunks:
            logger.warning(f"No chunks generated for meeting {transcript.meeting_id}")
            return 0

        logger.info(f"Generated {len(chunks)} chunks")

        # Step 2: Generate embeddings in batches
        texts = [chunk.text for chunk in chunks]
        embeddings = await self._generate_embeddings_batch(texts, batch_size)

        logger.info(f"Generated {len(embeddings)} embeddings")

        # Step 3: Save chunks with embeddings
        await self._save_chunks_with_embeddings(chunks, embeddings)

        logger.info(f"Indexed {len(chunks)} chunks for meeting {transcript.meeting_id}")
        return len(chunks)

    async def _generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int
    ) -> List[List[float]]:
        """Generate embeddings for texts in batches"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results = await self._embedding_engine.embed_texts(batch)
            all_embeddings.extend([r.embedding for r in results])

            logger.debug(f"Embedded batch {i // batch_size + 1}")

        return all_embeddings

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def _save_chunks_with_embeddings(
        self,
        chunks: List[TranscriptChunk],
        embeddings: List[List[float]]
    ) -> None:
        """Save chunks with their embeddings to database"""
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings count mismatch")

        # Prepare records for insertion
        records = []
        for chunk, embedding in zip(chunks, embeddings):
            record = chunk.to_db_dict()
            # Format embedding as PostgreSQL vector string
            record['embedding'] = f"[{','.join(str(x) for x in embedding)}]"
            records.append(record)

        try:
            # Insert in batches of 100 (Supabase limit)
            for i in range(0, len(records), 100):
                batch = records[i:i + 100]
                await asyncio.to_thread(
                    lambda b=batch: self._supabase.client.table('transcript_chunks')
                    .insert(b)
                    .execute()
                )
                logger.debug(f"Saved batch {i // 100 + 1}")

        except APIError as e:
            logger.error(f"Database error saving chunks: {e}")
            raise SupabaseQueryError(f"Failed to save chunks: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving chunks: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def delete_meeting_chunks(self, meeting_id: str, user_id: str) -> int:
        """
        Delete all chunks for a meeting.

        Useful for re-indexing.

        Args:
            meeting_id: Meeting to delete chunks for
            user_id: User ID for RLS

        Returns:
            Number of chunks deleted
        """
        try:
            response = await asyncio.to_thread(
                lambda: self._supabase.client.table('transcript_chunks')
                .delete()
                .eq('meeting_id', meeting_id)
                .eq('user_id', user_id)
                .execute()
            )

            count = len(response.data) if response.data else 0
            logger.info(f"Deleted {count} chunks for meeting {meeting_id}")
            return count

        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise SupabaseQueryError(f"Failed to delete chunks: {e}")

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def hybrid_search(
        self,
        query: str,
        user_id: str,
        meeting_id: Optional[str] = None,
        limit: Optional[int] = None,
        keyword_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining keyword and semantic similarity.

        Args:
            query: Search query text
            user_id: User ID for RLS
            meeting_id: Optional meeting ID to search within
            limit: Maximum results to return
            keyword_weight: Weight for keyword score (0-1)
            semantic_weight: Weight for semantic score (0-1)

        Returns:
            List of SearchResult objects sorted by combined score

        Raises:
            SupabaseQueryError: If search fails
        """
        logger.info(f"Hybrid search: '{query}' for user {user_id}")

        # Use defaults if not specified
        limit = limit or self.search_config.default_limit
        keyword_weight = keyword_weight if keyword_weight is not None else self.search_config.keyword_weight
        semantic_weight = semantic_weight if semantic_weight is not None else self.search_config.semantic_weight

        # Generate query embedding
        query_embedding = await self._embedding_engine.embed_query(query)

        # Call hybrid search function
        try:
            response = await asyncio.to_thread(
                lambda: self._supabase.client.rpc(
                    'hybrid_search_chunks',
                    {
                        'p_query_text': query,
                        'p_query_embedding': f"[{','.join(str(x) for x in query_embedding)}]",
                        'p_user_id': user_id,
                        'p_meeting_id': meeting_id,
                        'p_limit': limit,
                        'p_keyword_weight': keyword_weight,
                        'p_semantic_weight': semantic_weight
                    }
                ).execute()
            )

            results = []
            for row in response.data or []:
                # Filter by minimum score threshold
                if row['combined_score'] < self.search_config.min_score_threshold:
                    continue

                results.append(SearchResult(
                    chunk_id=row['chunk_id'],
                    meeting_id=row['meeting_id'],
                    chunk_index=row['chunk_index'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    speaker_id=row.get('speaker_id'),
                    text=row['text'],
                    keyword_score=row['keyword_score'],
                    semantic_score=row['semantic_score'],
                    combined_score=row['combined_score']
                ))

            logger.info(f"Found {len(results)} results")
            return results

        except APIError as e:
            logger.error(f"Search API error: {e}")
            raise SupabaseQueryError(f"Search failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def semantic_search(
        self,
        query: str,
        user_id: str,
        meeting_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Perform pure semantic (vector) search.

        Args:
            query: Search query text
            user_id: User ID for RLS
            meeting_id: Optional meeting ID to search within
            limit: Maximum results to return

        Returns:
            List of SearchResult objects sorted by similarity
        """
        logger.info(f"Semantic search: '{query}' for user {user_id}")

        limit = limit or self.search_config.default_limit

        # Generate query embedding
        query_embedding = await self._embedding_engine.embed_query(query)

        try:
            response = await asyncio.to_thread(
                lambda: self._supabase.client.rpc(
                    'semantic_search_chunks',
                    {
                        'p_query_embedding': f"[{','.join(str(x) for x in query_embedding)}]",
                        'p_user_id': user_id,
                        'p_meeting_id': meeting_id,
                        'p_limit': limit
                    }
                ).execute()
            )

            results = []
            for row in response.data or []:
                results.append(SearchResult(
                    chunk_id=row['chunk_id'],
                    meeting_id=row['meeting_id'],
                    chunk_index=row['chunk_index'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    speaker_id=row.get('speaker_id'),
                    text=row['text'],
                    keyword_score=0.0,
                    semantic_score=row['similarity'],
                    combined_score=row['similarity']
                ))

            logger.info(f"Found {len(results)} results")
            return results

        except APIError as e:
            logger.error(f"Search API error: {e}")
            raise SupabaseQueryError(f"Search failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def keyword_search(
        self,
        query: str,
        user_id: str,
        meeting_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Perform pure keyword (full-text) search.

        Args:
            query: Search query text
            user_id: User ID for RLS
            meeting_id: Optional meeting ID to search within
            limit: Maximum results to return

        Returns:
            List of SearchResult objects sorted by relevance
        """
        logger.info(f"Keyword search: '{query}' for user {user_id}")

        limit = limit or self.search_config.default_limit

        try:
            # Build query
            query_builder = self._supabase.client.table('transcript_chunks') \
                .select('*') \
                .eq('user_id', user_id) \
                .text_search('text_search', query, config='simple') \
                .limit(limit)

            if meeting_id:
                query_builder = query_builder.eq('meeting_id', meeting_id)

            response = await asyncio.to_thread(lambda: query_builder.execute())

            results = []
            for row in response.data or []:
                results.append(SearchResult(
                    chunk_id=row['id'],
                    meeting_id=row['meeting_id'],
                    chunk_index=row['chunk_index'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    speaker_id=row.get('speaker_id'),
                    text=row['text'],
                    keyword_score=1.0,  # Placeholder - actual rank from ts_rank
                    semantic_score=0.0,
                    combined_score=1.0
                ))

            logger.info(f"Found {len(results)} results")
            return results

        except APIError as e:
            logger.error(f"Search API error: {e}")
            raise SupabaseQueryError(f"Search failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def get_chunk_count(self, user_id: str, meeting_id: Optional[str] = None) -> int:
        """Get total number of chunks for a user or meeting"""
        try:
            query = self._supabase.client.table('transcript_chunks') \
                .select('id', count='exact') \
                .eq('user_id', user_id)

            if meeting_id:
                query = query.eq('meeting_id', meeting_id)

            response = await asyncio.to_thread(lambda: query.execute())
            return response.count or 0

        except Exception as e:
            logger.error(f"Error getting chunk count: {e}")
            return 0


# =============================================================================
# Singleton Instance
# =============================================================================

_search_engine: Optional[RAGSearchEngine] = None


def get_rag_search_engine(
    chunking_config: Optional[ChunkingConfig] = None,
    embedding_config: Optional[EmbeddingConfig] = None,
    search_config: Optional[SearchConfig] = None
) -> RAGSearchEngine:
    """Get or create singleton RAG search engine"""
    global _search_engine

    if _search_engine is None:
        _search_engine = RAGSearchEngine(
            chunking_config=chunking_config,
            embedding_config=embedding_config,
            search_config=search_config
        )

    return _search_engine


# =============================================================================
# Convenience Functions
# =============================================================================

async def index_meeting_transcript(
    transcript: Transcript,
    user_id: str
) -> int:
    """Index a meeting transcript for RAG search"""
    engine = get_rag_search_engine()
    return await engine.index_transcript(transcript, user_id)


async def search_meetings(
    query: str,
    user_id: str,
    meeting_id: Optional[str] = None,
    limit: int = 20
) -> List[SearchResult]:
    """Search meeting transcripts using hybrid search"""
    engine = get_rag_search_engine()
    return await engine.hybrid_search(query, user_id, meeting_id, limit)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    async def main():
        """Test RAG search engine"""
        print("=== RAG Search Engine Test ===\n")

        from models import TranscriptSegment

        # Create test transcript
        segments = [
            TranscriptSegment(
                meeting_id="test-meeting-123",
                start_time=0.0,
                end_time=5.0,
                speaker_id="speaker-1",
                text="프로젝트 진행 상황에 대해 논의하겠습니다.",
                confidence=0.95
            ),
            TranscriptSegment(
                meeting_id="test-meeting-123",
                start_time=5.0,
                end_time=12.0,
                speaker_id="speaker-2",
                text="현재 개발 진행률은 80%입니다. 다음 주까지 완료 예정입니다.",
                confidence=0.92
            ),
            TranscriptSegment(
                meeting_id="test-meeting-123",
                start_time=12.0,
                end_time=20.0,
                speaker_id="speaker-1",
                text="좋습니다. 일정에 문제가 없겠네요. 품질 테스트 계획은 어떻게 되나요?",
                confidence=0.90
            ),
        ]

        transcript = Transcript(
            meeting_id="test-meeting-123",
            segments=segments,
            language="ko",
            duration=20.0
        )

        # Initialize engine
        engine = RAGSearchEngine()

        # Test indexing (dry run - don't actually save)
        print("Testing chunker...")
        chunker = TextChunker()
        chunks = chunker.chunk_transcript(transcript, "test-user-456")
        print(f"Created {len(chunks)} chunks")

        for chunk in chunks:
            print(f"  Chunk {chunk.chunk_index}: {chunk.text[:50]}...")

        # Test embedding (if model is available)
        print("\nTesting embeddings...")
        try:
            embedding_engine = get_embedding_engine()
            query_embedding = await embedding_engine.embed_query("프로젝트 진행 상황")
            print(f"Query embedding dim: {len(query_embedding)}")
        except Exception as e:
            print(f"Embedding test skipped: {e}")

        print("\n=== Test Complete ===")

    asyncio.run(main())
