"""Extend projects table for Milestone 1.

Revision ID: 002_project_m1_fields
Revises: 001_initial_projects
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_project_m1_fields"
down_revision: str | None = "001_initial_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("default_branch", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("preflight_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("archived_at")
        batch_op.drop_column("preflight_json")
        batch_op.drop_column("tags")
        batch_op.drop_column("default_branch")
