"""Schemas for synced knowledge snapshot metadata."""

from __future__ import annotations

from app.schemas.base import BaseSchema


class KnowledgeSyncStats(BaseSchema):
    """Summary returned after syncing filesystem knowledge into PostgreSQL."""

    synced: bool
    documents: int = 0
    entries: int = 0
    embeddings: int = 0
    reason: str | None = None
