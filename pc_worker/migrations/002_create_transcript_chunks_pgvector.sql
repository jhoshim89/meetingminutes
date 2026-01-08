-- Migration: Create transcript_chunks table with pgvector for RAG search
-- Description: Enables hybrid search (semantic + keyword) for meeting transcripts
-- Date: 2026-01-09
-- Task: 4.1.1 - RAG Hybrid Search Foundation

-- ============================================================================
-- 1. Enable pgvector extension (if not already enabled)
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 2. Create transcript_chunks table
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Chunk metadata
    chunk_index INTEGER NOT NULL,           -- Sequential order within meeting
    start_time FLOAT NOT NULL,              -- Start time in seconds
    end_time FLOAT NOT NULL,                -- End time in seconds
    speaker_id UUID REFERENCES public.speakers(id) ON DELETE SET NULL,

    -- Content
    text TEXT NOT NULL,                     -- Chunk text content

    -- Search vectors
    embedding vector(1024),                 -- BGE-M3 embedding (1024 dimensions)
    text_search tsvector                    -- Full-text search vector
        GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chunk_index_positive CHECK (chunk_index >= 0),
    CONSTRAINT valid_time_range CHECK (start_time >= 0 AND end_time > start_time),
    CONSTRAINT text_not_empty CHECK (text != '')
);

-- ============================================================================
-- 3. Create indexes for efficient querying
-- ============================================================================

