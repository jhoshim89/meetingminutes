"""
Test Suite for OllamaSummarizer
Comprehensive tests for summarization pipeline with Ollama + Gemma 2
"""

import asyncio
import pytest
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from summarizer import OllamaSummarizer, get_summarizer
from models import TranscriptSegment, MeetingSummary
from exceptions import SummaryGenerationError


class TestOllamaSummarizer:
    """Test cases for OllamaSummarizer class"""

    @pytest.fixture
    def summarizer(self):
        """Create a summarizer instance for testing"""
        return OllamaSummarizer(
            ollama_url="http://localhost:11434",
            model_name="gemma2:7b",
            timeout=300,
            max_retries=3
        )

    @pytest.fixture
    def sample_transcript_segments(self) -> List[TranscriptSegment]:
        """Create sample transcript segments for testing"""
        return [
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=0.0,
                end_time=10.5,
                speaker_label="Speaker 1",
                text="좋은 아침입니다. 오늘 회의는 분기별 성과 검토와 다음 분기 목표 설정입니다.",
                confidence=0.95
            ),
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=10.5,
                end_time=35.2,
                speaker_label="Speaker 2",
                text="지난 분기 실적을 보면 매출이 15% 증가했고 신규 고객 확보는 25% 증가했습니다.",
                confidence=0.93
            ),
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=35.2,
                end_time=62.8,
                speaker_label="Speaker 1",
                text="좋은 성과네요. 하지만 고객 만족도가 2% 하락했다는 점이 걱정됩니다. 이에 대해 어떤 조치를 취하실 계획이신가요?",
                confidence=0.92
            ),
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=62.8,
                end_time=95.4,
                speaker_label="Speaker 2",
                text="네. 고객 서비스 팀과 함께 피드백을 분석했습니다. 주요 문제는 배송 시간 지연과 반품 절차였습니다. 다음 분기부터 배송 파트너를 변경하고 온라인 반품 시스템을 개선하겠습니다.",
                confidence=0.94
            ),
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=95.4,
                end_time=120.1,
                speaker_label="Speaker 1",
                text="좋습니다. 그럼 구체적인 타임라인과 담당자를 정해주세요.",
                confidence=0.91
            ),
            TranscriptSegment(
                meeting_id="test-meeting-001",
                start_time=120.1,
                end_time=145.7,
                speaker_label="Speaker 2",
                text="배송 파트너 변경은 김주임이 담당하고 2월 15일까지 완료하겠습니다. 반품 시스템 개선은 IT팀의 이과장이 담당하고 2월 28일까지 완료할 예정입니다.",
                confidence=0.92
            ),
        ]

    def test_summarizer_initialization(self, summarizer):
        """Test that summarizer initializes correctly"""
        assert summarizer.ollama_url == "http://localhost:11434"
        assert summarizer.model_name == "gemma2:7b"
        assert summarizer.timeout == 300
        assert summarizer.max_retries == 3
        assert summarizer.executor is not None

    def test_format_time(self, summarizer):
        """Test time formatting"""
        assert summarizer._format_time(0) == "00:00:00"
        assert summarizer._format_time(65) == "00:01:05"
        assert summarizer._format_time(3665) == "01:01:05"
        assert summarizer._format_time(7322.5) == "02:02:02"

    def test_format_transcript(self, summarizer, sample_transcript_segments):
        """Test transcript formatting"""
        transcript = summarizer._format_transcript(sample_transcript_segments)

        assert len(transcript) > 0
        assert "[00:00:00]" in transcript
        assert "Speaker 1" in transcript
        assert "Speaker 2" in transcript
        assert "좋은 아침입니다" in transcript

    def test_format_transcript_empty(self, summarizer):
        """Test formatting empty transcript"""
        result = summarizer._format_transcript([])
        assert result == ""

    def test_chunk_transcript_basic(self, summarizer, sample_transcript_segments):
        """Test basic transcript chunking"""
        transcript = summarizer._format_transcript(sample_transcript_segments)
        chunks = summarizer._chunk_transcript(transcript)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) > 0 for chunk in chunks)

        # Verify chunks don't exceed size limit
        for chunk in chunks:
            assert len(chunk) <= 4000 + 200  # CHUNK_SIZE + CHUNK_OVERLAP buffer

    def test_chunk_transcript_empty(self, summarizer):
        """Test chunking empty transcript"""
        with pytest.raises(SummaryGenerationError):
            summarizer._chunk_transcript("")

    def test_validate_summary_length_valid(self, summarizer):
        """Test validation of summary length"""
        valid_summary = "이번 회의의 주요 내용을 요약하면 다음과 같습니다." * 10
        assert summarizer._validate_summary_length(valid_summary) is True

    def test_validate_summary_length_too_short(self, summarizer):
        """Test validation of too short summary"""
        short_summary = "너무 짧음"
        assert summarizer._validate_summary_length(short_summary) is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, summarizer):
        """Test successful health check"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "models": [{"name": "gemma2:7b"}, {"name": "mistral:latest"}]
            })

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None

            mock_session.return_value = mock_session_instance

            result = await summarizer.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_model_not_found(self, summarizer):
        """Test health check when model is not found"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "models": [{"name": "mistral:latest"}]
            })

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None

            mock_session.return_value = mock_session_instance

            result = await summarizer.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, summarizer):
        """Test health check with connection error"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.side_effect = Exception("Connection error")

            result = await summarizer.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_extract_key_points(self, summarizer, sample_transcript_segments):
        """Test key point extraction"""
        transcript = summarizer._format_transcript(sample_transcript_segments)
        summary = "지난 분기 15% 매출 증가, 신규 고객 25% 증가. 하지만 고객 만족도 2% 하락. 배송 시간 지연과 반품 절차 개선 필요."

        with patch.object(summarizer, "_call_ollama_sync") as mock_ollama:
            mock_response = """- 지난 분기 매출 15% 증가, 신규 고객 25% 증가
