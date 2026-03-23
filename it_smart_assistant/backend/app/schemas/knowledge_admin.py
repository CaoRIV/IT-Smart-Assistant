"""Schemas for filesystem-backed knowledge admin MVP."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseResponse, BaseSchema


class KnowledgeDocumentRead(BaseSchema):
    """A raw uploaded PDF document tracked by the knowledge admin UI."""

    id: str
    title: str
    category: str
    file_name: str
    relative_path: str
    page_count: int | None = None
    status: str = "uploaded"
    source_office: str | None = None
    issued_date: str | None = None
    effective_date: str | None = None
    version: str | None = None
    source_url: str | None = None
    notes: str | None = None
    workbook_type: str | None = None
    sheet_schema_config: dict[str, object] | None = None
    uploaded_at: datetime | None = None


class KnowledgeDocumentMetadataUpdate(BaseSchema):
    """Editable metadata for a tracked raw knowledge document."""

    relative_path: str
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=100)
    status: str = Field(min_length=2, max_length=50)
    source_office: str | None = Field(default=None, max_length=255)
    issued_date: str | None = Field(default=None, max_length=20)
    effective_date: str | None = Field(default=None, max_length=20)
    version: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    workbook_type: str | None = Field(default=None, max_length=100)
    sheet_schema_config: dict[str, object] | None = None


class KnowledgeDocumentBatchMetadataUpdate(BaseSchema):
    """Batch status update for multiple tracked documents."""

    relative_paths: list[str] = Field(min_length=1)
    status: str = Field(min_length=2, max_length=50)
    source_office: str | None = Field(default=None, max_length=255)
    issued_date: str | None = Field(default=None, max_length=20)
    effective_date: str | None = Field(default=None, max_length=20)
    version: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    workbook_type: str | None = Field(default=None, max_length=100)
    sheet_schema_config: dict[str, object] | None = None


class KnowledgePreviewChunkRead(BaseSchema):
    """Preview of a processed chunk for document review."""

    chunk_id: str
    section_title: str | None = None
    summary: str
    page_from: int | None = None
    page_to: int | None = None


class KnowledgePreviewTableRowRead(BaseSchema):
    """Preview of a processed table row for document review."""

    row_id: str
    label: str
    amount_text: str | None = None
    page_from: int | None = None
    page_to: int | None = None


class KnowledgePreviewTableRead(BaseSchema):
    """Preview of a processed table extracted from a document."""

    table_id: str
    title: str
    page_from: int | None = None
    page_to: int | None = None
    rows: list[KnowledgePreviewTableRowRead] = Field(default_factory=list)


class KnowledgeDocumentPreviewRead(BaseSchema):
    """Processed preview for a managed knowledge document."""

    relative_path: str
    document_id: str | None = None
    chunk_count: int = 0
    table_count: int = 0
    chunks: list[KnowledgePreviewChunkRead] = Field(default_factory=list)
    tables: list[KnowledgePreviewTableRead] = Field(default_factory=list)


class KnowledgeAdminOverviewRead(BaseSchema):
    """Top-level CMS overview used by the admin dashboard."""

    total_documents: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    normalized_counts: dict[str, int] = Field(default_factory=dict)
    runtime_counts: dict[str, int] = Field(default_factory=dict)


class FAQCreate(BaseSchema):
    """Payload for creating an FAQ entry."""

    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=100)
    question: str = Field(min_length=5, max_length=500)
    answer: str = Field(min_length=5)
    source_url: str | None = Field(default=None, max_length=500)
    keywords: list[str] = Field(default_factory=list)


class FAQRead(FAQCreate):
    """Stored FAQ record."""

    id: str
    created_at: datetime
    updated_at: datetime


class FormFieldInput(BaseSchema):
    """Field definition for a managed form template."""

    name: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    type: str = Field(default="text", max_length=50)
    required: bool = False
    placeholder: str | None = Field(default=None, max_length=255)


class FormTemplateCreate(BaseSchema):
    """Payload for creating a form template."""

    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5)
    source_url: str | None = Field(default=None, max_length=500)
    keywords: list[str] = Field(default_factory=list)
    fields: list[FormFieldInput] = Field(default_factory=list)


class FormTemplateRead(FormTemplateCreate):
    """Stored form template."""

    id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeRebuildResponse(BaseResponse):
    """Response returned after rebuilding processed knowledge."""

    documents: int = 0
    chunks: int = 0
