"""Database upgrade/migration integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def alembic_cfg(tmp_path: Path) -> Config:
    db_path = tmp_path / "upgrade.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    os.environ["FADE_DATABASE_URL"] = db_url
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


class TestUpgrade:
    def test_fresh_db_upgrades_to_head(self, alembic_cfg: Config) -> None:
        command.upgrade(alembic_cfg, "head")
        url = alembic_cfg.get_main_option("sqlalchemy.url")
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert "projects" in tables
        assert "project_profiles" in tables
        assert "goals" in tables
        assert "plans" in tables
        assert "jobs" in tables
        assert "job_events" in tables
        assert "policies" in tables

        with engine.connect() as conn:
            integrity = conn.execute(text("PRAGMA integrity_check")).scalar()
        assert integrity == "ok"

    def test_upgrade_is_idempotent(self, alembic_cfg: Config) -> None:
        command.upgrade(alembic_cfg, "head")
        command.upgrade(alembic_cfg, "head")
        url = alembic_cfg.get_main_option("sqlalchemy.url")
        engine = create_engine(url)
        with engine.connect() as conn:
            integrity = conn.execute(text("PRAGMA integrity_check")).scalar()
        assert integrity == "ok"
