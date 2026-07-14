#!/usr/bin/env bash
# Security scan gate: pip-audit and npm audit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EXIT=0

echo "==> pip-audit (Python dependencies)"
if command -v uv >/dev/null 2>&1; then
  if uv run pip-audit 2>/dev/null; then
    echo "pip-audit: PASS"
  else
    echo "pip-audit: FAIL or not installed — run: uv pip install pip-audit" >&2
    EXIT=1
  fi
else
  echo "uv not found — skipping pip-audit" >&2
  EXIT=1
fi

echo "==> npm audit (frontend dependencies)"
if command -v pnpm >/dev/null 2>&1; then
  if pnpm audit --audit-level=high 2>/dev/null; then
    echo "npm audit: PASS (no high/critical)"
  else
    echo "npm audit: findings at high/critical level" >&2
    EXIT=1
  fi
else
  echo "pnpm not found — skipping npm audit" >&2
  EXIT=1
fi

if [[ $EXIT -eq 0 ]]; then
  echo "==> Security scan gate: PASS"
else
  echo "==> Security scan gate: FAIL" >&2
fi

exit $EXIT
