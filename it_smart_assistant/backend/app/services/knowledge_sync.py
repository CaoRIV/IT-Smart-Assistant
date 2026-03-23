"""Build runtime retrieval snapshot from normalized knowledge tables."""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_context
from app.knowledge.ingest import slugify
from app.repositories import knowledge as knowledge_repo
from app.schemas.knowledge import KnowledgeSyncStats
from app.services.knowledge_embedding import sync_knowledge_entry_embeddings

logger = logging.getLogger(__name__)


async def _knowledge_tables_ready(db: AsyncSession) -> bool:
    result = await db.execute(
        text(
            """
            SELECT
                to_regclass('public.knowledge_documents') IS NOT NULL
                AND to_regclass('public.knowledge_entries') IS NOT NULL
                AND to_regclass('public.knowledge_sources') IS NOT NULL
                AND to_regclass('public.knowledge_source_versions') IS NOT NULL
                AND to_regclass('public.knowledge_source_files') IS NOT NULL
                AND to_regclass('public.knowledge_chunks') IS NOT NULL
                AND to_regclass('public.knowledge_tables') IS NOT NULL
                AND to_regclass('public.knowledge_table_rows') IS NOT NULL
                AND to_regclass('public.knowledge_faqs') IS NOT NULL
                AND to_regclass('public.knowledge_forms') IS NOT NULL
                AND to_regclass('public.knowledge_procedures') IS NOT NULL
                AND to_regclass('public.knowledge_course_catalogs') IS NOT NULL
                AND to_regclass('public.knowledge_courses') IS NOT NULL
            """
        )
    )
    return bool(result.scalar())


async def _sync_source_documents(db: AsyncSession) -> tuple[int, dict]:
    document_count = 0
    source_document_map: dict = {}
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    s.source_id,
                    s.source_type,
                    s.title,
                    s.category,
                    s.source_office,
                    s.source_url,
                    s.notes,
                    s.current_status,
                    v.id AS source_version_id,
                    v.version_label,
                    v.issued_date,
                    v.effective_date,
                    v.status AS version_status,
                    f.relative_path,
                    f.storage_key,
                    f.file_name,
                    f.page_count
                FROM knowledge_sources s
                JOIN knowledge_source_versions v
                    ON v.source_pk_id = s.id
                   AND v.is_active IS TRUE
                LEFT JOIN knowledge_source_files f
                    ON f.source_version_id = v.id
                WHERE s.current_status = 'published'
                  AND v.status = 'published'
                ORDER BY s.created_at ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = await knowledge_repo.create_knowledge_document(
            db,
            payload={
                "external_id": row["source_id"],
                "title": row["title"],
                "category": row["category"],
                "source_kind": "document",
                "summary": row["notes"] or row["title"],
                "source_url": row["source_url"],
                "source_path": row["relative_path"],
                "relative_path": row["relative_path"],
                "storage_key": row["storage_key"],
                "page_count": row["page_count"],
                "status": "published",
                "metadata_json": {
                    "source_type": row["source_type"],
                    "source_office": row["source_office"],
                    "version_label": row["version_label"],
                    "issued_date": row["issued_date"].isoformat() if row["issued_date"] else None,
                    "effective_date": row["effective_date"].isoformat() if row["effective_date"] else None,
                    "file_name": row["file_name"],
                    "source_version_id": str(row["source_version_id"]),
                },
            },
        )
        source_document_map[row["source_version_id"]] = document
        document_count += 1

    return document_count, source_document_map


async def _sync_chunk_entries(db: AsyncSession, *, source_document_map: dict) -> int:
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    chunk_id,
                    source_version_id,
                    heading,
                    section_title,
                    content,
                    summary,
                    page_from,
                    page_to,
                    keywords,
                    metadata_json,
                    status
                FROM knowledge_chunks
                WHERE status = 'published'
                ORDER BY created_at ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = source_document_map.get(row["source_version_id"])
        if document is None:
            continue

        metadata_json = row["metadata_json"] or {}
        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": row["chunk_id"],
                "document_id": document.id,
                "title": document.title,
                "category": document.category,
                "source_kind": "chunk",
                "summary": row["summary"] or row["content"] or document.title,
                "content": row["content"] or "",
                "keywords": row["keywords"] or [],
                "section_title": row["section_title"] or row["heading"],
                "page_from": row["page_from"],
                "page_to": row["page_to"],
                "source_url": document.source_url,
                "source_path": document.source_path,
                "entry_metadata": metadata_json,
            },
        )
        entry_count += 1

    return entry_count


