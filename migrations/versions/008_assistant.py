"""Migration 008: assistant sessions, turns, approvals, memory, integrations, automations.

Revision ID: 008_assistant
Revises: 007_policies
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_assistant"
down_revision: str | None = "007_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_sessions",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("provider_id", sa.String(length=64), nullable=True),
        sa.Column("model_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "assistant_turns",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("session_id", sa.String(length=26), nullable=False),
        sa.Column("job_id", sa.String(length=26), nullable=True),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="answer"),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=True),
        sa.Column("model_id", sa.String(length=128), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("tool_calls_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_turns_session_id", "assistant_turns", ["session_id"])
    op.create_index("ix_assistant_turns_job_id", "assistant_turns", ["job_id"])
    op.create_index("ix_assistant_turns_state", "assistant_turns", ["state"])

    op.create_table(
        "tool_approvals",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("turn_id", sa.String(length=26), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("normalized_args_hash", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=False),
        sa.Column("args_preview", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_approvals_turn_id", "tool_approvals", ["turn_id"])

    op.create_table(
        "memory_items",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_turn_id", sa.String(length=26), nullable=True),
        sa.Column(
            "confidence", sa.String(length=32), nullable=False, server_default="user_stated"
        ),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "integration_accounts",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="disconnected"),
        sa.Column("scopes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("allow_entities_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
    )

    op.create_table(
        "automations",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("schedule_kind", sa.String(length=32), nullable=False, server_default="once"),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "assistant_controls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Full-text search over memory content (SQLite FTS5).
    op.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(memory_id, content)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_fts")
    op.drop_table("assistant_controls")
    op.drop_table("automations")
    op.drop_table("integration_accounts")
    op.drop_table("memory_items")
    op.drop_index("ix_tool_approvals_turn_id", table_name="tool_approvals")
    op.drop_table("tool_approvals")
    op.drop_index("ix_assistant_turns_state", table_name="assistant_turns")
    op.drop_index("ix_assistant_turns_job_id", table_name="assistant_turns")
    op.drop_index("ix_assistant_turns_session_id", table_name="assistant_turns")
    op.drop_table("assistant_turns")
    op.drop_table("assistant_sessions")
