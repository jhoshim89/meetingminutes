"""
LangChain Re-ranker Module
Re-ranks search results using Ollama + Gemma 2 for improved accuracy

Features:
- Cross-encoder style relevance scoring
- Batch re-ranking for efficiency
- Korean language optimized prompts
"""

import asyncio
from typing import List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import re

from pydantic import BaseModel, Field

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    logger
)
from rag_search import SearchResult
from exceptions import SummaryGenerationError

try:
    from langchain_community.llms import Ollama
except ImportError:
    try:
        from langchain.llms import Ollama
    except ImportError:
        logger.warning("LangChain Ollama not available")
        Ollama = None


# =============================================================================
# Configuration
# =============================================================================

class RerankerConfig(BaseModel):
    """Configuration for re-ranker"""
    ollama_url: str = Field(default=OLLAMA_BASE_URL)
    model_name: str = Field(default=OLLAMA_MODEL)
    timeout: int = Field(default=60, description="Timeout per re-rank call in seconds")
    batch_size: int = Field(default=5, description="Number of results to re-rank at once")
    top_k: int = Field(default=10, description="Number of final results to return")
    min_score: float = Field(default=0.3, description="Minimum relevance score threshold")
    rerank_weight: float = Field(default=0.4, description="Weight for LLM re-rank score")
    original_weight: float = Field(default=0.6, description="Weight for original search score")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class RerankedResult:
    """A re-ranked search result"""
    chunk_id: str
    meeting_id: str
    chunk_index: int
    start_time: float
    end_time: float
    speaker_id: Optional[str]
    text: str
    original_score: float
    rerank_score: float
    final_score: float
    relevance_explanation: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "meeting_id": self.meeting_id,
            "chunk_index": self.chunk_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "relevance_explanation": self.relevance_explanation
        }


# =============================================================================
# Re-ranker
# =============================================================================

