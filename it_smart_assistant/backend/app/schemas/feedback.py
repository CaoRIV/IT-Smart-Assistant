"""Schemas for message feedback."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class MessageFeedbackCreate(BaseSchema):
    """Create or update feedback for a single assistant message."""

    message_id: UUID
    helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


class MessageFeedbackRead(BaseSchema):
    """Feedback response."""

    id: UUID
    message_id: UUID
    user_id: UUID
    helpful: bool
    comment: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
