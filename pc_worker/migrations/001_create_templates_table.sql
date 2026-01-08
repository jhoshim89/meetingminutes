-- Migration: Create templates table with RLS policies
-- Description: Adds template management for organizing meetings by context
-- Date: 2026-01-08

-- Create templates table
CREATE TABLE IF NOT EXISTS public.templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT template_name_not_empty CHECK (name != ''),
    CONSTRAINT valid_tags CHECK (tags IS NULL OR array_length(tags, 1) IS NULL OR array_length(tags, 1) > 0)
);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON public.templates(user_id);

-- Create index for created_at ordering
CREATE INDEX IF NOT EXISTS idx_templates_created_at ON public.templates(user_id, created_at DESC);

-- Create index for tag-based searches (if using GIN index for array operations)
CREATE INDEX IF NOT EXISTS idx_templates_tags ON public.templates USING GIN(tags);

-- Enable RLS
ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can select their own templates
CREATE POLICY IF NOT EXISTS "Users can select their own templates"
    ON public.templates
    FOR SELECT
    USING (auth.uid() = user_id);

-- RLS Policy: Users can insert templates for themselves
CREATE POLICY IF NOT EXISTS "Users can insert their own templates"
    ON public.templates
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own templates
CREATE POLICY IF NOT EXISTS "Users can update their own templates"
    ON public.templates
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can delete their own templates
CREATE POLICY IF NOT EXISTS "Users can delete their own templates"
    ON public.templates
    FOR DELETE
    USING (auth.uid() = user_id);

-- Grant service_role access (for PC Worker)
-- Service role bypasses RLS, so these grants allow the worker to perform admin operations
GRANT ALL ON public.templates TO service_role;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION public.update_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_templates_updated_at
BEFORE UPDATE ON public.templates
FOR EACH ROW
EXECUTE FUNCTION public.update_templates_updated_at();

-- Add comment for documentation
COMMENT ON TABLE public.templates IS 'Meeting templates for organizing meetings by context (e.g., team meetings, project reviews)';
COMMENT ON COLUMN public.templates.tags IS 'Array of tags for categorizing and filtering meetings';