async def _sync_table_row_entries(db: AsyncSession, *, source_document_map: dict) -> int:
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    t.table_id,
                    t.title AS table_title,
                    t.source_version_id,
                    r.row_id,
                    r.row_order,
                    r.label,
                    r.row_data,
                    r.search_text,
                    r.track_tags,
                    r.basis_tags,
                    r.page_from,
                    r.page_to
                FROM knowledge_tables t
                JOIN knowledge_table_rows r ON r.table_pk_id = t.id
                WHERE t.status = 'published'
                  AND r.status = 'published'
                ORDER BY t.created_at ASC, r.row_order ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = source_document_map.get(row["source_version_id"])
        if document is None:
            continue

        row_data = row["row_data"] or {}
        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": f"{row['table_id']}-{row['row_id']}-{row['row_order']:02d}",
                "document_id": document.id,
                "title": document.title,
                "category": document.category,
                "source_kind": "table_row",
                "summary": f"{row['table_title']} - {row.get('label') or ''}".strip(" -"),
                "content": row["search_text"]
                or (
                    f"{row['table_title']}. {row.get('label') or ''}. "
                    f"Muc du lieu: {json_dumps_safe(row_data)}"
                ),
                "keywords": [
                    document.category,
                    document.title,
                    row["table_title"],
                    row.get("label") or "",
                    *list(row.get("track_tags") or []),
                    *list(row.get("basis_tags") or []),
                ],
                "section_title": row["table_title"],
                "page_from": row["page_from"],
                "page_to": row["page_to"],
                "source_url": document.source_url,
                "source_path": document.source_path,
                "entry_metadata": {
                    "track_tags": row.get("track_tags") or [],
                    "basis_tags": row.get("basis_tags") or [],
                    "raw_table_title": row["table_title"],
                    **row_data,
                },
            },
        )
        entry_count += 1

    return entry_count


