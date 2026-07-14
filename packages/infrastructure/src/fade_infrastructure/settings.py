"""Application settings with environment override and redacted diagnostics."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_SENSITIVE_KEYS = frozenset({"password", "secret", "token", "api_key", "database_url"})


class Settings(BaseSettings):
    """FADE platform configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FADE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="127.0.0.1", description="API bind host")
    port: int = Field(default=8000, description="API bind port")
    version: str = Field(default="0.1.0", description="Platform version")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./var/fade.db",
        description="SQLAlchemy database URL",
    )

    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")

    project_allowed_roots: str = Field(
        default="",
        description="Comma-separated allowed roots for project sources (empty = permissive)",
    )
    preflight_max_files: int = Field(default=50_000, description="Max files in preflight scan")
    preflight_max_bytes: int = Field(
        default=2_000_000_000,
        description="Max total bytes in preflight scan",
    )

    # Placeholder for future secret store integration
    openai_api_key: SecretStr | None = Field(default=None, description="Optional cloud API key")

    @property
    def var_dir(self) -> Path:
        return Path("var")

    @property
    def allowed_project_roots(self) -> list[str]:
        if not self.project_allowed_roots.strip():
            return []
        return [r.strip() for r in self.project_allowed_roots.split(",") if r.strip()]

    @property
    def db_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite"):
            # sqlite+aiosqlite:///./var/fade.db -> var/fade.db
            path_part = url.split("///", 1)[-1]
            return Path(path_part)
        return Path("var/fade.db")

    def redacted_dict(self) -> dict[str, Any]:
        """Return settings as dict with sensitive values redacted."""
        data: dict[str, Any] = {}
        for key, value in self.model_dump().items():
            if any(s in key.lower() for s in _SENSITIVE_KEYS):
                data[key] = "***REDACTED***"
            elif isinstance(value, SecretStr):
                data[key] = "***REDACTED***" if value.get_secret_value() else None
            else:
                data[key] = value
        return data


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
