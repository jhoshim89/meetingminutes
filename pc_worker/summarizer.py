"""
Summarization Module for PC Worker
Generates meeting summaries using Ollama + Gemma 2 with LangChain
Supports both sync and async operations with proper error handling
"""

import asyncio
import re
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import time

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    SUMMARIZATION_TIMEOUT,
    SUMMARIZATION_MAX_RETRIES,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SUMMARY_LENGTH_MIN,
    SUMMARY_LENGTH_MAX,
    logger
)
from models import TranscriptSegment, MeetingSummary
from exceptions import SummaryGenerationError

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.llms import Ollama
    from langchain.callbacks import StreamingStdOutCallbackHandler
except ImportError:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.llms import Ollama
        from langchain.callbacks import StreamingStdOutCallbackHandler
    except ImportError:
        # Fallback if LangChain modules not available
        logger.warning("LangChain modules not fully available, will use basic implementation")
        RecursiveCharacterTextSplitter = None
        Ollama = None
        StreamingStdOutCallbackHandler = None


class OllamaSummarizer:
    """
    Meeting summarizer using Ollama + Gemma 2 backend
    Chunks transcript intelligently and generates comprehensive summaries
    """

    # Korean-optimized summarization prompt
    KOREAN_SYSTEM_PROMPT = """당신은 회의 기록을 분석하는 전문 회의 요약 전문가입니다.

당신의 역할:
1. 회의의 핵심 내용을 명확하고 간결하게 요약하기
2. 중요한 결정사항과 액션 아이템 식별
3. 논의된 주요 주제와 결론 정리
4. 한국어로 자연스럽고 전문적인 표현 사용

요약 규칙:
- 길이: 최소 100자, 최대 1000자
- 시제: 과거형 사용
- 구조: 주제 → 논의 내용 → 결론/결정사항
- 명확성: 약자는 처음 사용 시 풀어서 표기
- 정확성: 정확하지 않은 정보는 포함하지 않기"""

    KOREAN_USER_PROMPT = """다음 회의 기록을 분석하고 요약해주세요:

{transcript}

요약은 다음 형식으로 작성해주세요:
[요약]
{요약 내용}

[핵심 포인트]
- 포인트1
- 포인트2
- ...

[액션 아이템]
- 담당자: 작업 내용
- 담당자: 작업 내용
- ..."""

    def __init__(
        self,
        ollama_url: str = OLLAMA_BASE_URL,
        model_name: str = OLLAMA_MODEL,
        timeout: int = SUMMARIZATION_TIMEOUT,
        max_retries: int = SUMMARIZATION_MAX_RETRIES
    ):
        """
        Initialize the summarizer

        Args:
            ollama_url: Base URL for Ollama server
            model_name: Name of the Ollama model to use
            timeout: Timeout in seconds for summarization
            max_retries: Maximum retry attempts
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._ollama_client = None
        self._text_splitter = None

        logger.info(f"OllamaSummarizer initialized with model: {model_name}")
        logger.info(f"Ollama URL: {ollama_url}")

    @property
    def ollama_client(self):
        """Lazy initialization of Ollama client"""
        if self._ollama_client is None:
            if Ollama is None:
                raise SummaryGenerationError(
                    "LangChain Ollama not available. Install langchain[ollama]"
                )
            try:
                self._ollama_client = Ollama(
                    base_url=self.ollama_url,
                    model=self.model_name,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40
                )
                logger.debug("Ollama client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                raise SummaryGenerationError(f"Cannot initialize Ollama: {e}")
        return self._ollama_client

    @property
    def text_splitter(self):
        """Lazy initialization of text splitter"""
        if self._text_splitter is None:
            if RecursiveCharacterTextSplitter is None:
                raise SummaryGenerationError(
                    "LangChain text splitter not available. Install langchain-text-splitters"
                )
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", "。", "！", "？", " ", ""],
                length_function=len
            )
        return self._text_splitter

    async def health_check(self) -> bool:
        """
        Check if Ollama server is available and model is loaded

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            # Try to ping Ollama API
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        model_names = [m.get("name", "") for m in models]

                        if any(self.model_name in name for name in model_names):
                            logger.debug(f"Ollama health check passed. Model {self.model_name} available")
                            return True
                        else:
                            logger.warning(
                                f"Model {self.model_name} not found. Available models: {model_names}"
                            )
                            return False
                    else:
                        logger.warning(f"Ollama health check failed with status {response.status}")
                        return False
        except asyncio.TimeoutError:
            logger.error("Ollama health check timeout")
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def _format_transcript(self, segments: List[TranscriptSegment]) -> str:
        """
        Format transcript segments into readable text

        Args:
            segments: List of transcript segments

        Returns:
            Formatted transcript string
        """
        if not segments:
            return ""

        lines = []
        for segment in segments:
            speaker = segment.speaker_label or f"Speaker {segment.speaker_id}"
            time_str = f"[{self._format_time(segment.start_time)}]"
            lines.append(f"{speaker} {time_str}: {segment.text}")

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _chunk_transcript(self, transcript: str) -> List[str]:
        """
        Split transcript into overlapping chunks

        Args:
            transcript: Full transcript text

        Returns:
            List of text chunks
        """
        try:
            if self.text_splitter is not None:
                chunks = self.text_splitter.split_text(transcript)
                logger.debug(f"Split transcript into {len(chunks)} chunks")
                return chunks
            else:
                # Fallback: simple character-based splitting
                logger.warning("Text splitter not available, using simple chunking")
                chunks = []
                start = 0
                while start < len(transcript):
                    end = start + CHUNK_SIZE
                    chunks.append(transcript[start:end])
                    start = end - CHUNK_OVERLAP
                return chunks
        except Exception as e:
            logger.error(f"Error chunking transcript: {e}")
            raise SummaryGenerationError(f"Cannot chunk transcript: {e}")

    async def _call_ollama_sync(self, prompt: str) -> str:
        """
        Call Ollama model synchronously (in thread)

        Args:
            prompt: Input prompt

        Returns:
            Model response
        """
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    lambda: self.ollama_client(prompt)
                ),
                timeout=self.timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Ollama call timeout after {self.timeout} seconds")
            raise SummaryGenerationError(f"Ollama timeout (>{self.timeout}s)")
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            raise SummaryGenerationError(f"Ollama call failed: {e}")

    async def _summarize_chunk(self, chunk: str, is_first: bool = False) -> str:
        """
        Summarize a single chunk of transcript

        Args:
            chunk: Transcript chunk text
            is_first: Whether this is the first chunk

        Returns:
            Summary of the chunk
        """
        if is_first:
            prompt = self.KOREAN_USER_PROMPT.format(transcript=chunk)
        else:
            prompt = f"""다음 회의 기록의 연속 부분을 요약하세요:

{chunk}

간단한 요약만 제공하세요 (100-300자):"""

        try:
            summary = await self._call_ollama_sync(prompt)
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to summarize chunk: {e}")
            raise

    async def _map_reduce_summarize(self, chunks: List[str]) -> str:
        """
        Perform map-reduce summarization on transcript chunks

        Args:
            chunks: List of transcript chunks

        Returns:
            Final summary
        """
        if not chunks:
            raise SummaryGenerationError("No chunks provided for summarization")

        logger.info(f"Starting map-reduce summarization on {len(chunks)} chunks")

        try:
            # Map phase: summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                logger.debug(f"Summarizing chunk {i+1}/{len(chunks)}")
                try:
                    summary = await self._summarize_chunk(chunk, is_first=(i == 0))
                    if summary:
                        chunk_summaries.append(summary)
                except Exception as e:
                    logger.warning(f"Failed to summarize chunk {i+1}: {e}")
                    # Continue with other chunks even if one fails
                    continue

            if not chunk_summaries:
                raise SummaryGenerationError("Failed to summarize any chunks")

            # Reduce phase: summarize all summaries
            combined_summaries = "\n\n".join(chunk_summaries)
            logger.debug(f"Combined {len(chunk_summaries)} chunk summaries")

            reduce_prompt = f"""다음은 회의의 여러 부분의 요약입니다. 이들을 하나의 통합 요약으로 작성하세요:

{combined_summaries}

최종 요약 (300-500자):"""

            final_summary = await self._call_ollama_sync(reduce_prompt)
            return final_summary.strip()

        except Exception as e:
            logger.error(f"Map-reduce summarization failed: {e}")
            raise

    async def _extract_key_points(self, transcript: str, summary: str) -> List[str]:
        """
        Extract key points from transcript using summary as context

        Args:
            transcript: Full transcript
            summary: Generated summary

        Returns:
            List of key points
        """
        try:
            prompt = f"""회의 요약과 기록을 기반으로 3-5개의 핵심 포인트를 추출하세요:

요약: {summary}

회의 기록: {transcript[:2000]}...

형식: 각 포인트를 별도 라인으로 작성하고 '-'로 시작
예:
- 핵심 포인트 1
- 핵심 포인트 2"""

            response = await self._call_ollama_sync(prompt)

            # Parse response into list
            points = [
                line.strip().lstrip("- •*").strip()
                for line in response.split("\n")
                if line.strip() and line.strip()[0] in "-•*"
            ]

            return points[:5]  # Return maximum 5 points

        except Exception as e:
            logger.warning(f"Failed to extract key points: {e}")
            return []

    async def _extract_action_items(self, transcript: str, summary: str) -> List[str]:
        """
        Extract action items from transcript

        Args:
            transcript: Full transcript
            summary: Generated summary

        Returns:
            List of action items
        """
        try:
            prompt = f"""회의 기록에서 액션 아이템을 추출하세요. 형식: [담당자]: [작업]

회의 요약: {summary}

관련 부분:
{transcript[:2000]}...

액션 아이템 (최대 5개):"""

            response = await self._call_ollama_sync(prompt)

            # Parse response into list
            items = [
                line.strip().lstrip("- •*").strip()
                for line in response.split("\n")
                if line.strip() and line.strip()[0] in "-•*"
            ]

            return items[:5]  # Return maximum 5 items

        except Exception as e:
            logger.warning(f"Failed to extract action items: {e}")
            return []

    def _validate_summary_length(self, summary: str) -> bool:
        """
        Validate that summary meets length requirements

        Args:
            summary: Generated summary text

        Returns:
            True if valid, False otherwise
        """
        length = len(summary)
        if length < SUMMARY_LENGTH_MIN:
            logger.warning(f"Summary too short: {length} < {SUMMARY_LENGTH_MIN} chars")
            return False
        if length > SUMMARY_LENGTH_MAX:
            logger.warning(f"Summary too long: {length} > {SUMMARY_LENGTH_MAX} chars")
            # Truncate if too long
            return True  # Still valid, just warn

        return True

    async def summarize(
        self,
        segments: List[TranscriptSegment],
        meeting_id: str = "",
        extract_details: bool = True
    ) -> MeetingSummary:
        """
        Generate summary from transcript segments

        Args:
            segments: List of transcript segments
            meeting_id: Meeting ID for tracking
            extract_details: Whether to extract key points and action items

        Returns:
            MeetingSummary object

        Raises:
            SummaryGenerationError: If summarization fails
        """
        start_time = time.time()
        logger.log_meeting_event(meeting_id, "summarization_started")

        try:
            # Check Ollama availability
            if not await self.health_check():
                raise SummaryGenerationError(
                    f"Ollama server not available at {self.ollama_url}"
                )

            # Format and validate transcript
            transcript = self._format_transcript(segments)
            if not transcript or len(transcript.strip()) == 0:
                raise SummaryGenerationError("Empty transcript provided")

            logger.debug(f"Formatted transcript: {len(transcript)} characters")

            # Chunk transcript
            chunks = self._chunk_transcript(transcript)
            logger.info(f"Chunked transcript into {len(chunks)} segments")

            # Generate summary
            summary_text = await self._map_reduce_summarize(chunks)

            # Validate length
            if not self._validate_summary_length(summary_text):
                logger.warning("Summary length validation failed")

            # Extract details if requested
            key_points = []
            action_items = []

            if extract_details:
                logger.debug("Extracting key points and action items")
                key_points = await self._extract_key_points(transcript, summary_text)
                action_items = await self._extract_action_items(transcript, summary_text)

            # Create summary object
            processing_time = time.time() - start_time
            summary = MeetingSummary(
                meeting_id=meeting_id,
                summary=summary_text,
                key_points=key_points,
                action_items=action_items,
                topics=[],  # Could be extracted from key_points
                sentiment=None,  # Could be analyzed separately
                model_used=f"{self.model_name} via Ollama"
            )

            logger.log_meeting_event(
                meeting_id,
                "summarization_completed",
                duration_s=f"{processing_time:.2f}",
                summary_length=len(summary_text),
                key_points_count=len(key_points),
                action_items_count=len(action_items)
            )

            return summary

        except SummaryGenerationError:
            raise
        except Exception as e:
            logger.log_meeting_event(
                meeting_id,
                "summarization_failed",
                error=str(e)
            )
            raise SummaryGenerationError(f"Summarization failed: {e}")

    async def summarize_with_retry(
        self,
        segments: List[TranscriptSegment],
        meeting_id: str = "",
        extract_details: bool = True
    ) -> Optional[MeetingSummary]:
        """
        Summarize with automatic retries on failure

        Args:
            segments: List of transcript segments
            meeting_id: Meeting ID for tracking
            extract_details: Whether to extract details

        Returns:
            MeetingSummary or None if all retries fail
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Summarization attempt {attempt}/{self.max_retries}")
                summary = await self.summarize(
                    segments=segments,
                    meeting_id=meeting_id,
                    extract_details=extract_details
                )
                return summary

            except SummaryGenerationError as e:
                logger.warning(f"Summarization attempt {attempt} failed: {e}")

                if attempt == self.max_retries:
                    logger.error(f"All summarization retries exhausted for {meeting_id}")
                    return None

                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

        return None


# Factory function
def get_summarizer(
    ollama_url: str = OLLAMA_BASE_URL,
    model_name: str = OLLAMA_MODEL,
    timeout: int = SUMMARIZATION_TIMEOUT,
    max_retries: int = SUMMARIZATION_MAX_RETRIES
) -> OllamaSummarizer:
    """
    Create summarizer instance

    Args:
        ollama_url: Ollama server URL
        model_name: Model name
        timeout: Summarization timeout
        max_retries: Maximum retry attempts

    Returns:
        OllamaSummarizer instance
    """
    return OllamaSummarizer(
        ollama_url=ollama_url,
        model_name=model_name,
        timeout=timeout,
        max_retries=max_retries
    )
