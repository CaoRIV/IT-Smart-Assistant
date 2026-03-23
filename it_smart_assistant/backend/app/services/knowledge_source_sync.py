"""Sync filesystem knowledge admin metadata into source-layer tables."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.paths import resolve_project_root
from app.knowledge.admin_store import load_document_metadata_map
from app.knowledge.ingest import DEFAULT_RAW_DIR, SUPPORTED_DOCUMENT_EXTENSIONS, slugify
from app.knowledge.workbook_schema import detect_workbook_schema
from app.repositories import knowledge_source as source_repo

PROJECT_ROOT = resolve_project_root(Path(__file__))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _storage_key_from_relative_path(relative_path: str) -> str:
    prefix = "knowledge_raw/"
    if relative_path.startswith(prefix):
        return f"knowledge/raw/{relative_path[len(prefix):]}"
    return f"knowledge/raw/{Path(relative_path).name}"


def _source_id_from_relative_path(relative_path: str) -> str:
    return f"src-{slugify(relative_path)}"


async def _source_tables_ready(db: AsyncSession) -> bool:
    result = await db.execute(
        text(
            """
            SELECT
                to_regclass('public.knowledge_sources') IS NOT NULL
                AND to_regclass('public.knowledge_source_versions') IS NOT NULL
                AND to_regclass('public.knowledge_source_files') IS NOT NULL
            """
        )
    )
    return bool(result.scalar())


async def sync_knowledge_source_catalog(db: AsyncSession) -> int:
    """Sync raw knowledge documents and metadata into source-layer tables."""
    if not await _source_tables_ready(db):
        return 0

    metadata_map = load_document_metadata_map()
    synced_count = 0
    seen_source_ids: list[str] = []

    for path in sorted(
        item
        for item in DEFAULT_RAW_DIR.rglob("*")
        if item.is_file() and item.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
    ):
        relative_path = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        metadata = metadata_map.get(relative_path, {})
        file_bytes = path.read_bytes()
        checksum = hashlib.sha256(file_bytes).hexdigest()
        source_id = _source_id_from_relative_path(relative_path)
        seen_source_ids.append(source_id)
        title = metadata.get("title") or path.stem.replace("_", " ").strip()
        category = metadata.get("category") or path.parent.name.replace("_", " ").title()
        current_status = metadata.get("status") or "draft"
        suffix = path.suffix.lower()
        source_type = suffix.lstrip(".")
        workbook_type = metadata.get("workbook_type") if suffix in {".csv", ".xlsx", ".xls", ".xlsm"} else None
        if workbook_type is None and suffix in {".csv", ".xlsx", ".xls", ".xlsm"}:
            detected = detect_workbook_schema(path, category=category) or {}
            workbook_type = detected.get("workbook_type")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        db_source = await source_repo.get_source_by_source_id(db, source_id)
        if db_source is None:
            db_source = await source_repo.create_source(
                db,
                payload={
                    "source_id": source_id,
                    "source_type": source_type,
                    "title": title,
                    "category": category,
                    "subcategory": workbook_type,
                    "source_office": metadata.get("source_office"),
                    "trust_level": "official",
                    "language": "vi",
                    "current_status": current_status,
                    "source_url": metadata.get("source_url"),
                    "notes": metadata.get("notes"),
                },
            )
        else:
            db_source = await source_repo.update_source(
                db,
                db_source=db_source,
                update_data={
                    "title": title,
                    "category": category,
                    "subcategory": workbook_type,
                    "source_office": metadata.get("source_office"),
                    "current_status": current_status,
                    "source_url": metadata.get("source_url"),
                    "notes": metadata.get("notes"),
                },
            )

        active_version = await source_repo.get_active_source_version(db, source_pk_id=db_source.id)
        version_payload = {
            "version_label": metadata.get("version"),
            "issued_date": _parse_date(metadata.get("issued_date")),
            "effective_date": _parse_date(metadata.get("effective_date")),
            "expiry_date": None,
            "status": current_status,
            "checksum_sha256": checksum,
            "is_active": True,
            "review_notes": metadata.get("notes"),
            "reviewed_by": None,
            "reviewed_at": datetime.now(UTC) if current_status == "published" else None,
        }

        if active_version is None:
            active_version = await source_repo.create_source_version(
                db,
                payload={
                    "source_pk_id": db_source.id,
                    **version_payload,
                },
            )
        elif active_version.checksum_sha256 == checksum:
            active_version = await source_repo.update_source_version(
                db,
                db_version=active_version,
                update_data=version_payload,
            )
        else:
            await source_repo.deactivate_active_versions(db, source_pk_id=db_source.id)
            active_version = await source_repo.create_source_version(
                db,
                payload={
                    "source_pk_id": db_source.id,
                    **version_payload,
                },
            )

        existing_files = await source_repo.list_source_files_by_version(
            db,
            source_version_id=active_version.id,
        )
        if not existing_files:
            await source_repo.create_source_file(
                db,
                payload={
                    "source_version_id": active_version.id,
                    "file_name": path.name,
                    "file_type": source_type,
                    "storage_backend": settings.STORAGE_BACKEND,
                    "storage_key": _storage_key_from_relative_path(relative_path),
                    "relative_path": relative_path,
                    "mime_type": mime_type,
                    "size_bytes": path.stat().st_size,
                    "page_count": None,
                    "is_scanned": None,
                    "ocr_used": None,
                    "extractor": None,
                    "quality_score": None,
                },
            )

        synced_count += 1

    await source_repo.delete_sources_not_in(db, source_ids=seen_source_ids)

    return synced_count
