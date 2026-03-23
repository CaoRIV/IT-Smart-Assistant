"""Embedding helpers for PostgreSQL-backed knowledge retrieval."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


def embeddings_enabled() -> bool:
    """Return True when the configured embedding provider can be used."""
    if not settings.ENABLE_VECTOR_SEARCH:
        return False
    if settings.EMBEDDING_PROVIDER == "openai":
        return bool(settings.OPENAI_API_KEY)
    if settings.EMBEDDING_PROVIDER == "google":
        return bool(settings.GOOGLE_API_KEY)
    return False


def _get_embedding_client() -> Any:
    """Create the configured embedding client."""
    if settings.EMBEDDING_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    if settings.EMBEDDING_PROVIDER == "google":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=google")
        return GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            output_dimensionality=settings.EMBEDDING_DIMENSIONS,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")


def _serialize_vector(vector: Sequence[float]) -> str:
    """Serialize an embedding into pgvector literal format."""
    return "[" + ",".join(f"{value:.9f}" for value in vector) + "]"


def build_embedding_text(entry: dict[str, Any]) -> str:
    """Build a stable embedding payload from a knowledge entry."""
    keywords = entry.get("keywords") or []
    keyword_text = ", ".join(str(keyword) for keyword in keywords if keyword)
    parts = [
        f"Tieu de: {entry.get('title', '')}",
        f"Danh muc: {entry.get('category', '')}",
        f"Loai nguon: {entry.get('source_kind', '')}",
    ]

    if entry.get("section_title"):
        parts.append(f"Muc: {entry['section_title']}")
    if entry.get("summary"):
        parts.append(f"Tom tat: {entry['summary']}")
    if keyword_text:
        parts.append(f"Tu khoa: {keyword_text}")
    if entry.get("content"):
        parts.append(f"Noi dung: {entry['content'][:6000]}")

    return "\n".join(parts).strip()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts."""
    client = _get_embedding_client()
    if hasattr(client, "aembed_documents"):
        return await client.aembed_documents(texts)
    return client.embed_documents(texts)


async def embed_query(query: str) -> list[float] | None:
    """Embed a single retrieval query."""
    if not embeddings_enabled():
        return None

    client = _get_embedding_client()
    if hasattr(client, "aembed_query"):
        return await client.aembed_query(query)
    return client.embed_query(query)


def embed_query_sync(query: str) -> list[float] | None:
    """Embed a single retrieval query from synchronous code paths."""
    if not embeddings_enabled():
        return None

    client = _get_embedding_client()
    return client.embed_query(query)


async def sync_knowledge_entry_embeddings(db: AsyncSession) -> int:
    """Generate and store embeddings for all synced knowledge entries."""
    if not embeddings_enabled():
        logger.info("Skipping knowledge embedding sync because embeddings are not enabled.")
        return 0

    result = await db.execute(
        text(
            """
            SELECT
                id,
                title,
                category,
                source_kind,
                summary,
                content,
                keywords,
                section_title
            FROM knowledge_entries
            ORDER BY created_at ASC
            """
        )
    )
    rows = [dict(row) for row in result.mappings().all()]
    if not rows:
        return 0

    embedded_count = 0
    batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)

    for batch_start in range(0, len(rows), batch_size):
        batch_rows = rows[batch_start : batch_start + batch_size]
        texts = [build_embedding_text(row) for row in batch_rows]
        embeddings = await embed_texts(texts)

        for row, embedding in zip(batch_rows, embeddings, strict=True):
            await db.execute(
                text(
                    """
                    UPDATE knowledge_entries
                    SET
                        embedding = CAST(:embedding AS vector),
                        embedding_model = :embedding_model,
                        embedding_updated_at = NOW()
                    WHERE id = :entry_id
                    """
                ),
                {
                    "embedding": _serialize_vector(embedding),
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "entry_id": row["id"],
                },
            )
            embedded_count += 1

    logger.info(
        "Knowledge embedding sync completed | entries=%s | provider=%s | model=%s",
        embedded_count,
        settings.EMBEDDING_PROVIDER,
        settings.EMBEDDING_MODEL,
    )
    return embedded_count
