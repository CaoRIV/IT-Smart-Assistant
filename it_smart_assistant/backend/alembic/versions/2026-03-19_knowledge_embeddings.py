"""knowledge entry embeddings

Revision ID: 2d42a0d9e6bf
Revises: 9a7b2d9f8c41
Create Date: 2026-03-19 22:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2d42a0d9e6bf"
down_revision: Union[str, None] = "9a7b2d9f8c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("knowledge_entries", sa.Column("embedding_model", sa.String(length=100), nullable=True))
    op.add_column(
        "knowledge_entries",
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("ALTER TABLE knowledge_entries ADD COLUMN embedding vector(1536)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS knowledge_entries_embedding_idx
        ON knowledge_entries
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS knowledge_entries_embedding_idx")
    op.execute("ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS embedding")
    op.drop_column("knowledge_entries", "embedding_updated_at")
    op.drop_column("knowledge_entries", "embedding_model")
