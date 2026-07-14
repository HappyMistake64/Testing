"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from fade_infrastructure.database import Base


class ProjectModel(Base):
    """Registered managed project."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="local_git")
    source_location: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    preflight_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
