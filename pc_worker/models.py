"""
Data Models for PC Worker
Uses Pydantic for validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class MeetingStatus(str, Enum):
    """Meeting processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Meeting(BaseModel):
    """Meeting model representing a meeting to be processed"""
    id: str
    title: str
    status: MeetingStatus = MeetingStatus.PENDING
    audio_url: Optional[str] = None
    audio_storage_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: str
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    processed_by: Optional[str] = None
    template_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing meetings")

    class Config:
        use_enum_values = True

    @validator('created_at', 'updated_at', pre=True)
    def parse_datetime(cls, value):
        """Parse datetime from various formats"""
        if isinstance(value, str):
            # Try to parse ISO format
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.fromisoformat(value)
        return value


class TranscriptSegment(BaseModel):
    """Individual transcript segment with speaker and timestamp"""
    meeting_id: str
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = Field(None, description="Speaker label from diarization")
    text: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None

    @validator('start_time', 'end_time')
    def validate_time(cls, v):
        """Ensure time values are non-negative"""
        if v < 0:
            raise ValueError("Time values must be non-negative")
        return v

    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Ensure end_time is after start_time"""
        if 'start_time' in values and v < values['start_time']:
            raise ValueError("end_time must be greater than start_time")
        return v


class Transcript(BaseModel):
    """Complete transcript for a meeting"""
    meeting_id: str
    segments: List[TranscriptSegment]
    language: Optional[str] = None
    duration: Optional[float] = None
    created_at: Optional[datetime] = None

    @validator('segments')
    def validate_segments_sorted(cls, v):
        """Ensure segments are sorted by start time"""
        if len(v) > 1:
            for i in range(len(v) - 1):
                if v[i].start_time > v[i + 1].start_time:
                    # Sort them automatically
                    return sorted(v, key=lambda s: s.start_time)
        return v


class SpeakerEmbedding(BaseModel):
    """Speaker voice embedding for identification"""
    speaker_id: str
    embedding: List[float]
    sample_count: int = Field(default=1, description="Number of audio samples used")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    @validator('embedding')
    def validate_embedding_dimensions(cls, v):
        """Validate embedding has reasonable dimensions"""
        if len(v) == 0:
            raise ValueError("Embedding cannot be empty")
        if len(v) > 1000:  # Reasonable upper limit
            raise ValueError("Embedding dimensions seem unreasonably large")
        return v


class Speaker(BaseModel):
    """Speaker profile with identification data"""
    id: str
    name: Optional[str] = None
    user_id: Optional[str] = None
    embedding: Optional[SpeakerEmbedding] = None
    audio_samples: List[str] = Field(default_factory=list, description="URLs to audio samples")
    meeting_ids: List[str] = Field(default_factory=list, description="Meetings this speaker appeared in")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MeetingSummary(BaseModel):
    """AI-generated meeting summary"""
    meeting_id: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(
        default_factory=list,
        description="Auto-classified categories (0-3): 현황, 배경, 논의, 문제점, 의견, 결의"
    )
    sentiment: Optional[str] = None
    created_at: Optional[datetime] = None
    model_used: Optional[str] = None

    @validator('summary')
    def validate_summary_not_empty(cls, v):
        """Ensure summary is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Summary cannot be empty")
        return v

    @validator('categories')
    def validate_categories(cls, v):
        """Ensure categories are valid and limited to 0-3 items"""
        valid_categories = {"현황", "배경", "논의", "문제점", "의견", "결의"}

        # Filter valid categories
        validated = [cat for cat in v if cat in valid_categories]

        # Limit to maximum 3 categories
        if len(validated) > 3:
            validated = validated[:3]

        return validated


class ProcessingResult(BaseModel):
    """Result of meeting processing"""
    meeting_id: str
    status: MeetingStatus
    transcript: Optional[Transcript] = None
    speakers: List[Speaker] = Field(default_factory=list)
    summary: Optional[MeetingSummary] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None


class AudioMetadata(BaseModel):
    """Metadata about audio file"""
    file_path: str
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    size_bytes: int

    @validator('sample_rate')
    def validate_sample_rate(cls, v):
        """Ensure sample rate is reasonable"""
        if v < 8000 or v > 192000:
            raise ValueError("Sample rate must be between 8kHz and 192kHz")
        return v

    @validator('channels')
    def validate_channels(cls, v):
        """Ensure channel count is reasonable"""
        if v < 1 or v > 8:
            raise ValueError("Channel count must be between 1 and 8")
        return v


class SystemInfo(BaseModel):
    """System information for monitoring"""
    worker_id: str
    worker_name: str
    cpu_available: bool = True
    gpu_available: bool = False
    gpu_name: Optional[str] = None
    memory_total_gb: Optional[float] = None
    memory_available_gb: Optional[float] = None
    python_version: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Template(BaseModel):
    """Meeting template for organizing meetings by context"""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing meetings")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('name')
    def validate_template_name(cls, v):
        """Ensure template name is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Template name cannot be empty")
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are valid"""
        if not isinstance(v, list):
            raise ValueError("Tags must be a list")
        # Filter out empty strings
        return [tag.strip() for tag in v if tag.strip()]
