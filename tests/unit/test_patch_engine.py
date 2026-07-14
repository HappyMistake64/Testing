"""Patch engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fade_patch_engine.patch import PatchEngine, PatchEngineError, PatchHunk, FileOperation, file_hash


class TestPatchEngine:
    def test_apply_with_valid_base_hash(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        target = ws / "app.py"
        target.write_text("old\n", encoding="utf-8")
        engine = PatchEngine(ws)
        result = engine.apply_hunks([
            PatchHunk(
                path="app.py",
                base_hash=file_hash("old\n"),
                operations=[
                    FileOperation(path="app.py", old_content="old\n", new_content="new\n"),
                ],
            ),
        ])
        assert "app.py" in result.applied_files
        assert target.read_text(encoding="utf-8") == "new\n"

    def test_reject_base_hash_mismatch(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "app.py").write_text("changed\n", encoding="utf-8")
        engine = PatchEngine(ws)
        with pytest.raises(PatchEngineError) as exc:
            engine.apply_hunks([
                PatchHunk(
                    path="app.py",
                    base_hash=file_hash("old\n"),
                    operations=[
                        FileOperation(path="app.py", old_content=None, new_content="new\n"),
                    ],
                ),
            ])
        assert exc.value.code == "BASE_HASH_MISMATCH"
