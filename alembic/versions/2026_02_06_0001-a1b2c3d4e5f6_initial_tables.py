"""Initial tables: tasks, agent_logs, decisions

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-06 00:00:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision tanimlayicilari (Alembic tarafindan kullanilir)
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """tasks, agent_logs ve decisions tablolarini olusturur."""
    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("agent", sa.String(100), nullable=True),
        sa.Column("risk", sa.String(20), nullable=True),
        sa.Column("urgency", sa.String(20), nullable=True),
        sa.Column("result_message", sa.Text(), nullable=True),
        sa.Column("result_success", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    # --- agent_logs ---
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_logs_agent_name", "agent_logs", ["agent_name"])
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])

    # --- decisions ---
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("risk", sa.String(20), nullable=False),
        sa.Column("urgency", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_decisions_task_id", "decisions", ["task_id"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])


def downgrade() -> None:
    """Tum tablolari kaldirir."""
    op.drop_index("ix_decisions_created_at", table_name="decisions")
    op.drop_index("ix_decisions_task_id", table_name="decisions")
    op.drop_table("decisions")

    op.drop_index("ix_agent_logs_created_at", table_name="agent_logs")
    op.drop_index("ix_agent_logs_agent_name", table_name="agent_logs")
    op.drop_table("agent_logs")

    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_table("tasks")
