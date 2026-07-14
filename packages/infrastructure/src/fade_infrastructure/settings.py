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

    # Resource budgets (M9)
    max_concurrent_heavy_jobs: int = Field(
        default=1,
        description="Max concurrent heavy jobs on constrained hardware",
    )
    max_concurrent_light_jobs: int = Field(
        default=2,
        description="Max concurrent light/read-only jobs",
    )
    artifact_retention_days: int = Field(
        default=30,
        description="Days to retain job artifacts before cleanup",
    )
    max_artifact_storage_mb: int = Field(
        default=2048,
        description="Soft cap for artifact storage in MB",
    )
    backup_retention_count: int = Field(
        default=7,
        description="Number of backup archives to retain",
    )

    # Placeholder for future secret store integration
    openai_api_key: SecretStr | None = Field(default=None, description="Optional cloud API key")
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama HTTP API base URL",
    )
    ollama_default_model: str = Field(
        default="llama3.2",
        description="Default Ollama model id",
    )

    @property
    def var_dir(self) -> Path:
        return Path("var")

    @property
    def workspaces_dir(self) -> Path:
        path = self.var_dir / "workspaces"
        path.mkdir(parents=True, exist_ok=True)
        return path

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
