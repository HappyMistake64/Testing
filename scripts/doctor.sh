#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> FADE Doctor"
echo ""

EXIT_CODE=0

check_cmd() {
  local name="$1"
  local cmd="$2"
  if command -v "$cmd" &>/dev/null; then
    echo "[PASS] $name: $($cmd --version 2>&1 | head -1)"
  else
    echo "[FAIL] $name: $cmd not found"
    EXIT_CODE=1
  fi
}

check_cmd "Python" "python3"
check_cmd "uv" "uv"
check_cmd "Node" "node"
check_cmd "pnpm" "pnpm"

echo ""

# Python deps
if [[ -d .venv ]] || uv sync --dry-run &>/dev/null; then
  echo "[PASS] Python dependencies: resolvable"
else
  echo "[FAIL] Python dependencies: cannot resolve"
  EXIT_CODE=1
fi

# Runtime dir
mkdir -p var
if [[ -w var ]]; then
  echo "[PASS] var/ directory: writable"
else
  echo "[FAIL] var/ directory: not writable"
  EXIT_CODE=1
fi

# Migrations
if uv run alembic current &>/dev/null 2>&1 || uv run alembic upgrade head &>/dev/null; then
  echo "[PASS] Database migrations: applicable"
else
  echo "[WARN] Database migrations: not yet applied (run: uv run alembic upgrade head)"
fi

# API doctor endpoint (if API is running)
if curl -sf http://127.0.0.1:8000/api/v1/system/doctor &>/dev/null; then
  DOCTOR_STATUS=$(curl -sf http://127.0.0.1:8000/api/v1/system/doctor | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "[INFO] API doctor status: $DOCTOR_STATUS"
  if [[ "$DOCTOR_STATUS" == "fail" ]]; then
    EXIT_CODE=1
  fi
else
  echo "[INFO] API not running (start with: ./scripts/dev.sh)"
fi

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
  echo "Doctor: PASS (no blocking issues)"
else
  echo "Doctor: FAIL (blocking issues found)"
fi

exit $EXIT_CODE
