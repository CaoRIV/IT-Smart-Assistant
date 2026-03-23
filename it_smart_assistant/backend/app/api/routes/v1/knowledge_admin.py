"""Filesystem-backed knowledge admin routes."""

from __future__ import annotations

from sqlalchemy import text

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentAdmin
from app.db.session import get_db_context
from app.knowledge.admin_store import (
    batch_update_document_metadata,
    create_faq,
    create_form_template,
    delete_document,
    delete_faq,
    delete_form_template,
    get_document_preview,
    list_documents,
    list_faqs,
    list_forms,
    rebuild_knowledge,
    save_uploaded_document,
    update_faq,
    update_document_metadata,
    update_form_template,
)
from app.knowledge.service import reset_student_knowledge_base_cache
from app.schemas.base import BaseResponse
from app.schemas.knowledge_admin import (
    FAQCreate,
    FAQRead,
    FormTemplateCreate,
    FormTemplateRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentBatchMetadataUpdate,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeDocumentPreviewRead,
    KnowledgeAdminOverviewRead,
    KnowledgeRebuildResponse,
)
from app.services.knowledge_normalized_sync import sync_normalized_knowledge
from app.services.knowledge_sync import sync_knowledge_snapshot
from app.services.knowledge_source_sync import sync_knowledge_source_catalog

router = APIRouter(prefix="/knowledge-admin")


async def _refresh_knowledge_runtime_cache() -> None:
    async with get_db_context() as db:
        await sync_knowledge_source_catalog(db)
        await sync_normalized_knowledge(db)
    await sync_knowledge_snapshot()
    reset_student_knowledge_base_cache()


@router.get("/overview", response_model=KnowledgeAdminOverviewRead)
async def read_knowledge_overview(
    current_user: CurrentAdmin,
):
    """Return CMS overview counts for source, normalized, and runtime layers."""
    documents = list_documents()
    status_counts: dict[str, int] = {}
    for document in documents:
        status_counts[document.status] = status_counts.get(document.status, 0) + 1

    normalized_counts: dict[str, int] = {}
    runtime_counts: dict[str, int] = {}
    async with get_db_context() as db:
        normalized_table_map = {
            "chunks": "knowledge_chunks",
            "tables": "knowledge_tables",
            "table_rows": "knowledge_table_rows",
            "faqs": "knowledge_faqs",
            "forms": "knowledge_forms",
            "procedures": "knowledge_procedures",
            "course_catalogs": "knowledge_course_catalogs",
            "courses": "knowledge_courses",
        }
        runtime_table_map = {
            "documents": "knowledge_documents",
            "entries": "knowledge_entries",
        }

        for key, table_name in normalized_table_map.items():
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            normalized_counts[key] = int(result.scalar() or 0)

        for key, table_name in runtime_table_map.items():
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            runtime_counts[key] = int(result.scalar() or 0)

    return KnowledgeAdminOverviewRead(
        total_documents=len(documents),
        status_counts=status_counts,
        normalized_counts=normalized_counts,
        runtime_counts=runtime_counts,
    )


@router.get("/documents", response_model=list[KnowledgeDocumentRead])
async def read_documents(
    current_user: CurrentAdmin,
):
    """List uploaded raw PDF documents for knowledge management."""
    return list_documents()


@router.post("/documents/upload", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentAdmin,
    file: UploadFile = File(...),
    category: str = Form(...),
    workbook_type: str | None = Form(default=None),
):
    """Upload a knowledge document to the raw store and rebuild processed knowledge."""
    content = await file.read()
    document = save_uploaded_document(
        file.filename or "document.pdf",
        content,
        category,
        workbook_type=workbook_type,
    )
    await _refresh_knowledge_runtime_cache()
    return document


@router.delete("/documents", response_model=BaseResponse)
async def remove_document(
    relative_path: str,
    current_user: CurrentAdmin,
):
    """Delete a tracked raw PDF document and refresh downstream layers."""
    delete_document(relative_path)
    await _refresh_knowledge_runtime_cache()
    return BaseResponse(message="Document deleted")


