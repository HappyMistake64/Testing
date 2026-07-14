"""Python source symbol extraction via AST."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path

from fade_domain.project_profile import SymbolEntry


@dataclass(frozen=True, slots=True)
class PythonParseResult:
    symbols: list[SymbolEntry]
    content_hash: str


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_python_file(file_path: Path, project_root: Path) -> PythonParseResult | None:
    """Extract top-level symbols from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    rel = str(file_path.relative_to(project_root))
    digest = _content_hash(content)

    try:
        tree = ast.parse(content, filename=rel)
    except SyntaxError:
        return PythonParseResult(symbols=[], content_hash=digest)

    symbols: list[SymbolEntry] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.append(SymbolEntry(
                name=node.name,
                kind="function",
                file_path=rel,
                line=node.lineno,
                language="python",
                content_hash=digest,
            ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(SymbolEntry(
                name=node.name,
                kind="class",
                file_path=rel,
                line=node.lineno,
                language="python",
                content_hash=digest,
            ))

    return PythonParseResult(symbols=symbols, content_hash=digest)
