"""Goals, plans, and approvals tables.

Revision ID: 005_goals_plans
Revises: 004_jobs_evidence
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_goals_plans"
down_revision: str | None = "004_jobs_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("constraints_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
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
    op.create_index("ix_goals_project_id", "goals", ["project_id"])

    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("goal_id", sa.String(length=26), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_goal_id", "plans", ["goal_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=26), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_subject_id", "approvals", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_approvals_subject_id", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_plans_goal_id", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_goals_project_id", table_name="goals")
    op.drop_table("goals")
