"""Repository helpers for knowledge persistence."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import (
    KnowledgeChunk,
    KnowledgeCourse,
    KnowledgeCourseCatalog,
    KnowledgeDocument,
    KnowledgeEntry,
    KnowledgeFaq,
    KnowledgeForm,
    KnowledgeInteraction,
    KnowledgeProcedure,
    KnowledgeTable,
    KnowledgeTableRow,
)


async def clear_knowledge_snapshot(db: AsyncSession) -> None:
    """Remove all synced knowledge snapshot rows."""
    await db.execute(delete(KnowledgeEntry))
    await db.execute(delete(KnowledgeDocument))
    await db.flush()


async def clear_normalized_knowledge(db: AsyncSession) -> None:
    """Remove all normalized knowledge rows before a full resync."""
    await db.execute(delete(KnowledgeCourse))
    await db.execute(delete(KnowledgeCourseCatalog))
    await db.execute(delete(KnowledgeTableRow))
    await db.execute(delete(KnowledgeTable))
    await db.execute(delete(KnowledgeChunk))
    await db.execute(delete(KnowledgeFaq))
    await db.execute(delete(KnowledgeInteraction))
    await db.execute(delete(KnowledgeProcedure))
    await db.execute(delete(KnowledgeForm))
    await db.flush()


async def create_knowledge_document(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeDocument:
    """Create a knowledge document row."""
    document = KnowledgeDocument(**payload)
    db.add(document)
    await db.flush()
    return document


async def create_knowledge_entry(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeEntry:
    """Create a knowledge entry row."""
    entry = KnowledgeEntry(**payload)
    db.add(entry)
    await db.flush()
    return entry


async def create_knowledge_chunk(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeChunk:
    chunk = KnowledgeChunk(**payload)
    db.add(chunk)
    await db.flush()
    return chunk


async def create_knowledge_course_catalog(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeCourseCatalog:
    catalog = KnowledgeCourseCatalog(**payload)
    db.add(catalog)
    await db.flush()
    return catalog


async def create_knowledge_course(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeCourse:
    course = KnowledgeCourse(**payload)
    db.add(course)
    await db.flush()
    return course


async def create_knowledge_table(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeTable:
    table = KnowledgeTable(**payload)
    db.add(table)
    await db.flush()
    return table


async def create_knowledge_table_row(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeTableRow:
    row = KnowledgeTableRow(**payload)
    db.add(row)
    await db.flush()
    return row


async def create_knowledge_faq(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeFaq:
    faq = KnowledgeFaq(**payload)
    db.add(faq)
    await db.flush()
    return faq


async def create_knowledge_interaction(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeInteraction:
    interaction = KnowledgeInteraction(**payload)
    db.add(interaction)
    await db.flush()
    return interaction


async def create_knowledge_procedure(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeProcedure:
    procedure = KnowledgeProcedure(**payload)
    db.add(procedure)
    await db.flush()
    return procedure


async def create_knowledge_form(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeForm:
    form = KnowledgeForm(**payload)
    db.add(form)
    await db.flush()
    return form


async def get_document_by_external_id(
    db: AsyncSession,
    external_id: str,
) -> KnowledgeDocument | None:
    """Fetch a synced knowledge document by external id."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.external_id == external_id)
    )
    return result.scalar_one_or_none()
