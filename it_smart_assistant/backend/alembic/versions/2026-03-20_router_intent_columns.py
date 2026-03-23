"""router intent metadata on messages

Revision ID: 8c1b4fe0e021
Revises: 2f8ab9c419d2
Create Date: 2026-03-20 04:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8c1b4fe0e021"
down_revision: str | None = "2f8ab9c419d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("router_intent", sa.String(length=50), nullable=True))
    op.add_column("messages", sa.Column("router_reason", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_messages_router_intent",
        "messages",
        ["router_intent"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_router_intent", table_name="messages")
    op.drop_column("messages", "router_reason")
    op.drop_column("messages", "router_intent")
