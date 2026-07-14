"""Tests for named pilot fixture materialization."""

from __future__ import annotations

from tests.fixtures.pilot_repo import materialize_named_pilot_repo


def test_materialize_neurostring_fixture(tmp_path) -> None:
    repo = materialize_named_pilot_repo(tmp_path / "neurostring", "neurostring")
    assert (repo / "fade-manifest.yaml").is_file()
    assert (repo / "src" / "pilot_app" / "main.py").is_file()
    assert "neurostring-pilot" in (repo / "fade-manifest.yaml").read_text(encoding="utf-8")


def test_materialize_tradepilot_fixture(tmp_path) -> None:
    repo = materialize_named_pilot_repo(tmp_path / "tradepilot", "tradepilot")
    assert (repo / "fade-manifest.yaml").is_file()
    manifest = (repo / "fade-manifest.yaml").read_text(encoding="utf-8")
    assert "tradepilot-pilot" in manifest
    assert "paper_trading" in manifest
