-- Migration: FCM Web Push and Appointment Scheduler
-- Version: 1.0.0
-- Date: 2026-01-09
-- Description: Creates tables for FCM tokens and meeting appointments

-- ============================================================================
-- 1. USER FCM TOKENS TABLE
-- ============================================================================
-- Stores Firebase Cloud Messaging tokens for Web Push notifications

CREATE TABLE IF NOT EXISTS user_fcm_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    device_type TEXT NOT NULL CHECK (device_type IN ('web', 'ios', 'android')),
    platform TEXT NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure unique tokens per user
    UNIQUE(user_id, token)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_fcm_tokens_user_id ON user_fcm_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_user_fcm_tokens_token ON user_fcm_tokens(token);

-- RLS Policies
ALTER TABLE user_fcm_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only view their own tokens
CREATE POLICY "Users can view own FCM tokens"
    ON user_fcm_tokens FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own tokens
CREATE POLICY "Users can insert own FCM tokens"
    ON user_fcm_tokens FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own tokens
CREATE POLICY "Users can update own FCM tokens"
    ON user_fcm_tokens FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own tokens
CREATE POLICY "Users can delete own FCM tokens"
    ON user_fcm_tokens FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 2. APPOINTMENTS TABLE
-- ============================================================================
-- Stores scheduled meetings/appointments for reminder notifications

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    notification_sent BOOLEAN DEFAULT FALSE,
    reminder_minutes_before INTEGER DEFAULT 15, -- Send reminder X minutes before
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Validation
    CHECK (duration_minutes > 0),
    CHECK (reminder_minutes_before >= 0)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_appointments_user_id ON appointments(user_id);
CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_at ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_appointments_notification_sent ON appointments(notification_sent);

-- Composite index for scheduler query
CREATE INDEX IF NOT EXISTS idx_appointments_scheduler
    ON appointments(scheduled_at, notification_sent)
    WHERE notification_sent = FALSE;

-- RLS Policies
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- Users can view their own appointments
CREATE POLICY "Users can view own appointments"
    ON appointments FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own appointments
CREATE POLICY "Users can insert own appointments"
    ON appointments FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own appointments
CREATE POLICY "Users can update own appointments"
    ON appointments FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own appointments
CREATE POLICY "Users can delete own appointments"
    ON appointments FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 3. HELPER FUNCTIONS
-- ============================================================================

-- Function to get upcoming appointments needing reminders
CREATE OR REPLACE FUNCTION get_upcoming_appointments_for_reminder(
    reminder_window_minutes INTEGER DEFAULT 15
)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    title TEXT,
    scheduled_at TIMESTAMPTZ,
    location TEXT,
    description TEXT,
    notification_sent BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.user_id,
        a.title,
        a.scheduled_at,
        a.location,
        a.description,
        a.notification_sent
    FROM appointments a
    WHERE
        a.notification_sent = FALSE
        AND a.scheduled_at >= NOW()
        AND a.scheduled_at <= NOW() + (reminder_window_minutes || ' minutes')::INTERVAL
    ORDER BY a.scheduled_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to mark notification as sent
CREATE OR REPLACE FUNCTION mark_notification_sent(appointment_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE appointments
    SET notification_sent = TRUE,
        updated_at = NOW()
    WHERE id = appointment_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to reset notifications (for testing)
CREATE OR REPLACE FUNCTION reset_notifications()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE appointments
    SET notification_sent = FALSE,
        updated_at = NOW()
    WHERE notification_sent = TRUE;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 4. TRIGGERS FOR UPDATED_AT
-- ============================================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to user_fcm_tokens
CREATE TRIGGER update_user_fcm_tokens_updated_at
    BEFORE UPDATE ON user_fcm_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to appointments
CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. SAMPLE DATA (for testing)
-- ============================================================================

-- Uncomment to insert test data:
--
-- INSERT INTO appointments (user_id, title, description, location, scheduled_at, duration_minutes, reminder_minutes_before)
-- VALUES
--     (auth.uid(), 'Team Standup', 'Daily team sync meeting', 'Zoom', NOW() + INTERVAL '10 minutes', 30, 15),
--     (auth.uid(), 'Client Presentation', 'Q1 Results presentation', 'Conference Room A', NOW() + INTERVAL '1 hour', 60, 15),
--     (auth.uid(), 'One-on-One', 'Weekly 1:1 with manager', 'Office', NOW() + INTERVAL '2 hours', 45, 15);

-- ============================================================================
-- 6. GRANTS FOR EDGE FUNCTIONS
-- ============================================================================

-- Grant permissions to service role for edge function
-- (Supabase automatically grants these, but explicit for clarity)

GRANT SELECT, UPDATE ON appointments TO service_role;
GRANT SELECT ON user_fcm_tokens TO service_role;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify tables created
DO $$
BEGIN
    RAISE NOTICE 'FCM Schema Migration Complete';
    RAISE NOTICE 'Tables created: user_fcm_tokens, appointments';
    RAISE NOTICE 'Functions created: get_upcoming_appointments_for_reminder, mark_notification_sent, reset_notifications';
    RAISE NOTICE 'RLS enabled on all tables';
END $$;
