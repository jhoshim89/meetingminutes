"""
Speaker Matcher Module
Handles automatic speaker matching using pyannote embeddings (768 dimensions)
Compares new speakers with registered speakers using cosine similarity
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import numpy as np

from supabase import Client
from postgrest.exceptions import APIError

from config import logger
from models import SpeakerEmbedding
from exceptions import SupabaseQueryError
from utils import retry_with_backoff


class SpeakerMatcher:
    """
    Speaker matcher for automatic speaker identification
    Uses voice embeddings to match speakers across meetings
    """

    def __init__(self, supabase_client: Client):
        """
        Initialize speaker matcher

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client
        logger.info("Speaker Matcher initialized")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def find_similar_speakers(
        self,
        embedding: List[float],
        user_id: str,
        threshold: float = 0.7,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find similar speakers using cosine similarity on voice embeddings

        Args:
            embedding: Voice embedding vector (768 dimensions)
            user_id: User ID to filter speakers
            threshold: Minimum similarity threshold (0.0 to 1.0)
            limit: Maximum number of results

        Returns:
            List of similar speakers with similarity scores

        Raises:
            SupabaseQueryError: If query fails
        """
        logger.log_operation_start(
            "find_similar_speakers",
            user_id=user_id,
            threshold=threshold,
            embedding_dim=len(embedding)
        )

        try:
            # Validate embedding dimensions
            if len(embedding) != 768:
                raise ValueError(f"Expected 768-dimensional embedding, got {len(embedding)}")

            # Convert embedding to proper format for pgvector
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            # Call RPC function for similarity search
            # Uses cosine similarity with pgvector's <=> operator
            response = await asyncio.to_thread(
                lambda: self.client.rpc(
                    "find_similar_speakers",
                    {
                        "query_embedding": embedding_str,
                        "query_user_id": user_id,
                        "similarity_threshold": threshold,
                        "match_limit": limit
                    }
                ).execute()
            )

            similar_speakers = response.data if response.data else []

            logger.log_operation_success(
                "find_similar_speakers",
                user_id=user_id,
                num_matches=len(similar_speakers),
                top_similarity=similar_speakers[0].get("similarity") if similar_speakers else 0.0
            )

            return similar_speakers

        except APIError as e:
            logger.log_operation_failure("find_similar_speakers", e, user_id=user_id)
            raise SupabaseQueryError(f"Failed to find similar speakers: {e}")
        except Exception as e:
            logger.log_operation_failure("find_similar_speakers", e, user_id=user_id)
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def match_speakers(
        self,
        speaker_embeddings: Dict[str, SpeakerEmbedding],
        user_id: str,
        threshold: float = 0.7
    ) -> Dict[str, Optional[str]]:
        """
        Match multiple speakers to existing speaker profiles

        Args:
            speaker_embeddings: Dictionary mapping speaker_label to SpeakerEmbedding
            user_id: User ID to filter speakers
            threshold: Minimum similarity threshold for matching

        Returns:
            Dictionary mapping speaker_label to matched speaker_id (None if no match)

        Raises:
            SupabaseQueryError: If matching fails
        """
        logger.log_operation_start(
            "match_speakers",
            user_id=user_id,
            num_speakers=len(speaker_embeddings),
            threshold=threshold
        )

        try:
            matches = {}

            for speaker_label, embedding_obj in speaker_embeddings.items():
                try:
                    # Find similar speakers for this embedding
                    similar = await self.find_similar_speakers(
                        embedding=embedding_obj.embedding,
                        user_id=user_id,
                        threshold=threshold,
                        limit=1
                    )

                    # Use best match if found
                    if similar and len(similar) > 0:
                        best_match = similar[0]
                        matched_speaker_id = best_match.get("id")
                        similarity_score = best_match.get("similarity")

                        matches[speaker_label] = matched_speaker_id

                        logger.debug(
                            f"Matched speaker '{speaker_label}' to ID {matched_speaker_id} "
                            f"(similarity: {similarity_score:.3f})"
                        )
                    else:
                        matches[speaker_label] = None
                        logger.debug(f"No match found for speaker '{speaker_label}'")

                except Exception as e:
                    logger.warning(f"Failed to match speaker '{speaker_label}': {e}")
                    matches[speaker_label] = None

            num_matched = sum(1 for v in matches.values() if v is not None)
            match_rate = num_matched / len(matches) if matches else 0

            logger.log_operation_success(
                "match_speakers",
                user_id=user_id,
                total_speakers=len(matches),
                matched_speakers=num_matched,
                match_rate=f"{match_rate*100:.1f}%"
            )

            return matches

        except Exception as e:
            logger.log_operation_failure("match_speakers", e, user_id=user_id)
            raise SupabaseQueryError(f"Failed to match speakers: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def save_speaker_embedding(
        self,
        speaker_id: str,
        embedding: List[float],
        confidence: Optional[float] = None,
        model_name: str = "pyannote/embedding"
    ) -> bool:
        """
        Save speaker embedding to database

        Args:
            speaker_id: Speaker ID to update
            embedding: Voice embedding vector (768 dimensions)
            confidence: Optional confidence score
            model_name: Model used to generate embedding

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If save fails
        """
        logger.log_operation_start(
            "save_speaker_embedding",
            speaker_id=speaker_id,
            embedding_dim=len(embedding)
        )

        try:
            # Validate embedding dimensions
            if len(embedding) != 768:
                raise ValueError(f"Expected 768-dimensional embedding, got {len(embedding)}")

            # Convert embedding to proper format for pgvector
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            # Update speaker record
            update_data: Dict[str, Any] = {
                "voice_embedding": embedding_str,
                "embedding_model": model_name,
                "last_embedding_updated": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            if confidence is not None:
                update_data["embedding_confidence"] = confidence

            await asyncio.to_thread(
                lambda: self.client.table("speakers")
                .update(update_data)
                .eq("id", speaker_id)
                .execute()
            )

            logger.log_operation_success(
                "save_speaker_embedding",
                speaker_id=speaker_id,
                model=model_name
            )

            return True

        except APIError as e:
            logger.log_operation_failure("save_speaker_embedding", e, speaker_id=speaker_id)
            raise SupabaseQueryError(f"Failed to save speaker embedding: {e}")
        except Exception as e:
            logger.log_operation_failure("save_speaker_embedding", e, speaker_id=speaker_id)
            raise SupabaseQueryError(f"Unexpected error: {e}")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    async def update_speaker_embedding(
        self,
        speaker_id: str,
        new_embedding: List[float],
        weight: float = 0.3
    ) -> bool:
        """
        Update existing speaker embedding using weighted average

        Args:
            speaker_id: Speaker ID to update
            new_embedding: New voice embedding vector
            weight: Weight for new embedding (0.0 to 1.0), existing gets (1-weight)

        Returns:
            True if successful

        Raises:
            SupabaseQueryError: If update fails
        """
        logger.log_operation_start(
            "update_speaker_embedding",
            speaker_id=speaker_id,
            new_embedding_weight=weight
        )

        try:
            # Validate embedding dimensions
            if len(new_embedding) != 768:
                raise ValueError(f"Expected 768-dimensional embedding, got {len(new_embedding)}")

            # Validate weight
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Weight must be between 0.0 and 1.0, got {weight}")

            # Get existing speaker data
            response = await asyncio.to_thread(
                lambda: self.client.table("speakers")
                .select("voice_embedding, embedding_confidence")
                .eq("id", speaker_id)
                .single()
                .execute()
            )

            if not response.data:
                raise ValueError(f"Speaker {speaker_id} not found")

            existing_embedding = response.data.get("voice_embedding")

            # If no existing embedding, just save the new one
            if not existing_embedding:
                logger.info(f"No existing embedding for speaker {speaker_id}, saving new one")
                return await self.save_speaker_embedding(speaker_id, new_embedding)

            # Calculate weighted average
            # Convert existing embedding (stored as pgvector string or list)
            if isinstance(existing_embedding, str):
                # Parse vector string format: "[0.1,0.2,...]"
                existing_array = np.array([
                    float(x) for x in existing_embedding.strip("[]").split(",")
                ])
            elif isinstance(existing_embedding, list):
                existing_array = np.array(existing_embedding)
            else:
                raise ValueError(f"Unexpected embedding format: {type(existing_embedding)}")

            new_array = np.array(new_embedding)

            # Weighted average: new_emb * weight + old_emb * (1-weight)
            averaged_embedding = (new_array * weight + existing_array * (1 - weight)).tolist()

            # Save averaged embedding
            await self.save_speaker_embedding(
                speaker_id=speaker_id,
                embedding=averaged_embedding,
                confidence=None  # Could update confidence based on variance
            )

            logger.log_operation_success(
                "update_speaker_embedding",
                speaker_id=speaker_id,
                weight=weight
            )

            return True

        except APIError as e:
            logger.log_operation_failure("update_speaker_embedding", e, speaker_id=speaker_id)
            raise SupabaseQueryError(f"Failed to update speaker embedding: {e}")
        except Exception as e:
            logger.log_operation_failure("update_speaker_embedding", e, speaker_id=speaker_id)
            raise SupabaseQueryError(f"Unexpected error: {e}")

    async def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Cosine similarity: dot(A, B) / (norm(A) * norm(B))
            # Convert to distance: 1 - cosine_distance
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure result is in [0, 1] range (handle floating point errors)
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    async def get_speaker_by_id(self, speaker_id: str) -> Optional[Dict]:
        """
        Get speaker information by ID

        Args:
            speaker_id: Speaker ID

        Returns:
            Speaker data dictionary or None if not found

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table("speakers")
                .select("*")
                .eq("id", speaker_id)
                .single()
                .execute()
            )

            return response.data if response.data else None

        except APIError as e:
            logger.error(f"Failed to get speaker {speaker_id}: {e}")
            raise SupabaseQueryError(f"Failed to get speaker: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting speaker {speaker_id}: {e}")
            return None

    async def get_user_speakers(
        self,
        user_id: str,
        has_embedding: bool = True
    ) -> List[Dict]:
        """
        Get all speakers for a user

        Args:
            user_id: User ID
            has_embedding: If True, only return speakers with embeddings

        Returns:
            List of speaker data dictionaries

        Raises:
            SupabaseQueryError: If query fails
        """
        try:
            query = self.client.table("speakers").select("*").eq("user_id", user_id)

            if has_embedding:
                query = query.not_.is_("voice_embedding", "null")

            response = await asyncio.to_thread(
                lambda: query.order("created_at", desc=True).execute()
            )

            return response.data if response.data else []

        except APIError as e:
            logger.error(f"Failed to get speakers for user {user_id}: {e}")
            raise SupabaseQueryError(f"Failed to get speakers: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting speakers for user {user_id}: {e}")
            raise SupabaseQueryError(f"Unexpected error: {e}")


def get_speaker_matcher(supabase_client: Client) -> SpeakerMatcher:
    """
    Factory function to create speaker matcher instance

    Args:
        supabase_client: Supabase client instance

    Returns:
        SpeakerMatcher instance
    """
    return SpeakerMatcher(supabase_client)
