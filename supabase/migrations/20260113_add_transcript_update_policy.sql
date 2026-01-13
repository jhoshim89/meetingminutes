-- Migration: Add UPDATE policy for transcripts table
-- Version: 1.0.1
-- Date: 2026-01-13
-- Description: Allows users to update transcripts (speaker assignment) for their meetings

-- Add UPDATE policy for transcripts table
-- Users can update transcripts that belong to their meetings
CREATE POLICY "Users can update transcripts of their meetings" ON transcripts
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM meetings
        WHERE meetings.id = transcripts.meeting_id
        AND meetings.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM meetings
        WHERE meetings.id = transcripts.meeting_id
        AND meetings.user_id = auth.uid()
    ));
