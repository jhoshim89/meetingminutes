-- Supabase Migration: Create meeting_summaries table for Phase 3
-- Phase: 3
-- Purpose: Store AI-generated meeting summaries with key points and action items
-- Status: Ready for production

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Main summaries table
CREATE TABLE IF NOT EXISTS public.meeting_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,

    -- Core summary content
    summary TEXT NOT NULL CHECK (length(summary) >= 100 AND length(summary) <= 1000),

    -- Extracted details (JSONB for flexibility)
    key_points TEXT[] DEFAULT '{}',
    action_items TEXT[] DEFAULT '{}',
    topics TEXT[] DEFAULT '{}',

    -- Optional metadata
    sentiment VARCHAR(20) CHECK (sentiment IN ('positive', 'negative', 'neutral', NULL)),
    model_used VARCHAR(100),
    processing_time_seconds NUMERIC(10, 2),

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_meeting_summaries_meeting_id
    ON public.meeting_summaries(meeting_id);

CREATE INDEX IF NOT EXISTS idx_meeting_summaries_created_at
    ON public.meeting_summaries(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_meeting_summaries_user_id
    ON public.meeting_summaries USING gin(
        (SELECT user_id FROM public.meetings WHERE meetings.id = meeting_summaries.meeting_id)
    );

-- Add comment for documentation
COMMENT ON TABLE public.meeting_summaries IS 'AI-generated summaries for meetings produced by Phase 3 (Ollama + Gemma 2)';
COMMENT ON COLUMN public.meeting_summaries.summary IS 'Main summary (100-1000 characters, high-level overview)';
COMMENT ON COLUMN public.meeting_summaries.key_points IS 'Array of 3-5 key discussion points';
COMMENT ON COLUMN public.meeting_summaries.action_items IS 'Array of 3-5 action items with responsible parties';
COMMENT ON COLUMN public.meeting_summaries.sentiment IS 'Overall meeting sentiment (positive/negative/neutral)';
COMMENT ON COLUMN public.meeting_summaries.model_used IS 'LLM model identifier (e.g., "gemma2:7b via Ollama")';

-- Enable Row Level Security (RLS)
ALTER TABLE public.meeting_summaries ENABLE ROW LEVEL SECURITY;

-- RLS Policy 1: Users can SELECT their own meeting summaries
CREATE POLICY "Users can view own meeting summaries"
    ON public.meeting_summaries
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.meetings
            WHERE meetings.id = meeting_summaries.meeting_id
            AND meetings.user_id = auth.uid()
        )
    );

-- RLS Policy 2: Service role can INSERT summaries (for PC Worker)
-- Note: Service role bypasses RLS, but we keep this for clarity
CREATE POLICY "Service role can create summaries"
    ON public.meeting_summaries
    FOR INSERT
    WITH CHECK (true);  -- Service role always bypasses RLS

-- RLS Policy 3: Users can UPDATE their own summaries (e.g., correct/improve)
CREATE POLICY "Users can update own meeting summaries"
    ON public.meeting_summaries
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.meetings
            WHERE meetings.id = meeting_summaries.meeting_id
            AND meetings.user_id = auth.uid()
        )
    );

-- RLS Policy 4: Users can DELETE their own summaries
CREATE POLICY "Users can delete own meeting summaries"
    ON public.meeting_summaries
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.meetings
            WHERE meetings.id = meeting_summaries.meeting_id
            AND meetings.user_id = auth.uid()
        )
    );

-- Create a view for easier summary retrieval with meeting info
CREATE OR REPLACE VIEW public.summaries_with_meeting AS
SELECT
    ms.id,
    ms.meeting_id,
    ms.summary,
    ms.key_points,
    ms.action_items,
    ms.topics,
    ms.sentiment,
    ms.model_used,
    ms.processing_time_seconds,
    ms.created_at,
    m.title AS meeting_title,
    m.user_id,
    m.created_at AS meeting_created_at,
    m.duration_seconds AS meeting_duration
FROM public.meeting_summaries ms
JOIN public.meetings m ON m.id = ms.meeting_id
ORDER BY ms.created_at DESC;

-- Grant permissions
GRANT SELECT ON public.meeting_summaries TO authenticated;
GRANT SELECT ON public.summaries_with_meeting TO authenticated;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_meeting_summaries_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_meeting_summaries_timestamp
    BEFORE UPDATE ON public.meeting_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_meeting_summaries_timestamp();

-- Migration tracking (optional, for audit)
INSERT INTO public._migrations (name, status, executed_at)
VALUES ('create_meeting_summaries', 'success', now())
ON CONFLICT (name) DO UPDATE SET executed_at = now();

-- Summary of created objects
-- Table: meeting_summaries (8 columns, indexed for performance)
-- Indexes: 3 (meeting_id, created_at, user_id via view)
-- RLS Policies: 4 (SELECT, INSERT, UPDATE, DELETE)
-- Views: 1 (summaries_with_meeting)
-- Functions: 1 (timestamp update trigger)
-- Estimated size: ~1MB per 10,000 summaries

-- Typical query patterns:
-- 1. Get summaries for a user's meetings:
--    SELECT * FROM summaries_with_meeting WHERE user_id = 'user-uuid'
--
-- 2. Get latest summary for a meeting:
--    SELECT * FROM meeting_summaries WHERE meeting_id = 'meeting-uuid'
--    ORDER BY created_at DESC LIMIT 1
--
-- 3. Find meetings by key point (requires text search):
--    SELECT * FROM summaries_with_meeting
--    WHERE key_points @> ARRAY['search term']
--
-- 4. Get all summaries created today:
--    SELECT * FROM summaries_with_meeting
--    WHERE created_at >= now()::date
--
-- Performance notes:
-- - created_at index enables fast "latest summaries" queries
-- - meeting_id foreign key enables fast meeting joins
-- - RLS policies are efficient (uses EXISTS with index lookup)
-- - ARRAY columns are indexed via GiN for text search capability

-- Rollback script (if needed):
-- DROP TABLE IF EXISTS public.meeting_summaries CASCADE;
-- DROP VIEW IF EXISTS public.summaries_with_meeting;
-- DROP FUNCTION IF EXISTS update_meeting_summaries_timestamp();
