"""Schemas for chat attachment uploads and prompt context."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.schemas.base import BaseSchema


AttachmentKind = Literal["document", "image"]


class ChatAttachmentRead(BaseSchema):
    """Public metadata for an uploaded chat attachment."""

    id: str
    file_name: str
    media_type: str
    kind: AttachmentKind
    size_bytes: int
    created_at: datetime


class PromptAttachment(BaseSchema):
    """Internal attachment payload used to enrich the agent prompt."""

    id: str
    file_name: str
    media_type: str
    kind: AttachmentKind
    extracted_text: str | None = None
    data_url: str | None = None