class LangChainReranker:
    """
    Re-ranks search results using LLM-based relevance scoring.

    Uses Ollama + Gemma 2 to evaluate query-document relevance
    and produce more accurate search rankings.
    """

    # Korean prompt for relevance scoring
    RELEVANCE_PROMPT = """당신은 검색 결과의 관련성을 평가하는 전문가입니다.

사용자 질문: {query}

검색된 문서:
{document}

이 문서가 사용자 질문에 얼마나 관련이 있는지 평가하세요.

평가 기준:
1. 직접적 관련성: 질문에 직접 답하는 내용이 있는가?
2. 주제 일치: 같은 주제를 다루고 있는가?
3. 정보 유용성: 질문에 도움이 되는 정보가 있는가?

다음 형식으로 응답하세요:
점수: [0.0-1.0 사이의 숫자]
이유: [한 줄 설명]"""

    # Batch relevance prompt
    BATCH_RELEVANCE_PROMPT = """사용자 질문: {query}

다음 문서들의 관련성을 0.0-1.0 점수로 평가하세요:

{documents}

각 문서에 대해 다음 형식으로 응답하세요:
[문서번호]: [점수] - [간단한 이유]

예시:
1: 0.8 - 질문과 직접 관련된 내용 포함
2: 0.3 - 주제는 유사하나 직접적 답변 없음"""

    def __init__(self, config: Optional[RerankerConfig] = None):
        """
        Initialize the re-ranker.

        Args:
            config: Optional configuration
        """
        self.config = config or RerankerConfig()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._ollama_client = None

        logger.info(f"LangChainReranker initialized with model: {self.config.model_name}")

    @property
    def ollama_client(self):
        """Lazy initialization of Ollama client"""
        if self._ollama_client is None:
            if Ollama is None:
                raise SummaryGenerationError(
                    "LangChain Ollama not available. Install langchain-community"
                )
            try:
                self._ollama_client = Ollama(
                    base_url=self.config.ollama_url,
                    model=self.config.model_name,
                    temperature=0.1,  # Low temperature for consistent scoring
                    top_p=0.9
                )
                logger.debug("Ollama client initialized for re-ranking")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                raise SummaryGenerationError(f"Cannot initialize Ollama: {e}")
        return self._ollama_client

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama model asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    lambda: self.ollama_client(prompt)
                ),
                timeout=self.config.timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Ollama call timeout after {self.config.timeout}s")
            raise
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise

    def _parse_score(self, response: str) -> Tuple[float, Optional[str]]:
        """
        Parse relevance score from LLM response.

        Args:
            response: LLM response text

        Returns:
            Tuple of (score, explanation)
        """
        # Try to find score pattern
        score_patterns = [
            r'점수:\s*([\d.]+)',
            r'score:\s*([\d.]+)',
            r'([\d.]+)\s*/\s*1',
            r'^([\d.]+)',
        ]

        score = 0.5  # Default score
        explanation = None

        for pattern in score_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    score = float(match.group(1))
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                    break
                except ValueError:
                    continue

        # Extract explanation
        reason_patterns = [
            r'이유:\s*(.+)',
            r'reason:\s*(.+)',
            r'-\s*(.+)$',
        ]

        for pattern in reason_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                explanation = match.group(1).strip()
                break

        return score, explanation

    def _parse_batch_scores(self, response: str, count: int) -> List[Tuple[float, Optional[str]]]:
        """
        Parse batch relevance scores from LLM response.

        Args:
            response: LLM response text
            count: Expected number of scores

        Returns:
            List of (score, explanation) tuples
        """
        results = []

        # Try to parse each document's score
        for i in range(1, count + 1):
            pattern = rf'{i}:\s*([\d.]+)\s*[-–]?\s*(.+)?'
            match = re.search(pattern, response)

            if match:
                try:
                    score = float(match.group(1))
                    score = max(0.0, min(1.0, score))
                    explanation = match.group(2).strip() if match.group(2) else None
                    results.append((score, explanation))
                except ValueError:
                    results.append((0.5, None))
            else:
                results.append((0.5, None))

        # Pad with default scores if needed
        while len(results) < count:
            results.append((0.5, None))

        return results

    async def rerank_single(
        self,
        query: str,
        result: SearchResult
    ) -> RerankedResult:
        """
        Re-rank a single search result.

        Args:
            query: Search query
            result: Search result to re-rank

        Returns:
            RerankedResult with updated scores
        """
        prompt = self.RELEVANCE_PROMPT.format(
            query=query,
            document=result.text
        )

        try:
            response = await self._call_ollama(prompt)
            rerank_score, explanation = self._parse_score(response)
        except Exception as e:
            logger.warning(f"Re-ranking failed for chunk {result.chunk_id}: {e}")
            rerank_score = result.combined_score
            explanation = None

        # Calculate final score (weighted combination)
        final_score = (
            result.combined_score * self.config.original_weight +
            rerank_score * self.config.rerank_weight
        )

        return RerankedResult(
            chunk_id=result.chunk_id,
            meeting_id=result.meeting_id,
            chunk_index=result.chunk_index,
            start_time=result.start_time,
            end_time=result.end_time,
            speaker_id=result.speaker_id,
            text=result.text,
            original_score=result.combined_score,
            rerank_score=rerank_score,
            final_score=final_score,
            relevance_explanation=explanation
        )

    async def rerank_batch(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[RerankedResult]:
        """
        Re-rank a batch of search results.

        More efficient than re-ranking one by one.

        Args:
            query: Search query
            results: Search results to re-rank

        Returns:
            List of RerankedResult with updated scores
        """
        if not results:
            return []

        # Format documents for batch prompt
        documents = "\n".join([
            f"[문서 {i+1}]\n{result.text}\n"
            for i, result in enumerate(results)
        ])

        prompt = self.BATCH_RELEVANCE_PROMPT.format(
            query=query,
            documents=documents
        )

        try:
            response = await self._call_ollama(prompt)
            scores = self._parse_batch_scores(response, len(results))
        except Exception as e:
            logger.warning(f"Batch re-ranking failed: {e}")
            # Fallback to original scores
            scores = [(r.combined_score, None) for r in results]

        # Create re-ranked results
        reranked = []
        for result, (rerank_score, explanation) in zip(results, scores):
            final_score = (
                result.combined_score * self.config.original_weight +
                rerank_score * self.config.rerank_weight
            )

            reranked.append(RerankedResult(
                chunk_id=result.chunk_id,
                meeting_id=result.meeting_id,
                chunk_index=result.chunk_index,
                start_time=result.start_time,
                end_time=result.end_time,
                speaker_id=result.speaker_id,
                text=result.text,
                original_score=result.combined_score,
                rerank_score=rerank_score,
                final_score=final_score,
                relevance_explanation=explanation
            ))

        return reranked

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None
    ) -> List[RerankedResult]:
        """
        Re-rank search results and return top-k.

        Args:
            query: Search query
            results: Initial search results
            top_k: Number of results to return (default: config.top_k)

        Returns:
            Re-ranked and sorted results
        """
        if not results:
            return []

        top_k = top_k or self.config.top_k
        logger.info(f"Re-ranking {len(results)} results for query: '{query}'")

        # Process in batches
        all_reranked = []
        for i in range(0, len(results), self.config.batch_size):
            batch = results[i:i + self.config.batch_size]
            reranked_batch = await self.rerank_batch(query, batch)
            all_reranked.extend(reranked_batch)
            logger.debug(f"Re-ranked batch {i // self.config.batch_size + 1}")

        # Sort by final score (descending)
        all_reranked.sort(key=lambda x: x.final_score, reverse=True)

        # Filter by minimum score and limit to top_k
        filtered = [
            r for r in all_reranked
            if r.final_score >= self.config.min_score
        ][:top_k]

        logger.info(f"Returning {len(filtered)} re-ranked results")
        return filtered

    async def health_check(self) -> bool:
        """Check if Ollama is available for re-ranking"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Re-ranker health check failed: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

_reranker_instance: Optional[LangChainReranker] = None


def get_reranker(config: Optional[RerankerConfig] = None) -> LangChainReranker:
    """Get or create singleton re-ranker instance"""
    global _reranker_instance

    if _reranker_instance is None:
        _reranker_instance = LangChainReranker(config)

    return _reranker_instance


# =============================================================================
# Convenience Functions
# =============================================================================

async def rerank_search_results(
    query: str,
    results: List[SearchResult],
    top_k: int = 10
) -> List[RerankedResult]:
    """
    Re-rank search results using LLM.

    Args:
        query: Search query
        results: Initial search results
        top_k: Number of results to return

    Returns:
        Re-ranked results
    """
    reranker = get_reranker()
    return await reranker.rerank(query, results, top_k)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    async def main():
        """Test re-ranker"""
        print("=== LangChain Re-ranker Test ===\n")

        # Create mock search results
        mock_results = [
            SearchResult(
                chunk_id="chunk-1",
                meeting_id="meeting-1",
                chunk_index=0,
                start_time=0.0,
                end_time=10.0,
                speaker_id="speaker-1",
                text="프로젝트 일정을 논의했습니다. 다음 주까지 개발 완료 예정입니다.",
                keyword_score=0.8,
                semantic_score=0.7,
                combined_score=0.73
            ),
            SearchResult(
                chunk_id="chunk-2",
                meeting_id="meeting-1",
                chunk_index=1,
                start_time=10.0,
                end_time=20.0,
                speaker_id="speaker-2",
                text="품질 테스트는 개발 완료 후 3일 내에 진행할 예정입니다.",
                keyword_score=0.5,
                semantic_score=0.6,
                combined_score=0.57
            ),
            SearchResult(
                chunk_id="chunk-3",
                meeting_id="meeting-1",
                chunk_index=2,
                start_time=20.0,
                end_time=30.0,
                speaker_id="speaker-1",
                text="예산 관련 문의는 재무팀에 확인하겠습니다.",
                keyword_score=0.2,
                semantic_score=0.3,
                combined_score=0.27
            ),
        ]

        # Test re-ranking
        reranker = LangChainReranker()

        # Check health first
        print("Checking Ollama availability...")
        if not await reranker.health_check():
            print("Ollama not available. Skipping re-rank test.")
            return

        query = "프로젝트 일정이 어떻게 되나요?"
        print(f"\nQuery: {query}")
        print(f"Original results: {len(mock_results)}")

        reranked = await reranker.rerank(query, mock_results, top_k=3)

        print(f"\nRe-ranked results ({len(reranked)}):")
        for i, result in enumerate(reranked):
            print(f"\n{i+1}. Score: {result.final_score:.3f} "
                  f"(orig: {result.original_score:.3f}, "
                  f"rerank: {result.rerank_score:.3f})")
            print(f"   Text: {result.text[:60]}...")
            if result.relevance_explanation:
                print(f"   Reason: {result.relevance_explanation}")

        print("\n=== Test Complete ===")

    asyncio.run(main())
