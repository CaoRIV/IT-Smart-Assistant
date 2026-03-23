"""Repository helpers for knowledge source-layer tables."""

from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeSource, KnowledgeSourceFile, KnowledgeSourceVersion


async def get_source_by_source_id(
    db: AsyncSession,
    source_id: str,
) -> KnowledgeSource | None:
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.source_id == source_id))
    return result.scalar_one_or_none()


async def create_source(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeSource:
    source = KnowledgeSource(**payload)
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


async def update_source(
    db: AsyncSession,
    *,
    db_source: KnowledgeSource,
    update_data: dict,
) -> KnowledgeSource:
    for field, value in update_data.items():
        setattr(db_source, field, value)
    db.add(db_source)
    await db.flush()
    await db.refresh(db_source)
    return db_source


async def get_active_source_version(
    db: AsyncSession,
    *,
    source_pk_id,
) -> KnowledgeSourceVersion | None:
    result = await db.execute(
        select(KnowledgeSourceVersion).where(
            KnowledgeSourceVersion.source_pk_id == source_pk_id,
            KnowledgeSourceVersion.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def deactivate_active_versions(
    db: AsyncSession,
    *,
    source_pk_id,
) -> None:
    await db.execute(
        update(KnowledgeSourceVersion)
        .where(
            KnowledgeSourceVersion.source_pk_id == source_pk_id,
            KnowledgeSourceVersion.is_active.is_(True),
        )
        .values(is_active=False)
    )
    await db.flush()


async def create_source_version(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeSourceVersion:
    version = KnowledgeSourceVersion(**payload)
    db.add(version)
    await db.flush()
    await db.refresh(version)
    return version


async def update_source_version(
    db: AsyncSession,
    *,
    db_version: KnowledgeSourceVersion,
    update_data: dict,
) -> KnowledgeSourceVersion:
    for field, value in update_data.items():
        setattr(db_version, field, value)
    db.add(db_version)
    await db.flush()
    await db.refresh(db_version)
    return db_version


async def list_source_files_by_version(
    db: AsyncSession,
    *,
    source_version_id,
) -> list[KnowledgeSourceFile]:
    result = await db.execute(
        select(KnowledgeSourceFile).where(KnowledgeSourceFile.source_version_id == source_version_id)
    )
    return list(result.scalars().all())


async def create_source_file(
    db: AsyncSession,
    *,
    payload: dict,
) -> KnowledgeSourceFile:
    source_file = KnowledgeSourceFile(**payload)
    db.add(source_file)
    await db.flush()
    await db.refresh(source_file)
    return source_file


async def delete_sources_not_in(
    db: AsyncSession,
    *,
    source_ids: list[str],
) -> None:
    if source_ids:
        await db.execute(delete(KnowledgeSource).where(KnowledgeSource.source_id.not_in(source_ids)))
    else:
        await db.execute(delete(KnowledgeSource))
    await db.flush()
