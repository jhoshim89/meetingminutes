-- Migration: Create appointments table with RLS policies
-- Description: Adds meeting appointment/scheduling functionality with reminders
-- Date: 2026-01-09

-- Create appointments table
CREATE TABLE IF NOT EXISTS public.appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reminder_minutes INTEGER DEFAULT 5,
    duration_minutes INTEGER DEFAULT 60,
    template_id UUID REFERENCES public.templates(id) ON DELETE SET NULL,
    tags TEXT[] DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    meeting_id UUID REFERENCES public.meetings(id) ON DELETE SET NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    auto_record BOOLEAN DEFAULT TRUE,
    fcm_token TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT appointment_title_not_empty CHECK (title != ''),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'recording', 'completed', 'cancelled', 'missed')),
    CONSTRAINT valid_reminder_minutes CHECK (reminder_minutes >= 0 AND reminder_minutes <= 1440),
    CONSTRAINT valid_duration_minutes CHECK (duration_minutes > 0 AND duration_minutes <= 1440),
    CONSTRAINT scheduled_at_in_future CHECK (scheduled_at > created_at)
);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_appointments_user_id ON public.appointments(user_id);

-- Create index for scheduled_at (for upcoming appointments queries)
CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_at ON public.appointments(user_id, scheduled_at ASC);

-- Create index for status filtering
CREATE INDEX IF NOT EXISTS idx_appointments_status ON public.appointments(user_id, status);

-- Create composite index for pending appointments that need notifications
CREATE INDEX IF NOT EXISTS idx_appointments_pending_notifications
    ON public.appointments(user_id, scheduled_at, notification_sent)
    WHERE status = 'pending' AND notification_sent = FALSE;

-- Create index for template_id lookups
CREATE INDEX IF NOT EXISTS idx_appointments_template_id ON public.appointments(template_id);

-- Create index for meeting_id lookups
CREATE INDEX IF NOT EXISTS idx_appointments_meeting_id ON public.appointments(meeting_id);

-- Create index for tag-based searches (GIN index for array operations)
CREATE INDEX IF NOT EXISTS idx_appointments_tags ON public.appointments USING GIN(tags);

-- Enable RLS
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can select their own appointments
CREATE POLICY IF NOT EXISTS "Users can select their own appointments"
    ON public.appointments
    FOR SELECT
    USING (auth.uid() = user_id);

-- RLS Policy: Users can insert appointments for themselves
CREATE POLICY IF NOT EXISTS "Users can insert their own appointments"
    ON public.appointments
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own appointments
CREATE POLICY IF NOT EXISTS "Users can update their own appointments"
    ON public.appointments
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can delete their own appointments
CREATE POLICY IF NOT EXISTS "Users can delete their own appointments"
    ON public.appointments
    FOR DELETE
    USING (auth.uid() = user_id);

-- Grant service_role access (for PC Worker and automated processes)
-- Service role bypasses RLS, so these grants allow the worker to perform admin operations
GRANT ALL ON public.appointments TO service_role;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION public.update_appointments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_appointments_updated_at
BEFORE UPDATE ON public.appointments
FOR EACH ROW
EXECUTE FUNCTION public.update_appointments_updated_at();

-- Create function to automatically mark missed appointments
CREATE OR REPLACE FUNCTION public.mark_missed_appointments()
RETURNS void AS $$
BEGIN
    UPDATE public.appointments
    SET status = 'missed', updated_at = NOW()
    WHERE status = 'pending'
      AND scheduled_at < NOW() - (duration_minutes || ' minutes')::INTERVAL
      AND meeting_id IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Create function to get upcoming appointments (for reminder notifications)
CREATE OR REPLACE FUNCTION public.get_upcoming_appointments_for_reminder(minutes_ahead INTEGER DEFAULT 5)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    title VARCHAR(255),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    reminder_minutes INTEGER,
    fcm_token TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.user_id,
        a.title,
        a.scheduled_at,
        a.reminder_minutes,
        a.fcm_token
    FROM public.appointments a
    WHERE a.status = 'pending'
      AND a.notification_sent = FALSE
      AND a.fcm_token IS NOT NULL
      AND a.scheduled_at <= NOW() + (a.reminder_minutes || ' minutes')::INTERVAL
      AND a.scheduled_at > NOW();
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE public.appointments IS 'Meeting appointments/schedules with reminder notifications and auto-recording';
COMMENT ON COLUMN public.appointments.scheduled_at IS 'Scheduled date and time for the meeting';
COMMENT ON COLUMN public.appointments.reminder_minutes IS 'Minutes before scheduled_at to send reminder notification (0-1440)';
COMMENT ON COLUMN public.appointments.duration_minutes IS 'Expected duration of the meeting in minutes (1-1440)';
COMMENT ON COLUMN public.appointments.status IS 'Appointment status: pending, recording, completed, cancelled, missed';
COMMENT ON COLUMN public.appointments.meeting_id IS 'Reference to the created meeting if appointment was recorded';
COMMENT ON COLUMN public.appointments.notification_sent IS 'Flag indicating if reminder notification was sent';
COMMENT ON COLUMN public.appointments.auto_record IS 'Whether to automatically start recording at scheduled time';
COMMENT ON COLUMN public.appointments.fcm_token IS 'Firebase Cloud Messaging token for push notifications';
COMMENT ON FUNCTION public.mark_missed_appointments() IS 'Marks appointments as missed if scheduled_at + duration has passed and no meeting was created';
COMMENT ON FUNCTION public.get_upcoming_appointments_for_reminder(INTEGER) IS 'Retrieves appointments that need reminder notifications sent';
