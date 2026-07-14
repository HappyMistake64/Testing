"""Project profiles and symbol index tables.

Revision ID: 003_project_profiles
Revises: 002_project_m1_fields
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_project_profiles"
down_revision: str | None = "002_project_m1_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_profiles",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.String(length=64), nullable=True),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_profiles_project_id", "project_profiles", ["project_id"])

    op.create_table(
        "symbol_index",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("project_id", sa.String(length=26), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symbol_index_project_id", "symbol_index", ["project_id"])
    op.create_index("ix_symbol_index_name", "symbol_index", ["name"])


def downgrade() -> None:
    op.drop_index("ix_symbol_index_name", table_name="symbol_index")
    op.drop_index("ix_symbol_index_project_id", table_name="symbol_index")
    op.drop_table("symbol_index")
    op.drop_index("ix_project_profiles_project_id", table_name="project_profiles")
    op.drop_table("project_profiles")