async def _sync_course_catalog_entries(db: AsyncSession, *, source_document_map: dict) -> int:
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    catalog.catalog_id,
                    catalog.program_name,
                    catalog.program_code,
                    catalog.academic_year,
                    catalog.canonical_sheet,
                    catalog.metadata_json AS catalog_metadata,
                    catalog.source_version_id,
                    course.course_record_id,
                    course.program_track,
                    course.degree_level,
                    course.semester_number,
                    course.semester_label,
                    course.course_order,
                    course.course_name,
                    course.normalized_course_name,
                    course.course_name_aliases,
                    course.course_code,
                    course.credits,
                    course.lecture_hours,
                    course.discussion_hours,
                    course.course_design_hours,
                    course.project_hours,
                    course.lab_hours,
                    course.practice_hours,
                    course.self_study_hours,
                    course.prerequisite_text,
                    course.prerequisite_codes,
                    course.teaching_language,
                    course.search_text,
                    course.raw_row_data
                FROM knowledge_course_catalogs catalog
                JOIN knowledge_courses course ON course.catalog_pk_id = catalog.id
                WHERE catalog.status = 'published'
                  AND course.status = 'published'
                ORDER BY catalog.created_at ASC, course.program_track ASC, course.semester_number ASC NULLS LAST, course.course_order ASC NULLS LAST, course.row_number ASC
                """
            )
        )
    ).mappings()

    grouped_courses: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for row in rows:
        document = source_document_map.get(row["source_version_id"])
        if document is None:
            continue

        grouped_courses[
            (
                row["catalog_id"],
                row["program_track"] or "khac",
                row["semester_label"] or "Khong ro hoc ky",
            )
        ].append(row)

        summary_parts = [
            row["course_name"],
            f"Ma mon {row['course_code']}",
            f"{row['credits']} tin chi",
            row["semester_label"],
            row["program_track"],
        ]
        if row["prerequisite_text"]:
            summary_parts.append(f"Tien quyet {row['prerequisite_text']}")
        if row["teaching_language"]:
            summary_parts.append(f"Ngon ngu {row['teaching_language']}")

        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": row["course_record_id"],
                "document_id": document.id,
                "title": row["course_name"],
                "category": document.category,
                "source_kind": "course_record",
                "summary": " - ".join(part for part in summary_parts if part),
                "content": (
                    f"Hoc phan: {row['course_name']}\n"
                    f"Ma hoc phan: {row['course_code']}\n"
                    f"Chuong trinh: {row['program_track']}\n"
                    f"Hoc ky: {row['semester_label']}\n"
                    f"So tin chi: {row['credits']}\n"
                    f"LT: {row['lecture_hours'] or 0}; TL/BT: {row['discussion_hours'] or 0}; "
                    f"TKMH: {row['course_design_hours'] or 0}; BTL: {row['project_hours'] or 0}; "
                    f"TN: {row['lab_hours'] or 0}; TH: {row['practice_hours'] or 0}; THoc: {row['self_study_hours'] or 0}\n"
                    f"Hoc phan tien quyet: {row['prerequisite_text'] or 'Khong co'}\n"
                    f"Ngon ngu giang day: {row['teaching_language'] or 'Khong ro'}"
                ),
                "keywords": [
                    document.category,
                    row["program_name"],
                    row["program_track"] or "",
                    row["semester_label"] or "",
                    row["course_code"],
                    row["course_name"],
                    *(row["course_name_aliases"] or []),
                    row["teaching_language"] or "",
                ],
                "section_title": row["semester_label"],
                "page_from": None,
                "page_to": None,
                "source_url": document.source_url,
                "source_path": document.source_path,
                "entry_metadata": {
                    "catalog_id": row["catalog_id"],
                    "program_name": row["program_name"],
                    "program_code": row["program_code"],
                    "academic_year": row["academic_year"],
                    "canonical_sheet": row["canonical_sheet"],
                    "program_track": row["program_track"],
                    "degree_level": row["degree_level"],
                    "semester_number": row["semester_number"],
                    "semester_label": row["semester_label"],
                    "course_order": row["course_order"],
                    "course_code": row["course_code"],
                    "credits": row["credits"],
                    "lecture_hours": row["lecture_hours"],
                    "discussion_hours": row["discussion_hours"],
                    "course_design_hours": row["course_design_hours"],
                    "project_hours": row["project_hours"],
                    "lab_hours": row["lab_hours"],
                    "practice_hours": row["practice_hours"],
                    "self_study_hours": row["self_study_hours"],
                    "prerequisite_text": row["prerequisite_text"],
                    "prerequisite_codes": row["prerequisite_codes"] or [],
                    "teaching_language": row["teaching_language"],
                    "normalized_course_name": row["normalized_course_name"],
                    "aliases": row["course_name_aliases"] or [],
                    "raw_row_data": row["raw_row_data"] or {},
                    **(row["catalog_metadata"] or {}),
                },
            },
        )
        entry_count += 1

    for (catalog_id, program_track, semester_label), items in grouped_courses.items():
        first = items[0]
        document = source_document_map.get(first["source_version_id"])
        if document is None:
            continue

        course_codes = [item["course_code"] for item in items]
        course_names = [item["course_name"] for item in items]
        total_credits = sum(int(item["credits"] or 0) for item in items)
        listed_courses = "; ".join(
            f"{item['course_code']} - {item['course_name']}" for item in items[:20]
        )
        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": f"{catalog_id}-{program_track}-{slugify(semester_label)}-summary",
                "document_id": document.id,
                "title": f"{first['program_name']} - {program_track} - {semester_label}",
                "category": document.category,
                "source_kind": "course_summary",
                "summary": f"{semester_label} ({program_track}) co {len(items)} hoc phan, tong {total_credits} tin chi.",
                "content": (
                    f"Chuong trinh {first['program_name']} - {program_track} - {semester_label}.\n"
                    f"So hoc phan: {len(items)}. Tong tin chi: {total_credits}.\n"
                    f"Danh sach mon hoc: {listed_courses}"
                ),
                "keywords": [
                    document.category,
                    first["program_name"],
                    program_track,
                    semester_label,
                    "danh sach mon hoc",
                    "tong tin chi",
                ],
                "section_title": semester_label,
                "page_from": None,
                "page_to": None,
                "source_url": document.source_url,
                "source_path": document.source_path,
                "entry_metadata": {
                    "catalog_id": catalog_id,
                    "program_track": program_track,
                    "semester_label": semester_label,
                    "semester_number": first["semester_number"],
                    "course_count": len(items),
                    "total_credits": total_credits,
                    "course_codes": course_codes,
                    "course_names": course_names,
                },
            },
        )
        entry_count += 1

    return entry_count


async def _sync_faq_documents(db: AsyncSession) -> tuple[int, int]:
    document_count = 0
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    faq_id,
                    question,
                    answer,
                    category,
                    keywords,
                    source_url
                FROM knowledge_faqs
                WHERE status = 'published'
                ORDER BY created_at ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = await knowledge_repo.create_knowledge_document(
            db,
            payload={
                "external_id": row["faq_id"],
                "title": row["question"],
                "category": row["category"],
                "source_kind": "faq",
                "summary": row["question"],
                "source_url": row["source_url"],
                "source_path": None,
                "relative_path": None,
                "storage_key": None,
                "page_count": None,
                "status": "published",
                "metadata_json": {"keywords": row["keywords"] or []},
            },
        )
        document_count += 1

        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": f"{row['faq_id']}-entry",
                "document_id": document.id,
                "title": row["question"],
                "category": row["category"],
                "source_kind": "faq",
                "summary": row["question"],
                "content": f"Cau hoi: {row['question']}\n\nTra loi: {row['answer']}",
                "keywords": row["keywords"] or [],
                "section_title": None,
                "page_from": None,
                "page_to": None,
                "source_url": row["source_url"],
                "source_path": None,
                "entry_metadata": {},
            },
        )
        entry_count += 1

    return document_count, entry_count


async def _sync_form_documents(db: AsyncSession) -> tuple[int, int]:
    document_count = 0
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    form_id,
                    title,
                    category,
                    description,
                    keywords,
                    fields,
                    related_procedure_id
                FROM knowledge_forms
                WHERE status = 'published'
                ORDER BY created_at ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = await knowledge_repo.create_knowledge_document(
            db,
            payload={
                "external_id": row["form_id"],
                "title": row["title"],
                "category": row["category"],
                "source_kind": "form_template",
                "summary": row["description"] or row["title"],
                "source_url": None,
                "source_path": None,
                "relative_path": None,
                "storage_key": None,
                "page_count": None,
                "status": "published",
                "metadata_json": {
                    "keywords": row["keywords"] or [],
                    "related_procedure_id": row["related_procedure_id"],
                },
            },
        )
        document_count += 1

        field_descriptions = [
            f"{field.get('label', '')} ({field.get('name', '')}, {field.get('type', 'text')})"
            for field in (row["fields"] or [])
        ]
        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": f"{row['form_id']}-entry",
                "document_id": document.id,
                "title": row["title"],
                "category": row["category"],
                "source_kind": "form_template",
                "summary": row["description"] or row["title"],
                "content": (
                    f"Bieu mau: {row['title']}\n\n"
                    f"Mo ta: {row['description'] or ''}\n\n"
                    f"Cac truong: {', '.join(field_descriptions) if field_descriptions else 'Khong co'}"
                ),
                "keywords": row["keywords"] or [],
                "section_title": None,
                "page_from": None,
                "page_to": None,
                "source_url": None,
                "source_path": None,
                "entry_metadata": {
                    "fields": row["fields"] or [],
                    "related_procedure_id": row["related_procedure_id"],
                },
            },
        )
        entry_count += 1

    return document_count, entry_count


async def _sync_procedure_documents(db: AsyncSession) -> tuple[int, int]:
    document_count = 0
    entry_count = 0
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    procedure_id,
                    title,
                    category,
                    keywords,
                    eligibility,
                    required_documents,
                    steps,
                    contact_office,
                    related_form_id,
                    source_ids
                FROM knowledge_procedures
                WHERE status = 'published'
                ORDER BY created_at ASC
                """
            )
        )
    ).mappings()

    for row in rows:
        document = await knowledge_repo.create_knowledge_document(
            db,
            payload={
                "external_id": row["procedure_id"],
                "title": row["title"],
                "category": row["category"],
                "source_kind": "procedure",
                "summary": row["title"],
                "source_url": None,
                "source_path": None,
                "relative_path": None,
                "storage_key": None,
                "page_count": None,
                "status": "published",
                "metadata_json": {
                    "keywords": row["keywords"] or [],
                    "related_form_id": row["related_form_id"],
                    "source_ids": row["source_ids"] or [],
                },
            },
        )
        document_count += 1

        await knowledge_repo.create_knowledge_entry(
            db,
            payload={
                "external_id": f"{row['procedure_id']}-entry",
                "document_id": document.id,
                "title": row["title"],
                "category": row["category"],
                "source_kind": "procedure",
                "summary": row["title"],
                "content": (
                    f"Thu tuc: {row['title']}\n\n"
                    f"Dieu kien: {join_lines(row['eligibility'])}\n\n"
                    f"Ho so: {join_lines(row['required_documents'])}\n\n"
                    f"Cac buoc: {join_lines(row['steps'])}\n\n"
                    f"Don vi lien he: {row['contact_office'] or 'Khong ro'}"
                ),
                "keywords": row["keywords"] or [],
                "section_title": None,
                "page_from": None,
                "page_to": None,
                "source_url": None,
                "source_path": None,
                "entry_metadata": {
                    "eligibility": row["eligibility"] or [],
                    "required_documents": row["required_documents"] or [],
                    "steps": row["steps"] or [],
                    "contact_office": row["contact_office"],
                    "related_form_id": row["related_form_id"],
                    "source_ids": row["source_ids"] or [],
                },
            },
        )
        entry_count += 1

    return document_count, entry_count


