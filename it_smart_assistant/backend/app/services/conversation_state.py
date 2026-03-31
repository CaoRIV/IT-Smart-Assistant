"""Redis-based state management for conversation context.

Stores: current_subject, extracted_text, and other ephemeral conversation state.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.clients.redis import RedisClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConversationStateManager:
    """Manages conversation state in Redis.
    
    Keys stored:
    - {conversation_id}:history - Chat history (list of messages)
    - {conversation_id}:subject - Current subject/môn học
    - {conversation_id}:extracted_text - Last OCR result from image
    - {conversation_id}:metadata - Additional conversation metadata
    """

    def __init__(self, redis_client: RedisClient | None = None):
        self.redis = redis_client or RedisClient()
        self.ttl_seconds = 3600 * 24  # 24 hours TTL

    def _history_key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}:history"

    def _subject_key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}:subject"

    def _extracted_text_key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}:extracted_text"

    def _metadata_key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}:metadata"

    async def connect(self) -> None:
        """Connect to Redis if not already connected."""
        await self.redis.connect()

    async def save_history(
        self,
        conversation_id: str,
        history: list[dict[str, Any]],
    ) -> None:
        """Save conversation history to Redis."""
        key = self._history_key(conversation_id)
        await self.redis.set(
            key,
            json.dumps(history, ensure_ascii=False),
            ttl=self.ttl_seconds,
        )
        logger.debug(f"Saved history for conversation {conversation_id}")

    async def get_history(
        self,
        conversation_id: str,
    ) -> list[dict[str, Any]] | None:
        """Get conversation history from Redis."""
        key = self._history_key(conversation_id)
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode history for {conversation_id}")
        return None

    async def save_subject(
        self,
        conversation_id: str,
        subject: str,
    ) -> None:
        """Save current subject (môn học) for conversation."""
        key = self._subject_key(conversation_id)
        await self.redis.set(key, subject, ttl=self.ttl_seconds)
        logger.debug(f"Saved subject '{subject}' for conversation {conversation_id}")

    async def get_subject(self, conversation_id: str) -> str | None:
        """Get current subject for conversation."""
        key = self._subject_key(conversation_id)
        return await self.redis.get(key)

    async def save_extracted_text(
        self,
        conversation_id: str,
        extracted_text: str,
        image_id: str | None = None,
    ) -> None:
        """Save extracted text from image OCR.
        
        Args:
            conversation_id: Conversation ID
            extracted_text: Text extracted from image
            image_id: Optional image/attachment ID for reference
        """
        key = self._extracted_text_key(conversation_id)
        data = {
            "text": extracted_text,
            "image_id": image_id,
        }
        await self.redis.set(
            key,
            json.dumps(data, ensure_ascii=False),
            ttl=self.ttl_seconds,
        )
        logger.debug(f"Saved extracted text for conversation {conversation_id}")

    async def get_extracted_text(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """Get previously extracted text from image.
        
        Returns:
            Dict with 'text' and 'image_id' or None if not found
        """
        key = self._extracted_text_key(conversation_id)
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode extracted text for {conversation_id}")
        return None

    async def save_metadata(
        self,
        conversation_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Save additional conversation metadata."""
        key = self._metadata_key(conversation_id)
        await self.redis.set(
            key,
            json.dumps(metadata, ensure_ascii=False),
            ttl=self.ttl_seconds,
        )

    async def get_metadata(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """Get conversation metadata."""
        key = self._metadata_key(conversation_id)
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode metadata for {conversation_id}")
        return None

    async def get_full_state(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Get full conversation state from Redis.
        
        Returns:
            Dict with history, subject, extracted_text, metadata
        """
        history = await self.get_history(conversation_id)
        subject = await self.get_subject(conversation_id)
        extracted = await self.get_extracted_text(conversation_id)
        metadata = await self.get_metadata(conversation_id)

        return {
            "conversation_id": conversation_id,
            "history": history or [],
            "subject": subject,
            "extracted_text": extracted.get("text") if extracted else None,
            "extracted_image_id": extracted.get("image_id") if extracted else None,
            "metadata": metadata or {},
        }

    async def clear_state(self, conversation_id: str) -> None:
        """Clear all state for a conversation."""
        keys = [
            self._history_key(conversation_id),
            self._subject_key(conversation_id),
            self._extracted_text_key(conversation_id),
            self._metadata_key(conversation_id),
        ]
        for key in keys:
            await self.redis.delete(key)
        logger.info(f"Cleared state for conversation {conversation_id}")

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()


# Global instance (lazy initialization)
_state_manager: ConversationStateManager | None = None


async def get_state_manager() -> ConversationStateManager:
    """Get or create global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ConversationStateManager()
        await _state_manager.connect()
    return _state_manager
