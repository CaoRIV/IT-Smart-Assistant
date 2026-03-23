"""Knowledge persistence models for production-lite retrieval infrastructure."""

from __future__ import annotations

import uuid

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class KnowledgeSource(Base, TimestampMixin):
    """Source-of-truth record for a knowledge asset."""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="official")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="vi")
    current_status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list["KnowledgeSourceVersion"]] = relationship(
        "KnowledgeSourceVersion",
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="KnowledgeSourceVersion.created_at.desc()",
    )


class KnowledgeSourceVersion(Base, TimestampMixin):
    """Versioned metadata for a knowledge source."""

    __tablename__ = "knowledge_source_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_pk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="versions")
    files: Mapped[list["KnowledgeSourceFile"]] = relationship(
        "KnowledgeSourceFile",
        back_populates="source_version",
        cascade="all, delete-orphan",
        order_by="KnowledgeSourceFile.created_at.desc()",
    )


class KnowledgeSourceFile(Base, TimestampMixin):
    """Physical file metadata for a source version."""

    __tablename__ = "knowledge_source_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_scanned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ocr_used: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    extractor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    source_version: Mapped["KnowledgeSourceVersion"] = relationship(
        "KnowledgeSourceVersion",
        back_populates="files",
    )


class KnowledgeChunk(Base, TimestampMixin):
    """Normalized text chunk produced from a source version."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_source_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    heading_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)


class KnowledgeTable(Base, TimestampMixin):
    """Normalized table metadata extracted from a source version."""

    __tablename__ = "knowledge_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_source_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    schema_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)


class KnowledgeTableRow(Base, TimestampMixin):
    """Normalized structured row extracted from a knowledge table."""

    __tablename__ = "knowledge_table_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_pk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_id: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    row_order: Mapped[int] = mapped_column(Integer, nullable=False)
    row_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    track_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    basis_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)


class KnowledgeCourseCatalog(Base, TimestampMixin):
    """Normalized course catalog metadata derived from an Excel workbook."""

    __tablename__ = "knowledge_course_catalogs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_source_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    academic_year: Mapped[str | None] = mapped_column(String(50), nullable=True)
    canonical_sheet: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_sheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    glossary_sheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class KnowledgeCourse(Base, TimestampMixin):
    """Normalized course row from a course catalog workbook."""

    __tablename__ = "knowledge_courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_record_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    catalog_pk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_course_catalogs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    program_track: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    degree_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    program_variant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    semester_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    semester_label: Mapped[str] = mapped_column(String(100), nullable=False)
    course_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    course_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_course_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    course_name_aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    course_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    lecture_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discussion_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    course_design_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lab_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practice_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    self_study_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prerequisite_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisite_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    teaching_language: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)


class KnowledgeFaq(Base, TimestampMixin):
    """Normalized FAQ record."""

    __tablename__ = "knowledge_faqs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    faq_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_source_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="reviewed_faq")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published", index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class KnowledgeInteraction(Base, TimestampMixin):
    """Normalized anonymized interaction pattern."""

    __tablename__ = "knowledge_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_question_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_question_clean: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_answer_clean: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quality_label: Mapped[str] = mapped_column(String(50), nullable=False)
    contains_private_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeProcedure(Base, TimestampMixin):
    """Normalized procedure workflow template."""

    __tablename__ = "knowledge_procedures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    procedure_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    eligibility: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    required_documents: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    steps: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    contact_office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_form_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published", index=True)
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="official")


class KnowledgeForm(Base, TimestampMixin):
    """Normalized managed form template."""

    __tablename__ = "knowledge_forms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    fields: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    print_template_type: Mapped[str] = mapped_column(String(100), nullable=False, default="administrative_letter")
    related_procedure_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published", index=True)


class KnowledgeDocument(Base, TimestampMixin):
    """Top-level knowledge document/source record."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    relative_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    entries: Mapped[list["KnowledgeEntry"]] = relationship(
        "KnowledgeEntry",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeEntry.created_at",
    )


class KnowledgeEntry(Base, TimestampMixin):
    """Searchable unit derived from a knowledge document."""

    __tablename__ = "knowledge_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[KnowledgeDocument | None] = relationship("KnowledgeDocument", back_populates="entries")
