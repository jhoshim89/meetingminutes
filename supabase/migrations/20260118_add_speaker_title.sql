-- Migration: Add title (position/role) to speakers table
-- Date: 2026-01-18
-- Purpose: Support speaker pre-registration with job titles for meeting participants

-- 1. Add title column to speakers table
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS title TEXT;

-- 2. Add comment for documentation
COMMENT ON COLUMN speakers.title IS 'Job title or position of the speaker (e.g., 학장, 부학장)';

-- 3. Create RPC function to get pre-registered speakers
CREATE OR REPLACE FUNCTION get_preregistered_speakers(
    p_user_id UUID
)
RETURNS TABLE (
    speaker_id UUID,
    name TEXT,
    title TEXT,
    is_registered BOOLEAN,
    has_voice_profile BOOLEAN,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id as speaker_id,
        s.name,
        s.title,
        s.is_registered,
        (s.voice_embedding IS NOT NULL) as has_voice_profile,
        s.created_at
    FROM speakers s
    WHERE s.user_id = p_user_id
        AND s.is_registered = TRUE
    ORDER BY s.name ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Update find_similar_speakers to include title
DROP FUNCTION IF EXISTS find_similar_speakers(vector(768), UUID, INTEGER, FLOAT);

CREATE OR REPLACE FUNCTION find_similar_speakers(
    p_voice_embedding vector(768),
    p_user_id UUID,
    p_limit INTEGER DEFAULT 5,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    speaker_id UUID,
    name TEXT,
    title TEXT,
    similarity FLOAT,
    embedding_model VARCHAR(100),
    is_registered BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id as speaker_id,
        s.name,
        s.title,
        1 - (s.voice_embedding <=> p_voice_embedding) as similarity,
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

-- 5. Create RPC function to update speaker voice embedding (for manual matching)
CREATE OR REPLACE FUNCTION copy_speaker_embedding(
    p_source_speaker_id UUID,
    p_target_speaker_id UUID,
    p_user_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_source_embedding vector(768);
    v_source_model VARCHAR(100);
    v_source_confidence FLOAT;
BEGIN
    -- Get source embedding
    SELECT voice_embedding, embedding_model, embedding_confidence
    INTO v_source_embedding, v_source_model, v_source_confidence
    FROM speakers
    WHERE id = p_source_speaker_id
        AND user_id = p_user_id;

    IF v_source_embedding IS NULL THEN
        RAISE EXCEPTION 'Source speaker has no voice embedding';
    END IF;

    -- Copy to target
    UPDATE speakers
    SET
        voice_embedding = v_source_embedding,
        embedding_model = v_source_model,
        embedding_confidence = v_source_confidence,
        last_embedding_updated = NOW(),
        updated_at = NOW()
    WHERE id = p_target_speaker_id
        AND user_id = p_user_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Grant execute permissions
GRANT EXECUTE ON FUNCTION get_preregistered_speakers TO authenticated;
GRANT EXECUTE ON FUNCTION find_similar_speakers TO authenticated;
GRANT EXECUTE ON FUNCTION copy_speaker_embedding TO authenticated;

-- 7. Comments for documentation
COMMENT ON FUNCTION get_preregistered_speakers IS 'Get all pre-registered speakers for a user';
COMMENT ON FUNCTION copy_speaker_embedding IS 'Copy voice embedding from one speaker to another (for manual matching)';
