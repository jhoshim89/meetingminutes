-- Migration: Initial Schema for Meeting Minutes App
-- Version: 1.0.0
-- Date: 2026-01-11
-- Description: Core tables and functions including Vector Search capability

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 1. TABLES
-- ============================================================================

-- 1.1 MEETINGS
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    audio_url TEXT,
    transcript_url TEXT,
    duration_seconds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'recording', -- 'recording', 'processing', 'completed', 'error'
    speaker_count INTEGER DEFAULT 0,
    template_id UUID, -- References templates(id), loose constraint to allow NULL
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.2 SPEAKERS
CREATE TABLE IF NOT EXISTS speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_registered BOOLEAN DEFAULT FALSE,
    voice_profile_path TEXT, -- Path to voice sample/embedding
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.3 TRANSCRIPTS
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker_id UUID REFERENCES speakers(id) ON DELETE SET NULL,
    speaker_name TEXT,
    text TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.4 TRANSCRIPT CHUNKS (For RAG/Search)
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Denormalized for RLS efficiency
    speaker_id UUID REFERENCES speakers(id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    embedding vector(1536), -- ADA-002 dimension, adjust if using different model
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1.5 TEMPLATES
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    structure JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at);

CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_id ON transcripts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_start_time ON transcripts(start_time);

CREATE INDEX IF NOT EXISTS idx_transcript_chunks_meeting_id ON transcript_chunks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_user_id ON transcript_chunks(user_id);
-- Enable HNSW index for vector similarity search if data volume grows
-- CREATE INDEX ON transcript_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_speakers_user_id ON speakers(user_id);
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON templates(user_id);


-- ============================================================================
-- 3. RLS POLICIES
-- ============================================================================

-- Enable RLS
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE speakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- 3.1 MEETINGS POLICY
CREATE POLICY "Users can manage their own meetings" ON meetings
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3.2 SPEAKERS POLICY
CREATE POLICY "Users can manage their own speakers" ON speakers
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3.3 TRANSCRIPTS POLICY (Inherits access via meeting)
-- Note: 'transcripts' table doesn't have user_id. We check meeting ownership.
CREATE POLICY "Users can view transcripts of their meetings" ON transcripts
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM meetings
        WHERE meetings.id = transcripts.meeting_id
        AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert transcripts to their meetings" ON transcripts
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM meetings
        WHERE meetings.id = transcripts.meeting_id
        AND meetings.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete transcripts of their meetings" ON transcripts
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM meetings
        WHERE meetings.id = transcripts.meeting_id
        AND meetings.user_id = auth.uid()
    ));

-- 3.4 TRANSCRIPT CHUNKS POLICY
-- We added user_id to transcript_chunks for easier/faster RLS.
CREATE POLICY "Users can manage their own transcript chunks" ON transcript_chunks
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3.5 TEMPLATES POLICY
CREATE POLICY "Users can manage their own templates" ON templates
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ============================================================================
-- 4. SEARCH FUNCTIONS (RPC)
-- ============================================================================

-- 4.1 Simple Keyword + Semantic Search (Simplified for compatibility)
-- Used by SupabaseService.hybridSearchChunks
CREATE OR REPLACE FUNCTION hybrid_search_chunks_simple(
    p_query_text TEXT,
    p_user_id UUID,
    p_meeting_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    meeting_id UUID,
    chunk_index INTEGER,
    start_time DOUBLE PRECISION,
    end_time DOUBLE PRECISION,
    speaker_id UUID,
    text TEXT,
    keyword_score DOUBLE PRECISION,
    semantic_score DOUBLE PRECISION,
    combined_score DOUBLE PRECISION
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Currently implements a simple text search as 'combined_score'.
    -- The full vector search requires updating this function to utilize embedding comparisons
    -- when embeddings are available on the client/generated via edge function.
    
    RETURN QUERY
    SELECT 
        tc.id AS chunk_id,
        tc.meeting_id,
        tc.chunk_index,
        tc.start_time,
        tc.end_time,
        tc.speaker_id,
        tc.text,
        1.0::DOUBLE PRECISION AS keyword_score, -- Placeholder
        0.0::DOUBLE PRECISION AS semantic_score, -- Placeholder
        1.0::DOUBLE PRECISION AS combined_score  -- Placeholder
    FROM transcript_chunks tc
    WHERE 
        tc.user_id = p_user_id
        AND (p_meeting_id IS NULL OR tc.meeting_id = p_meeting_id)
        AND tc.text ILIKE '%' || p_query_text || '%' -- Simple case-insensitive search
    ORDER BY tc.start_time ASC
    LIMIT p_limit;
END;
$$;


-- ============================================================================
-- 5. TRIGGERS
-- ============================================================================
-- Reuse existing timestamp trigger if available, or create new one safely

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_speakers_updated_at
    BEFORE UPDATE ON speakers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at
    BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