-- Index for meeting_id lookups (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_meeting_id
    ON public.transcript_chunks(meeting_id);

-- Index for user_id lookups (RLS filtering)
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_user_id
    ON public.transcript_chunks(user_id);

-- Index for chunk ordering within a meeting
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_meeting_order
    ON public.transcript_chunks(meeting_id, chunk_index);

-- GIN index for full-text search (keyword search)
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_text_search
    ON public.transcript_chunks USING GIN(text_search);

-- IVFFlat index for vector similarity search (semantic search)
-- Note: lists = sqrt(n) where n is expected number of rows
-- Starting with 100 lists, suitable for up to ~10,000 chunks
-- Rebuild with more lists as data grows: ALTER INDEX ... SET (lists = ...)
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_embedding
    ON public.transcript_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================================
-- 4. Enable Row Level Security (RLS)
-- ============================================================================
ALTER TABLE public.transcript_chunks ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can select their own chunks
CREATE POLICY "Users can select their own transcript chunks"
    ON public.transcript_chunks
    FOR SELECT
    USING (auth.uid() = user_id);

-- RLS Policy: Users can insert chunks for themselves
CREATE POLICY "Users can insert their own transcript chunks"
    ON public.transcript_chunks
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own chunks
CREATE POLICY "Users can update their own transcript chunks"
    ON public.transcript_chunks
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can delete their own chunks
CREATE POLICY "Users can delete their own transcript chunks"
    ON public.transcript_chunks
    FOR DELETE
    USING (auth.uid() = user_id);

-- Grant service_role access (for PC Worker)
GRANT ALL ON public.transcript_chunks TO service_role;

-- ============================================================================
-- 5. Create hybrid search function
-- ============================================================================
-- This function combines keyword (BM25-like) and semantic (vector) search
-- Returns chunks ranked by combined score

CREATE OR REPLACE FUNCTION public.hybrid_search_chunks(
    p_query_text TEXT,
    p_query_embedding vector(1024),
    p_user_id UUID,
    p_meeting_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 20,
    p_keyword_weight FLOAT DEFAULT 0.3,
    p_semantic_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id UUID,
    meeting_id UUID,
    chunk_index INTEGER,
    start_time FLOAT,
    end_time FLOAT,
    speaker_id UUID,
    text TEXT,
    keyword_score FLOAT,
    semantic_score FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    WITH keyword_results AS (
        SELECT
            tc.id,
            ts_rank_cd(tc.text_search, plainto_tsquery('simple', p_query_text)) AS kw_score
        FROM public.transcript_chunks tc
        WHERE tc.user_id = p_user_id
            AND (p_meeting_id IS NULL OR tc.meeting_id = p_meeting_id)
            AND tc.text_search @@ plainto_tsquery('simple', p_query_text)
    ),
    semantic_results AS (
        SELECT
            tc.id,
            1 - (tc.embedding <=> p_query_embedding) AS sem_score  -- Cosine similarity
        FROM public.transcript_chunks tc
        WHERE tc.user_id = p_user_id
            AND (p_meeting_id IS NULL OR tc.meeting_id = p_meeting_id)
            AND tc.embedding IS NOT NULL
        ORDER BY tc.embedding <=> p_query_embedding
        LIMIT p_limit * 3  -- Get more candidates for merging
    ),
    combined AS (
        SELECT
            COALESCE(kr.id, sr.id) AS id,
            COALESCE(kr.kw_score, 0) AS kw_score,
            COALESCE(sr.sem_score, 0) AS sem_score,
            (COALESCE(kr.kw_score, 0) * p_keyword_weight +
             COALESCE(sr.sem_score, 0) * p_semantic_weight) AS combined
        FROM keyword_results kr
        FULL OUTER JOIN semantic_results sr ON kr.id = sr.id
    )
    SELECT
        tc.id AS chunk_id,
        tc.meeting_id,
        tc.chunk_index,
        tc.start_time,
        tc.end_time,
        tc.speaker_id,
        tc.text,
        c.kw_score::FLOAT AS keyword_score,
        c.sem_score::FLOAT AS semantic_score,
        c.combined::FLOAT AS combined_score
    FROM combined c
    JOIN public.transcript_chunks tc ON tc.id = c.id
    ORDER BY c.combined DESC
    LIMIT p_limit;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.hybrid_search_chunks TO authenticated;

-- ============================================================================
-- 6. Create semantic-only search function (for pure vector search)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.semantic_search_chunks(
    p_query_embedding vector(1024),
    p_user_id UUID,
    p_meeting_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    meeting_id UUID,
    chunk_index INTEGER,
    start_time FLOAT,
    end_time FLOAT,
    speaker_id UUID,
    text TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        tc.id AS chunk_id,
        tc.meeting_id,
        tc.chunk_index,
        tc.start_time,
        tc.end_time,
        tc.speaker_id,
        tc.text,
        (1 - (tc.embedding <=> p_query_embedding))::FLOAT AS similarity
    FROM public.transcript_chunks tc
    WHERE tc.user_id = p_user_id
        AND (p_meeting_id IS NULL OR tc.meeting_id = p_meeting_id)
        AND tc.embedding IS NOT NULL
    ORDER BY tc.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.semantic_search_chunks TO authenticated;

-- ============================================================================
-- 7. Create helper function to set IVFFlat probes
-- ============================================================================
-- Higher probes = better accuracy, slower search
-- Recommended: probes = sqrt(lists)

CREATE OR REPLACE FUNCTION public.set_ivfflat_probes(p_probes INTEGER DEFAULT 10)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    EXECUTE format('SET ivfflat.probes = %s', p_probes);
END;
$$;

GRANT EXECUTE ON FUNCTION public.set_ivfflat_probes TO service_role;

-- ============================================================================
-- 8. Add comments for documentation
-- ============================================================================
COMMENT ON TABLE public.transcript_chunks IS
    'Chunked transcript segments with embeddings for RAG search. Each chunk represents 5-10 seconds of meeting audio.';

COMMENT ON COLUMN public.transcript_chunks.embedding IS
    'BGE-M3 embedding vector (1024 dimensions) for semantic similarity search';

COMMENT ON COLUMN public.transcript_chunks.text_search IS
    'Auto-generated tsvector for full-text keyword search';

COMMENT ON FUNCTION public.hybrid_search_chunks IS
    'Hybrid search combining keyword (BM25-like) and semantic (vector) search with configurable weights';

COMMENT ON FUNCTION public.semantic_search_chunks IS
    'Pure semantic search using vector similarity (cosine distance)';
