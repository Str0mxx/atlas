"""Add notifications table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-08 00:00:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision tanimlayicilari (Alembic tarafindan kullanilir)
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """notifications tablosunu olusturur."""
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column(
            "priority", sa.String(20), nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="pending",
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("recipient", sa.String(200), nullable=True),
        sa.Column(
            "channel", sa.String(20), nullable=False,
            server_default="telegram",
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_notifications_task_id", "notifications", ["task_id"],
    )
    op.create_index(
        "ix_notifications_event_type", "notifications", ["event_type"],
    )
    op.create_index(
        "ix_notifications_created_at", "notifications", ["created_at"],
    )


def downgrade() -> None:
    """notifications tablosunu kaldirir."""
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_event_type", table_name="notifications")
    op.drop_index("ix_notifications_task_id", table_name="notifications")
    op.drop_table("notifications")
