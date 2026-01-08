"""
Embedding Engine for RAG Search
Uses BGE-M3 for multilingual text embeddings (Korean optimized)

BGE-M3 Features:
- 1024-dimensional dense embeddings
- Excellent multilingual support (Korean included)
- Optimized for semantic similarity search
"""

import asyncio
from typing import List, Optional, Union
from dataclasses import dataclass
import numpy as np
from pydantic import BaseModel, Field

from logger import get_logger
from config import get_config

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class EmbeddingConfig(BaseModel):
    """Configuration for embedding engine"""
    model_name: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model name for embeddings"
    )
    embedding_dim: int = Field(
        default=1024,
        description="Embedding vector dimension"
    )
    max_length: int = Field(
        default=512,
        description="Maximum token length for input text"
    )
    batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )
    use_fp16: bool = Field(
        default=True,
        description="Use FP16 for faster inference (GPU only)"
    )
    normalize_embeddings: bool = Field(
        default=True,
        description="L2 normalize embeddings for cosine similarity"
    )
    device: Optional[str] = Field(
        default=None,
        description="Device to use (cuda/cpu). Auto-detect if None"
    )


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    text: str
    embedding: List[float]
    token_count: int

    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array"""
        return np.array(self.embedding, dtype=np.float32)


# =============================================================================
# Embedding Engine
# =============================================================================

class EmbeddingEngine:
    """
    Generates text embeddings using BGE-M3 model.

    Optimized for Korean text with multilingual support.
    Supports both single text and batch processing.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize the embedding engine.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or EmbeddingConfig()
        self._model = None
        self._tokenizer = None
        self._device = None
        self._initialized = False

        logger.info(f"EmbeddingEngine created with model: {self.config.model_name}")

    async def initialize(self) -> None:
        """
        Lazily initialize the model.

        Called automatically on first use, but can be called
        explicitly to pre-load the model.
        """
        if self._initialized:
            return

        logger.info(f"Initializing embedding model: {self.config.model_name}")

        # Run initialization in thread pool (model loading is CPU-bound)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

        self._initialized = True
        logger.info(f"Embedding model initialized on device: {self._device}")

    def _load_model(self) -> None:
        """Load the embedding model (sync, runs in thread pool)"""
        import torch

        # Determine device
        if self.config.device:
            self._device = self.config.device
        else:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading model on device: {self._device}")

        try:
            # Try FlagEmbedding first (official BGE-M3 implementation)
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.config.model_name,
                use_fp16=self.config.use_fp16 and self._device == "cuda",
                device=self._device
            )
            self._model_type = "flag"
            logger.info("Loaded BGE-M3 using FlagEmbedding")

        except ImportError:
            # Fallback to sentence-transformers
            logger.warning("FlagEmbedding not available, using sentence-transformers")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.config.model_name,
                device=self._device
            )
            self._model_type = "sentence_transformers"
            logger.info("Loaded model using sentence-transformers")

    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            EmbeddingResult with embedding vector
        """
        await self.initialize()

        results = await self.embed_texts([text])
        return results[0]

    async def embed_texts(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            show_progress: Whether to show progress bar

        Returns:
            List of EmbeddingResult objects
        """
        await self.initialize()

        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")

        # Run embedding in thread pool (GPU-bound operation)
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._embed_batch(texts, show_progress)
        )

        # Create results
        results = []
        for text, embedding in zip(texts, embeddings):
            results.append(EmbeddingResult(
                text=text,
                embedding=embedding.tolist(),
                token_count=len(text.split())  # Rough estimate
            ))

        logger.info(f"Generated {len(results)} embeddings")
        return results

    def _embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings in batches (sync, runs in thread pool).

        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress

        Returns:
            Numpy array of embeddings (N x embedding_dim)
        """
        if self._model_type == "flag":
            # FlagEmbedding API
            output = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                max_length=self.config.max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )

            # BGE-M3 returns dict with 'dense_vecs'
            if isinstance(output, dict):
                embeddings = output['dense_vecs']
            else:
                embeddings = output

        else:
            # sentence-transformers API
            embeddings = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.config.normalize_embeddings
            )

        # Ensure numpy array
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # Normalize if needed (FlagEmbedding already normalizes)
        if self.config.normalize_embeddings and self._model_type != "flag":
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-10)

        return embeddings.astype(np.float32)

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Convenience method that returns just the embedding vector.

        Args:
            query: Search query text

        Returns:
            List of floats (embedding vector)
        """
        result = await self.embed_text(query)
        return result.embedding

    def embed_query_sync(self, query: str) -> List[float]:
        """
        Synchronous version of embed_query.

        Useful for contexts where async is not available.

        Args:
            query: Search query text

        Returns:
            List of floats (embedding vector)
        """
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new event loop for this thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.embed_query(query))
                return future.result()
        else:
            return asyncio.run(self.embed_query(query))

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension"""
        return self.config.embedding_dim

    @property
    def is_initialized(self) -> bool:
        """Check if model is initialized"""
        return self._initialized

    async def close(self) -> None:
        """Clean up resources"""
        if self._model is not None:
            # Release GPU memory
            self._model = None
            self._initialized = False

            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("Embedding engine closed")


# =============================================================================
# Singleton Instance
# =============================================================================

_engine_instance: Optional[EmbeddingEngine] = None


def get_embedding_engine(config: Optional[EmbeddingConfig] = None) -> EmbeddingEngine:
    """
    Get or create the singleton embedding engine instance.

    Args:
        config: Optional configuration for first initialization

    Returns:
        EmbeddingEngine instance
    """
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = EmbeddingEngine(config)

    return _engine_instance


async def embed_texts_batch(
    texts: List[str],
    config: Optional[EmbeddingConfig] = None
) -> List[List[float]]:
    """
    Convenience function to embed multiple texts.

    Args:
        texts: List of texts to embed
        config: Optional configuration

    Returns:
        List of embedding vectors
    """
    engine = get_embedding_engine(config)
    results = await engine.embed_texts(texts)
    return [r.embedding for r in results]


async def embed_query(
    query: str,
    config: Optional[EmbeddingConfig] = None
) -> List[float]:
    """
    Convenience function to embed a search query.

    Args:
        query: Search query text
        config: Optional configuration

    Returns:
        Embedding vector
    """
    engine = get_embedding_engine(config)
    return await engine.embed_query(query)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    async def main():
        """Test embedding engine"""
        print("=== Embedding Engine Test ===\n")

        # Create engine
        engine = EmbeddingEngine()

        # Test texts (Korean and English)
        test_texts = [
            "안녕하세요. 오늘 회의에서 프로젝트 진행 상황을 논의하겠습니다.",
            "Hello. Today we will discuss the project progress.",
            "다음 주까지 개발 완료 예정입니다.",
            "The development is expected to be completed by next week.",
        ]

        # Generate embeddings
        print("Generating embeddings...")
        results = await engine.embed_texts(test_texts)

        print(f"\nGenerated {len(results)} embeddings:")
        for i, result in enumerate(results):
            print(f"\n{i+1}. Text: {result.text[:50]}...")
            print(f"   Embedding dim: {len(result.embedding)}")
            print(f"   First 5 values: {result.embedding[:5]}")

        # Test similarity
        print("\n=== Similarity Test ===")
        import numpy as np

        embeddings = np.array([r.embedding for r in results])

        # Calculate cosine similarities
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                similarity = np.dot(embeddings[i], embeddings[j])
                print(f"Similarity({i+1}, {j+1}): {similarity:.4f}")

        # Clean up
        await engine.close()
        print("\n=== Test Complete ===")

    asyncio.run(main())
