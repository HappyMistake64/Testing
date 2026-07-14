"""Path safety unit tests."""

from __future__ import annotations

import pytest
from fade_infrastructure.path_safety import PathSafetyError, PathSafetyService
from fade_infrastructure.settings import Settings


class TestPathSafety:
    def test_rejects_nonexistent_path(self, tmp_path) -> None:
        service = PathSafetyService(Settings())
        with pytest.raises(PathSafetyError) as exc:
            service.validate_and_resolve(str(tmp_path / "missing"))
        assert exc.value.code == "PROJECT_PATH_NOT_FOUND"

    def test_resolves_valid_directory(self, tmp_path) -> None:
        project = tmp_path / "myproject"
        project.mkdir()
        service = PathSafetyService(Settings(project_allowed_roots=str(tmp_path)))
        resolved = service.validate_and_resolve(str(project))
        assert resolved == project.resolve()

    def test_rejects_path_outside_allowed_roots(self, tmp_path) -> None:
        allowed = tmp_path / "allowed"
        outside = tmp_path / "outside"
        allowed.mkdir()
        outside.mkdir()
        service = PathSafetyService(Settings(project_allowed_roots=str(allowed)))
        with pytest.raises(PathSafetyError) as exc:
            service.validate_and_resolve(str(outside))
        assert exc.value.code == "PROJECT_PATH_NOT_ALLOWED"

    def test_rejects_symlink_escape(self, tmp_path) -> None:
        allowed = tmp_path / "allowed"
        outside = tmp_path / "outside"
        allowed.mkdir()
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        link = allowed / "escape"
        link.symlink_to(outside)

        service = PathSafetyService(Settings(project_allowed_roots=str(allowed)))
        with pytest.raises(PathSafetyError) as exc:
            service.validate_and_resolve(str(link))
        assert exc.value.code in ("PROJECT_PATH_SYMLINK_ESCAPE", "PROJECT_PATH_NOT_ALLOWED")
