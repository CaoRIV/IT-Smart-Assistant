"""Feedback service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.repositories import feedback as feedback_repo
from app.schemas.feedback import MessageFeedbackCreate


class FeedbackService:
    """Service for assistant-message feedback."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update_feedback(
        self,
        *,
        data: MessageFeedbackCreate,
        user_id: UUID,
    ):
        message_and_conversation = await feedback_repo.get_message_with_conversation(
            self.db,
            message_id=data.message_id,
        )
        if not message_and_conversation:
            raise NotFoundError(message="Message not found")

        message, conversation = message_and_conversation
        if conversation.user_id != user_id:
            raise AuthorizationError(message="You cannot rate this message")
        if message.role != "assistant":
            raise AuthorizationError(message="Only assistant messages can be rated")

        current_feedback = await feedback_repo.get_feedback_for_message_and_user(
            self.db,
            message_id=data.message_id,
            user_id=user_id,
        )
        if current_feedback:
            return await feedback_repo.update_feedback(
                self.db,
                db_feedback=current_feedback,
                helpful=data.helpful,
                comment=data.comment,
            )

        return await feedback_repo.create_feedback(
            self.db,
            message_id=data.message_id,
            user_id=user_id,
            helpful=data.helpful,
            comment=data.comment,
        )