def join_lines(values: list | None) -> str:
    if not values:
        return "Khong co"
    return "; ".join(str(value) for value in values)


def json_dumps_safe(payload: dict) -> str:
    try:
        import json

        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(payload)


async def sync_knowledge_snapshot() -> KnowledgeSyncStats:
    """Persist the runtime retrieval snapshot from normalized PostgreSQL tables."""
    async with get_db_context() as db:
        if not await _knowledge_tables_ready(db):
            logger.warning("Knowledge sync skipped because normalized knowledge tables are not available yet.")
            return KnowledgeSyncStats(
                synced=False,
                reason="normalized knowledge tables are not migrated yet",
            )

        await knowledge_repo.clear_knowledge_snapshot(db)

        source_documents, source_document_map = await _sync_source_documents(db)
        chunk_entries = await _sync_chunk_entries(db, source_document_map=source_document_map)
        table_entries = await _sync_table_row_entries(db, source_document_map=source_document_map)
        course_entries = await _sync_course_catalog_entries(db, source_document_map=source_document_map)
        faq_documents, faq_entries = await _sync_faq_documents(db)
        form_documents, form_entries = await _sync_form_documents(db)
        procedure_documents, procedure_entries = await _sync_procedure_documents(db)

        try:
            embedded_entries = await sync_knowledge_entry_embeddings(db)
        except Exception as exc:
            logger.warning("Knowledge embedding sync failed, continuing without vector updates: %s", exc)
            embedded_entries = 0

        return KnowledgeSyncStats(
            synced=True,
            documents=source_documents + faq_documents + form_documents + procedure_documents,
            entries=chunk_entries + table_entries + course_entries + faq_entries + form_entries + procedure_entries,
            embeddings=embedded_entries,
        )
