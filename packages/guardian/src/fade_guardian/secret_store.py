"""Secret detection and redaction."""

from __future__ import annotations

import re
from re import Pattern

_SECRET_PATTERNS: list[tuple[str, Pattern[str]]] = [
    (
        "OPENAI_API_KEY",
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ),
    (
        "AWS_ACCESS_KEY",
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    (
        "GENERIC_API_KEY",
        re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    ),
    (
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "BEARER_TOKEN",
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    ),
]

REDACTION = "***REDACTED***"


class SecretStore:
    """Detects and redacts secrets from text."""

    def __init__(self, extra_patterns: list[tuple[str, Pattern[str]]] | None = None) -> None:
        self._patterns = list(_SECRET_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def contains_secret(self, text: str) -> bool:
        return any(pattern.search(text) for _, pattern in self._patterns)

    def redact(self, text: str) -> str:
        result = text
        for name, pattern in self._patterns:
            result = pattern.sub(f"{REDACTION}<{name}>", result)
        return result

    def scan_paths(self, paths: list[str]) -> list[str]:
        """Return paths that look like secret files (by name only)."""
        sensitive_names = {".env", "id_rsa", "credentials.json", "secrets.yaml", ".npmrc"}
        flagged: list[str] = []
        for path in paths:
            parts = {part.lower() for part in path.replace("\\", "/").split("/")}
            if parts & sensitive_names:
                flagged.append(path)
        return flagged
