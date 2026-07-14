"""Database migration integration tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def migrated_db(tmp_path) -> str:
    db_file = tmp_path / "migrate_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    os.environ["FADE_DATABASE_URL"] = db_url

    from fade_infrastructure.settings import get_settings

    get_settings.cache_clear()

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        env={**os.environ, "FADE_DATABASE_URL": db_url},
    )
    assert result.returncode == 0, result.stderr
    return db_url


class TestMigrations:
    @pytest.mark.asyncio
    async def test_fresh_db_upgrades_to_head(self, migrated_db: str) -> None:
        engine = create_async_engine(migrated_db)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = {row[0] for row in result}
            assert "projects" in tables
            assert "alembic_version" in tables

            integrity = await conn.execute(text("PRAGMA integrity_check"))
            assert integrity.scalar_one() == "ok"
        await engine.dispose()

    def test_migration_is_repeatable(self, tmp_path) -> None:
        db_file = tmp_path / "repeat.db"
        db_url = f"sqlite+aiosqlite:///{db_file}"
        cwd = Path(__file__).resolve().parents[2]
        env = {**os.environ, "FADE_DATABASE_URL": db_url}

        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
            )
            assert result.returncode == 0, result.stderr
