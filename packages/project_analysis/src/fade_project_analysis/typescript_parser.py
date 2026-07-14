"""TypeScript/JavaScript symbol extraction via lightweight parsing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from fade_domain.project_profile import SymbolEntry

_FUNCTION_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
    re.MULTILINE,
)
_CLASS_RE = re.compile(
    r"^(?:export\s+)?class\s+(\w+)",
    re.MULTILINE,
)
_INTERFACE_RE = re.compile(
    r"^(?:export\s+)?interface\s+(\w+)",
    re.MULTILINE,
)
_TYPE_RE = re.compile(
    r"^(?:export\s+)?type\s+(\w+)",
    re.MULTILINE,
)
_CONST_FN_RE = re.compile(
    r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class TypeScriptParseResult:
    symbols: list[SymbolEntry]
    content_hash: str


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _line_number(content: str, match_start: int) -> int:
    return content.count("\n", 0, match_start) + 1


def parse_typescript_file(file_path: Path, project_root: Path) -> TypeScriptParseResult | None:
    """Extract symbols from TypeScript/JavaScript source."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    rel = str(file_path.relative_to(project_root))
    digest = _content_hash(content)
    symbols: list[SymbolEntry] = []

    for pattern, kind in (
        (_FUNCTION_RE, "function"),
        (_CLASS_RE, "class"),
        (_INTERFACE_RE, "interface"),
        (_TYPE_RE, "type"),
        (_CONST_FN_RE, "function"),
    ):
        for match in pattern.finditer(content):
            symbols.append(SymbolEntry(
                name=match.group(1),
                kind=kind,
                file_path=rel,
                line=_line_number(content, match.start()),
                language="typescript",
                content_hash=digest,
            ))

    return TypeScriptParseResult(symbols=symbols, content_hash=digest)
