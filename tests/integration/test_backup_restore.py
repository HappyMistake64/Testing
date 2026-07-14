"""Backup and restore integration tests."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import tarfile
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "fade"
    var_dir = root / "var"
    var_dir.mkdir(parents=True)
    db = var_dir / "fade.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE backup_marker (id INTEGER PRIMARY KEY, note TEXT)")
    conn.execute("INSERT INTO backup_marker (note) VALUES ('pre-backup')")
    conn.commit()
    conn.close()
    (var_dir / "artifacts").mkdir()
    (var_dir / "artifacts" / "sample.txt").write_text("artifact", encoding="utf-8")
    return root


class TestBackupRestore:
    def test_backup_and_restore_roundtrip(self, workspace: Path) -> None:
        backup_dir = workspace / "backups"
        backup_dir.mkdir()
        archive = backup_dir / "fade-backup-test.tar.gz"

        with tarfile.open(archive, "w:gz") as tar:
            tar.add(workspace / "var" / "fade.db", arcname="var/fade.db")
            tar.add(workspace / "var" / "artifacts", arcname="var/artifacts")

        assert archive.exists()

        # Simulate restore
        restore_root = workspace / "restored"
        restore_root.mkdir()
        (restore_root / "var").mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(restore_root, filter="data")

        restored_db = restore_root / "var" / "fade.db"
        conn = sqlite3.connect(restored_db)
        row = conn.execute("SELECT note FROM backup_marker").fetchone()
        conn.close()
        assert row[0] == "pre-backup"
        assert (restore_root / "var" / "artifacts" / "sample.txt").read_text() == "artifact"

    def test_backup_script_creates_archive(self, tmp_path: Path) -> None:
        root = tmp_path / "platform"
        src = Path(__file__).resolve().parents[2]
        ignore = shutil.ignore_patterns(".git", "node_modules", "var", "backups")
        shutil.copytree(src, root, ignore=ignore)
        var_dir = root / "var"
        var_dir.mkdir()
        (var_dir / "fade.db").write_bytes(b"")
        env = {**os.environ, "FADE_BACKUP_DIR": str(root / "backups")}
        result = subprocess.run(
            ["bash", str(root / "scripts" / "backup.sh")],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        backups = list((root / "backups").glob("fade-backup-*.tar.gz"))
        assert len(backups) == 1
