"""message feedback table

Revision ID: 2f8ab9c419d2
Revises: 2d42a0d9e6bf
Create Date: 2026-03-20 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f8ab9c419d2"
down_revision: Union[str, None] = "2d42a0d9e6bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], name=op.f("message_feedback_message_id_fkey"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("message_feedback_user_id_fkey"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("message_feedback_pkey")),
        sa.UniqueConstraint("message_id", "user_id", name="message_feedback_message_user_key"),
    )
    op.create_index(op.f("message_feedback_message_id_idx"), "message_feedback", ["message_id"], unique=False)
    op.create_index(op.f("message_feedback_user_id_idx"), "message_feedback", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("message_feedback_user_id_idx"), table_name="message_feedback")
    op.drop_index(op.f("message_feedback_message_id_idx"), table_name="message_feedback")
    op.drop_table("message_feedback")
