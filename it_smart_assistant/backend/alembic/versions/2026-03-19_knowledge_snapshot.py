"""knowledge snapshot tables

Revision ID: 9a7b2d9f8c41
Revises: c983e3bfb8d1
Create Date: 2026-03-19 21:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a7b2d9f8c41"
down_revision: Union[str, None] = "c983e3bfb8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_documents_pkey")),
    )
    op.create_index(
        op.f("knowledge_documents_external_id_idx"),
        "knowledge_documents",
        ["external_id"],
        unique=True,
    )
    op.create_index(
        op.f("knowledge_documents_category_idx"),
        "knowledge_documents",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("knowledge_documents_source_kind_idx"),
        "knowledge_documents",
        ["source_kind"],
        unique=False,
    )

    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("entry_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            name=op.f("knowledge_entries_document_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_entries_pkey")),
    )
    op.create_index(
        op.f("knowledge_entries_external_id_idx"),
        "knowledge_entries",
        ["external_id"],
        unique=True,
    )
    op.create_index(
        op.f("knowledge_entries_document_id_idx"),
        "knowledge_entries",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("knowledge_entries_category_idx"),
        "knowledge_entries",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("knowledge_entries_source_kind_idx"),
        "knowledge_entries",
        ["source_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("knowledge_entries_source_kind_idx"), table_name="knowledge_entries")
    op.drop_index(op.f("knowledge_entries_category_idx"), table_name="knowledge_entries")
    op.drop_index(op.f("knowledge_entries_document_id_idx"), table_name="knowledge_entries")
    op.drop_index(op.f("knowledge_entries_external_id_idx"), table_name="knowledge_entries")
    op.drop_table("knowledge_entries")

    op.drop_index(op.f("knowledge_documents_source_kind_idx"), table_name="knowledge_documents")
    op.drop_index(op.f("knowledge_documents_category_idx"), table_name="knowledge_documents")
    op.drop_index(op.f("knowledge_documents_external_id_idx"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
