-- Migration: Fix speaker voice embedding dimension
-- Date: 2026-01-27
-- Purpose: Change voice_embedding from 768 to 512 dimensions to match pyannote/embedding actual output
-- Note: pyannote 3.0 uses wespeaker-based 512-dimensional embeddings

-- 1. Drop the existing HNSW index (required before column change)
DROP INDEX IF EXISTS idx_speakers_voice_embedding;

-- 2. Drop existing function that uses the old dimension
DROP FUNCTION IF EXISTS find_similar_speakers(vector(768), UUID, INTEGER, FLOAT);

-- 3. Change column dimension (pgvector requires dropping and recreating)
-- First, backup any existing embeddings (if any)
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS voice_embedding_backup vector(768);
UPDATE speakers SET voice_embedding_backup = voice_embedding WHERE voice_embedding IS NOT NULL;

-- 4. Drop old column and create new one with correct dimension
ALTER TABLE speakers DROP COLUMN IF EXISTS voice_embedding;
ALTER TABLE speakers ADD COLUMN voice_embedding vector(512);

-- 5. Note: Existing embeddings cannot be migrated (dimension mismatch)
-- They will need to be re-extracted from audio. This is expected since
-- the old dimension was incorrect and no valid embeddings should exist.

-- 6. Drop backup column
ALTER TABLE speakers DROP COLUMN IF EXISTS voice_embedding_backup;

-- 7. Recreate HNSW index with correct dimension
CREATE INDEX IF NOT EXISTS idx_speakers_voice_embedding
    ON speakers USING hnsw (voice_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 8. Recreate RPC function with correct dimension (512)
CREATE OR REPLACE FUNCTION find_similar_speakers(
    p_voice_embedding vector(512),
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

-- 9. Grant execute permission
GRANT EXECUTE ON FUNCTION find_similar_speakers(vector(512), UUID, INTEGER, FLOAT) TO authenticated;

-- 10. Update comments
COMMENT ON COLUMN speakers.voice_embedding IS 'Voice embedding vector from pyannote/embedding model (512 dimensions, wespeaker-based)';
COMMENT ON FUNCTION find_similar_speakers(vector(512), UUID, INTEGER, FLOAT) IS 'Find speakers with similar voice embeddings using cosine similarity (512-dim pyannote embeddings)';
