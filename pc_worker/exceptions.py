"""
Custom Exception Classes for PC Worker
Provides structured error handling across the application
"""


class PCWorkerException(Exception):
    """Base exception for all PC Worker errors"""
    pass


class SupabaseError(PCWorkerException):
    """Base exception for Supabase-related errors"""
    pass


class SupabaseConnectionError(SupabaseError):
    """Raised when unable to connect to Supabase"""
    pass


class SupabaseAuthenticationError(SupabaseError):
    """Raised when Supabase authentication fails"""
    pass


class SupabaseQueryError(SupabaseError):
    """Raised when a Supabase query fails"""
    pass


class SupabaseStorageError(SupabaseError):
    """Raised when Supabase Storage operations fail"""
    pass


class SupabaseRealtimeError(SupabaseError):
    """Raised when Supabase Realtime operations fail"""
    pass


class AudioProcessingError(PCWorkerException):
    """Base exception for audio processing errors"""
    pass


class AudioDownloadError(AudioProcessingError):
    """Raised when audio download fails"""
    pass


class AudioCorruptedError(AudioProcessingError):
    """Raised when audio file is corrupted or invalid"""
    pass


class AudioPreprocessingError(AudioProcessingError):
    """Raised when audio preprocessing fails"""
    pass


class TranscriptionError(PCWorkerException):
    """Raised when transcription fails"""
    pass


class DiarizationError(PCWorkerException):
    """Raised when speaker diarization fails"""
    pass


class SummaryGenerationError(PCWorkerException):
    """Raised when AI summary generation fails"""
    pass


class ValidationError(PCWorkerException):
    """Raised when data validation fails"""
    pass


class ConfigurationError(PCWorkerException):
    """Raised when configuration is invalid"""
    pass


class RetryExhaustedError(PCWorkerException):
    """Raised when all retry attempts have been exhausted"""
    def __init__(self, operation: str, attempts: int, last_error: Exception):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted for {operation} after {attempts} attempts. "
            f"Last error: {last_error}"
        )
