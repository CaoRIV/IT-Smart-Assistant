"""knowledge normalized layer tables

Revision ID: c3d91a7f21aa
Revises: a4c7fb18c223
Create Date: 2026-03-20 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d91a7f21aa"
down_revision: Union[str, None] = "a4c7fb18c223"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("source_version_id", sa.UUID(), nullable=True),
        sa.Column("heading", sa.String(length=500), nullable=True),
        sa.Column("heading_level", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["knowledge_source_versions.id"],
            name=op.f("knowledge_chunks_source_version_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_chunks_pkey")),
    )
    op.create_index(op.f("knowledge_chunks_chunk_id_idx"), "knowledge_chunks", ["chunk_id"], unique=True)
    op.create_index(op.f("knowledge_chunks_source_version_id_idx"), "knowledge_chunks", ["source_version_id"], unique=False)
    op.create_index(op.f("knowledge_chunks_status_idx"), "knowledge_chunks", ["status"], unique=False)

    op.create_table(
        "knowledge_tables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("table_id", sa.String(length=255), nullable=False),
        sa.Column("source_version_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("schema_type", sa.String(length=100), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["knowledge_source_versions.id"],
            name=op.f("knowledge_tables_source_version_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_tables_pkey")),
    )
    op.create_index(op.f("knowledge_tables_table_id_idx"), "knowledge_tables", ["table_id"], unique=True)
    op.create_index(op.f("knowledge_tables_source_version_id_idx"), "knowledge_tables", ["source_version_id"], unique=False)
    op.create_index(op.f("knowledge_tables_schema_type_idx"), "knowledge_tables", ["schema_type"], unique=False)
    op.create_index(op.f("knowledge_tables_status_idx"), "knowledge_tables", ["status"], unique=False)

    op.create_table(
        "knowledge_table_rows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("table_pk_id", sa.UUID(), nullable=False),
        sa.Column("row_id", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=True),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("row_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("track_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("basis_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["table_pk_id"],
            ["knowledge_tables.id"],
            name=op.f("knowledge_table_rows_table_pk_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_table_rows_pkey")),
    )
    op.create_index(op.f("knowledge_table_rows_table_pk_id_idx"), "knowledge_table_rows", ["table_pk_id"], unique=False)
    op.create_index(op.f("knowledge_table_rows_status_idx"), "knowledge_table_rows", ["status"], unique=False)
    op.create_index(
        "knowledge_table_rows_table_row_key",
        "knowledge_table_rows",
        ["table_pk_id", "row_id", "row_order"],
        unique=True,
    )

    op.create_table(
        "knowledge_faqs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("faq_id", sa.String(length=255), nullable=False),
        sa.Column("source_version_id", sa.UUID(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trust_level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["knowledge_source_versions.id"],
            name=op.f("knowledge_faqs_source_version_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_faqs_pkey")),
    )
    op.create_index(op.f("knowledge_faqs_faq_id_idx"), "knowledge_faqs", ["faq_id"], unique=True)
    op.create_index(op.f("knowledge_faqs_category_idx"), "knowledge_faqs", ["category"], unique=False)
    op.create_index(op.f("knowledge_faqs_status_idx"), "knowledge_faqs", ["status"], unique=False)
    op.create_index(op.f("knowledge_faqs_source_version_id_idx"), "knowledge_faqs", ["source_version_id"], unique=False)

    op.create_table(
        "knowledge_interactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("interaction_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_question_raw", sa.Text(), nullable=True),
        sa.Column("user_question_clean", sa.Text(), nullable=False),
        sa.Column("resolved_answer_clean", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("quality_label", sa.String(length=50), nullable=False),
        sa.Column("contains_private_data", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_interactions_pkey")),
    )
    op.create_index(op.f("knowledge_interactions_interaction_id_idx"), "knowledge_interactions", ["interaction_id"], unique=True)
    op.create_index(op.f("knowledge_interactions_intent_idx"), "knowledge_interactions", ["intent"], unique=False)
    op.create_index(op.f("knowledge_interactions_category_idx"), "knowledge_interactions", ["category"], unique=False)
    op.create_index(op.f("knowledge_interactions_review_status_idx"), "knowledge_interactions", ["review_status"], unique=False)

    op.create_table(
        "knowledge_procedures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("procedure_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("eligibility", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contact_office", sa.String(length=255), nullable=True),
        sa.Column("related_form_id", sa.String(length=255), nullable=True),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("trust_level", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_procedures_pkey")),
    )
    op.create_index(op.f("knowledge_procedures_procedure_id_idx"), "knowledge_procedures", ["procedure_id"], unique=True)
    op.create_index(op.f("knowledge_procedures_category_idx"), "knowledge_procedures", ["category"], unique=False)
    op.create_index(op.f("knowledge_procedures_status_idx"), "knowledge_procedures", ["status"], unique=False)

    op.create_table(
        "knowledge_forms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("form_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("print_template_type", sa.String(length=100), nullable=False),
        sa.Column("related_procedure_id", sa.String(length=255), nullable=True),
        sa.Column("source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_forms_pkey")),
    )
    op.create_index(op.f("knowledge_forms_form_id_idx"), "knowledge_forms", ["form_id"], unique=True)
    op.create_index(op.f("knowledge_forms_category_idx"), "knowledge_forms", ["category"], unique=False)
    op.create_index(op.f("knowledge_forms_status_idx"), "knowledge_forms", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("knowledge_forms_status_idx"), table_name="knowledge_forms")
    op.drop_index(op.f("knowledge_forms_category_idx"), table_name="knowledge_forms")
    op.drop_index(op.f("knowledge_forms_form_id_idx"), table_name="knowledge_forms")
    op.drop_table("knowledge_forms")

    op.drop_index(op.f("knowledge_procedures_status_idx"), table_name="knowledge_procedures")
    op.drop_index(op.f("knowledge_procedures_category_idx"), table_name="knowledge_procedures")
    op.drop_index(op.f("knowledge_procedures_procedure_id_idx"), table_name="knowledge_procedures")
    op.drop_table("knowledge_procedures")

    op.drop_index(op.f("knowledge_interactions_review_status_idx"), table_name="knowledge_interactions")
    op.drop_index(op.f("knowledge_interactions_category_idx"), table_name="knowledge_interactions")
    op.drop_index(op.f("knowledge_interactions_intent_idx"), table_name="knowledge_interactions")
    op.drop_index(op.f("knowledge_interactions_interaction_id_idx"), table_name="knowledge_interactions")
    op.drop_table("knowledge_interactions")

    op.drop_index(op.f("knowledge_faqs_source_version_id_idx"), table_name="knowledge_faqs")
    op.drop_index(op.f("knowledge_faqs_status_idx"), table_name="knowledge_faqs")
    op.drop_index(op.f("knowledge_faqs_category_idx"), table_name="knowledge_faqs")
    op.drop_index(op.f("knowledge_faqs_faq_id_idx"), table_name="knowledge_faqs")
    op.drop_table("knowledge_faqs")

    op.drop_index("knowledge_table_rows_table_row_key", table_name="knowledge_table_rows")
    op.drop_index(op.f("knowledge_table_rows_status_idx"), table_name="knowledge_table_rows")
    op.drop_index(op.f("knowledge_table_rows_table_pk_id_idx"), table_name="knowledge_table_rows")
    op.drop_table("knowledge_table_rows")

    op.drop_index(op.f("knowledge_tables_status_idx"), table_name="knowledge_tables")
    op.drop_index(op.f("knowledge_tables_schema_type_idx"), table_name="knowledge_tables")
    op.drop_index(op.f("knowledge_tables_source_version_id_idx"), table_name="knowledge_tables")
    op.drop_index(op.f("knowledge_tables_table_id_idx"), table_name="knowledge_tables")
    op.drop_table("knowledge_tables")

    op.drop_index(op.f("knowledge_chunks_status_idx"), table_name="knowledge_chunks")
    op.drop_index(op.f("knowledge_chunks_source_version_id_idx"), table_name="knowledge_chunks")
    op.drop_index(op.f("knowledge_chunks_chunk_id_idx"), table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
