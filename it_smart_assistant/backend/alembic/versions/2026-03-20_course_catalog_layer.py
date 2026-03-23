"""course catalog normalized tables

Revision ID: e1b7c9a12f44
Revises: c3d91a7f21aa
Create Date: 2026-03-20 22:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1b7c9a12f44"
down_revision: Union[str, None] = "c3d91a7f21aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_course_catalogs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("catalog_id", sa.String(length=255), nullable=False),
        sa.Column("source_version_id", sa.UUID(), nullable=True),
        sa.Column("program_name", sa.String(length=255), nullable=False),
        sa.Column("program_code", sa.String(length=100), nullable=True),
        sa.Column("academic_year", sa.String(length=50), nullable=True),
        sa.Column("canonical_sheet", sa.String(length=255), nullable=False),
        sa.Column("summary_sheet", sa.String(length=255), nullable=True),
        sa.Column("glossary_sheet", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["knowledge_source_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_course_catalogs_catalog_id",
        "knowledge_course_catalogs",
        ["catalog_id"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_course_catalogs_source_version_id",
        "knowledge_course_catalogs",
        ["source_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_course_catalogs_status",
        "knowledge_course_catalogs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "knowledge_courses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_record_id", sa.String(length=255), nullable=False),
        sa.Column("catalog_pk_id", sa.UUID(), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("program_track", sa.String(length=50), nullable=False),
        sa.Column("degree_level", sa.String(length=50), nullable=True),
        sa.Column("program_variant", sa.String(length=100), nullable=True),
        sa.Column("semester_number", sa.Integer(), nullable=True),
        sa.Column("semester_label", sa.String(length=100), nullable=False),
        sa.Column("course_order", sa.Integer(), nullable=True),
        sa.Column("course_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_course_name", sa.String(length=500), nullable=False),
        sa.Column("course_name_aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("course_code", sa.String(length=100), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("lecture_hours", sa.Integer(), nullable=True),
        sa.Column("discussion_hours", sa.Integer(), nullable=True),
        sa.Column("course_design_hours", sa.Integer(), nullable=True),
        sa.Column("project_hours", sa.Integer(), nullable=True),
        sa.Column("lab_hours", sa.Integer(), nullable=True),
        sa.Column("practice_hours", sa.Integer(), nullable=True),
        sa.Column("self_study_hours", sa.Integer(), nullable=True),
        sa.Column("prerequisite_text", sa.Text(), nullable=True),
        sa.Column("prerequisite_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("teaching_language", sa.String(length=50), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("raw_row_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["catalog_pk_id"],
            ["knowledge_course_catalogs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_courses_course_record_id", "knowledge_courses", ["course_record_id"], unique=True)
    op.create_index("ix_knowledge_courses_catalog_pk_id", "knowledge_courses", ["catalog_pk_id"], unique=False)
    op.create_index("ix_knowledge_courses_program_track", "knowledge_courses", ["program_track"], unique=False)
    op.create_index("ix_knowledge_courses_semester_number", "knowledge_courses", ["semester_number"], unique=False)
    op.create_index("ix_knowledge_courses_normalized_course_name", "knowledge_courses", ["normalized_course_name"], unique=False)
    op.create_index("ix_knowledge_courses_course_code", "knowledge_courses", ["course_code"], unique=False)
    op.create_index("ix_knowledge_courses_teaching_language", "knowledge_courses", ["teaching_language"], unique=False)
    op.create_index("ix_knowledge_courses_status", "knowledge_courses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_courses_status", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_teaching_language", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_course_code", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_normalized_course_name", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_semester_number", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_program_track", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_catalog_pk_id", table_name="knowledge_courses")
    op.drop_index("ix_knowledge_courses_course_record_id", table_name="knowledge_courses")
    op.drop_table("knowledge_courses")

    op.drop_index("ix_knowledge_course_catalogs_status", table_name="knowledge_course_catalogs")
    op.drop_index("ix_knowledge_course_catalogs_source_version_id", table_name="knowledge_course_catalogs")
    op.drop_index("ix_knowledge_course_catalogs_catalog_id", table_name="knowledge_course_catalogs")
    op.drop_table("knowledge_course_catalogs")