- 고객 만족도 2% 하락
- 배송 파트너 변경 및 반품 시스템 개선 필요"""

            mock_ollama.return_value = mock_response

            points = await summarizer._extract_key_points(transcript, summary)

            assert len(points) > 0
            assert isinstance(points, list)
            assert all(isinstance(p, str) for p in points)

    @pytest.mark.asyncio
    async def test_extract_action_items(self, summarizer, sample_transcript_segments):
        """Test action item extraction"""
        transcript = summarizer._format_transcript(sample_transcript_segments)
        summary = "배송 파트너 변경 및 반품 시스템 개선"

        with patch.object(summarizer, "_call_ollama_sync") as mock_ollama:
            mock_response = """- 김주임: 배송 파트너 변경 (2월 15일까지)
- 이과장: 반품 시스템 개선 (2월 28일까지)"""

            mock_ollama.return_value = mock_response

            items = await summarizer._extract_action_items(transcript, summary)

            assert len(items) > 0
            assert isinstance(items, list)
            assert all(isinstance(item, str) for item in items)

    def test_get_summarizer_factory(self):
        """Test factory function"""
        summarizer = get_summarizer(
            ollama_url="http://localhost:11434",
            model_name="gemma2:7b"
        )

        assert isinstance(summarizer, OllamaSummarizer)
        assert summarizer.model_name == "gemma2:7b"


class TestSummarizerIntegration:
    """Integration tests for summarizer with mock Ollama"""

    @pytest.fixture
    def summarizer(self):
        """Create a summarizer instance"""
        return OllamaSummarizer(
            ollama_url="http://localhost:11434",
            model_name="gemma2:7b",
            timeout=60,
            max_retries=2
        )

    @pytest.fixture
    def sample_segments(self) -> List[TranscriptSegment]:
        """Sample transcript for testing"""
        return [
            TranscriptSegment(
                meeting_id="test-001",
                start_time=0.0,
                end_time=30.0,
                speaker_label="Manager",
                text="Q3 성과 검토를 시작하겠습니다. 지난분기 목표 달성률은 85%였습니다.",
                confidence=0.95
            ),
            TranscriptSegment(
                meeting_id="test-001",
                start_time=30.0,
                end_time=60.0,
                speaker_label="Team Lead",
                text="마케팅팀이 신규 캠페인으로 브랜드 인지도를 30% 높였습니다.",
                confidence=0.93
            ),
            TranscriptSegment(
                meeting_id="test-001",
                start_time=60.0,
                end_time=90.0,
                speaker_label="Manager",
                text="그러면 Q4에는 판매 확대에 집중해야겠습니다. 구체적인 계획을 세워주세요.",
                confidence=0.92
            ),
        ]

    @pytest.mark.asyncio
    async def test_summarize_with_retry_failure(self, summarizer, sample_segments):
        """Test summarization with retry logic when Ollama fails"""
        with patch.object(summarizer, "health_check", return_value=False):
            result = await summarizer.summarize_with_retry(
                segments=sample_segments,
                meeting_id="test-001"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_summarize_empty_segments(self, summarizer):
        """Test summarization with empty segments"""
        with pytest.raises(SummaryGenerationError):
            await summarizer.summarize(
                segments=[],
                meeting_id="test-001"
            )

    def test_korean_system_prompt_exists(self, summarizer):
        """Test that Korean system prompt is defined"""
        assert len(summarizer.KOREAN_SYSTEM_PROMPT) > 0
        assert "한국어" in summarizer.KOREAN_SYSTEM_PROMPT
        assert "회의" in summarizer.KOREAN_SYSTEM_PROMPT

    def test_korean_user_prompt_exists(self, summarizer):
        """Test that Korean user prompt is defined"""
        assert len(summarizer.KOREAN_USER_PROMPT) > 0
        assert "요약" in summarizer.KOREAN_USER_PROMPT


class TestErrorHandling:
    """Test error handling in summarizer"""

    @pytest.fixture
    def summarizer(self):
        """Create summarizer for error testing"""
        return OllamaSummarizer(
            ollama_url="http://invalid:99999",
            model_name="gemma2:7b",
            timeout=1,
            max_retries=1
        )

    def test_invalid_ollama_url(self, summarizer):
        """Test handling of invalid Ollama URL"""
        assert summarizer.ollama_url == "http://invalid:99999"

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, summarizer):
        """Test health check timeout"""
        result = await summarizer.health_check()
        assert result is False

    def test_summarization_exception_message(self):
        """Test exception message format"""
        error = SummaryGenerationError("Test error")
        assert str(error) == "Test error"


class TestConfigurationValidation:
    """Test configuration and validation"""

    def test_summarizer_config_defaults(self):
        """Test default configuration values"""
        summarizer = OllamaSummarizer()

        assert summarizer.ollama_url == "http://localhost:11434"
        assert summarizer.model_name == "gemma2:7b"
        assert summarizer.timeout == 300
        assert summarizer.max_retries == 3

    def test_summarizer_custom_config(self):
        """Test custom configuration"""
        summarizer = OllamaSummarizer(
            ollama_url="http://192.168.1.100:11434",
            model_name="gemma2:27b",
            timeout=600,
            max_retries=5
        )

        assert summarizer.ollama_url == "http://192.168.1.100:11434"
        assert summarizer.model_name == "gemma2:27b"
        assert summarizer.timeout == 600
        assert summarizer.max_retries == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
