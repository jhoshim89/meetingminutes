-- Migration: Add voice embedding support to speakers table
-- Date: 2026-01-16
-- Purpose: Enable automatic speaker matching using voice embeddings (pyannote/embedding, 768 dimensions)

-- 1. Add voice_embedding column to speakers table
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS voice_embedding vector(768);

-- 2. Add embedding metadata columns
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'pyannote/embedding';
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS embedding_confidence FLOAT;
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS last_embedding_updated TIMESTAMPTZ;

-- 3. Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_speakers_voice_embedding
    ON speakers USING hnsw (voice_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 4. Create RPC function to find similar speakers by voice embedding
CREATE OR REPLACE FUNCTION find_similar_speakers(
    p_voice_embedding vector(768),
    p_user_id UUID,
    p_limit INTEGER DEFAULT 5,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    speaker_id UUID,
    name TEXT,
    similarity FLOAT,
    embedding_model VARCHAR(100),
    is_registered BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id as speaker_id,
        s.name,
        1 - (s.voice_embedding <=> p_voice_embedding) as similarity,  -- Convert distance to similarity
        s.embedding_model,
        s.is_registered
    FROM speakers s
    WHERE s.user_id = p_user_id
        AND s.voice_embedding IS NOT NULL
        AND 1 - (s.voice_embedding <=> p_voice_embedding) >= p_similarity_threshold
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Grant execute permission
GRANT EXECUTE ON FUNCTION find_similar_speakers TO authenticated;

-- 6. Add comment for documentation
COMMENT ON COLUMN speakers.voice_embedding IS 'Voice embedding vector from pyannote/embedding model (768 dimensions)';
COMMENT ON FUNCTION find_similar_speakers IS 'Find speakers with similar voice embeddings using cosine similarity';
