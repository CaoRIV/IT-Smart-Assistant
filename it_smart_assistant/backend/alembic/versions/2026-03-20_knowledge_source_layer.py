"""knowledge source layer tables

Revision ID: a4c7fb18c223
Revises: 8c1b4fe0e021
Create Date: 2026-03-20 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a4c7fb18c223"
down_revision: Union[str, None] = "8c1b4fe0e021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("source_office", sa.String(length=255), nullable=True),
        sa.Column("trust_level", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("current_status", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_sources_pkey")),
    )
    op.create_index(op.f("knowledge_sources_source_id_idx"), "knowledge_sources", ["source_id"], unique=True)
    op.create_index(op.f("knowledge_sources_source_type_idx"), "knowledge_sources", ["source_type"], unique=False)
    op.create_index(op.f("knowledge_sources_category_idx"), "knowledge_sources", ["category"], unique=False)
    op.create_index(op.f("knowledge_sources_current_status_idx"), "knowledge_sources", ["current_status"], unique=False)

    op.create_table(
        "knowledge_source_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_pk_id", sa.UUID(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_pk_id"],
            ["knowledge_sources.id"],
            name=op.f("knowledge_source_versions_source_pk_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_source_versions_pkey")),
    )
    op.create_index(op.f("knowledge_source_versions_source_pk_id_idx"), "knowledge_source_versions", ["source_pk_id"], unique=False)
    op.create_index(op.f("knowledge_source_versions_status_idx"), "knowledge_source_versions", ["status"], unique=False)
    op.create_index(op.f("knowledge_source_versions_is_active_idx"), "knowledge_source_versions", ["is_active"], unique=False)

    op.create_table(
        "knowledge_source_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_version_id", sa.UUID(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("storage_backend", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("is_scanned", sa.Boolean(), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), nullable=True),
        sa.Column("extractor", sa.String(length=100), nullable=True),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["knowledge_source_versions.id"],
            name=op.f("knowledge_source_files_source_version_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_source_files_pkey")),
    )
    op.create_index(op.f("knowledge_source_files_source_version_id_idx"), "knowledge_source_files", ["source_version_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("knowledge_source_files_source_version_id_idx"), table_name="knowledge_source_files")
    op.drop_table("knowledge_source_files")

    op.drop_index(op.f("knowledge_source_versions_is_active_idx"), table_name="knowledge_source_versions")
    op.drop_index(op.f("knowledge_source_versions_status_idx"), table_name="knowledge_source_versions")
    op.drop_index(op.f("knowledge_source_versions_source_pk_id_idx"), table_name="knowledge_source_versions")
    op.drop_table("knowledge_source_versions")

    op.drop_index(op.f("knowledge_sources_current_status_idx"), table_name="knowledge_sources")
    op.drop_index(op.f("knowledge_sources_category_idx"), table_name="knowledge_sources")
    op.drop_index(op.f("knowledge_sources_source_type_idx"), table_name="knowledge_sources")
    op.drop_index(op.f("knowledge_sources_source_id_idx"), table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