@router.patch("/documents/metadata", response_model=KnowledgeDocumentRead)
async def patch_document_metadata(
    document_in: KnowledgeDocumentMetadataUpdate,
    current_user: CurrentAdmin,
):
    """Update metadata and publish state for a tracked raw document."""
    document = update_document_metadata(document_in)
    await _refresh_knowledge_runtime_cache()
    return document


@router.post("/documents/metadata/batch", response_model=list[KnowledgeDocumentRead])
async def batch_patch_document_metadata(
    documents_in: KnowledgeDocumentBatchMetadataUpdate,
    current_user: CurrentAdmin,
):
    """Batch update metadata and publish state for tracked raw documents."""
    documents = batch_update_document_metadata(documents_in)
    await _refresh_knowledge_runtime_cache()
    return documents


@router.get("/documents/preview", response_model=KnowledgeDocumentPreviewRead)
async def read_document_preview(
    current_user: CurrentAdmin,
    relative_path: str,
):
    """Preview processed chunks and tables for a document under review."""
    return get_document_preview(relative_path)


@router.post("/documents/rebuild", response_model=KnowledgeRebuildResponse)
async def trigger_rebuild(
    current_user: CurrentAdmin,
):
    """Rebuild processed knowledge artifacts from the current raw/admin stores."""
    result = rebuild_knowledge()
    await _refresh_knowledge_runtime_cache()
    return KnowledgeRebuildResponse(
        message="Knowledge rebuilt successfully",
        documents=result["documents"],
        chunks=result["chunks"],
    )


@router.get("/faqs", response_model=list[FAQRead])
async def read_faqs(
    current_user: CurrentAdmin,
):
    """List admin-managed FAQs."""
    return list_faqs()


@router.post("/faqs", response_model=FAQRead, status_code=status.HTTP_201_CREATED)
async def create_faq_entry(
    faq_in: FAQCreate,
    current_user: CurrentAdmin,
):
    """Create a new FAQ entry."""
    faq = create_faq(faq_in)
    await _refresh_knowledge_runtime_cache()
    return faq


@router.patch("/faqs/{faq_id}", response_model=FAQRead)
async def update_faq_entry(
    faq_id: str,
    faq_in: FAQCreate,
    current_user: CurrentAdmin,
):
    """Update an existing FAQ entry."""
    faq = update_faq(faq_id, faq_in)
    await _refresh_knowledge_runtime_cache()
    return faq


@router.delete("/faqs/{faq_id}", response_model=BaseResponse)
async def remove_faq_entry(
    faq_id: str,
    current_user: CurrentAdmin,
):
    """Delete an FAQ entry."""
    delete_faq(faq_id)
    await _refresh_knowledge_runtime_cache()
    return BaseResponse(message="FAQ deleted")


@router.get("/forms", response_model=list[FormTemplateRead])
async def read_form_templates(
    current_user: CurrentAdmin,
):
    """List admin-managed form templates."""
    return list_forms()


@router.post("/forms", response_model=FormTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_form_template_entry(
    form_in: FormTemplateCreate,
    current_user: CurrentAdmin,
):
    """Create a new form template entry."""
    form_template = create_form_template(form_in)
    await _refresh_knowledge_runtime_cache()
    return form_template


@router.patch("/forms/{form_id}", response_model=FormTemplateRead)
async def update_form_template_entry(
    form_id: str,
    form_in: FormTemplateCreate,
    current_user: CurrentAdmin,
):
    """Update an existing form template entry."""
    form_template = update_form_template(form_id, form_in)
    await _refresh_knowledge_runtime_cache()
    return form_template


@router.delete("/forms/{form_id}", response_model=BaseResponse)
async def remove_form_template_entry(
    form_id: str,
    current_user: CurrentAdmin,
):
    """Delete a form template entry."""
    delete_form_template(form_id)
    await _refresh_knowledge_runtime_cache()
    return BaseResponse(message="Form template deleted")
