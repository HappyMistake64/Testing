"""Settings unit tests."""

from __future__ import annotations

from fade_infrastructure.settings import Settings


class TestSettings:
    def test_redacted_dict_hides_database_url(self) -> None:
        settings = Settings(database_url="sqlite+aiosqlite:///./var/fade.db")
        redacted = settings.redacted_dict()
        assert redacted["database_url"] == "***REDACTED***"

    def test_redacted_dict_shows_safe_values(self) -> None:
        settings = Settings(env="test", version="0.1.0")
        redacted = settings.redacted_dict()
        assert redacted["env"] == "test"
        assert redacted["version"] == "0.1.0"

    def test_db_path_from_sqlite_url(self) -> None:
        settings = Settings(database_url="sqlite+aiosqlite:///./var/fade.db")
        assert settings.db_path == settings.db_path.__class__("var/fade.db")
