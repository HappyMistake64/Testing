#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> FADE dev environment"

# Ensure runtime directories
mkdir -p var/{artifacts,workspaces,logs,indexes}
mkdir -p backups

# Install Python dependencies if needed
if [[ ! -d .venv ]]; then
  echo "==> Creating Python virtual environment with uv"
  uv sync --all-extras
fi

# Run migrations
echo "==> Running database migrations"
uv run alembic upgrade head

# Install frontend dependencies if needed
if [[ ! -d apps/web/node_modules ]]; then
  echo "==> Installing frontend dependencies"
  pnpm install
fi

echo "==> Starting API (port 8000), worker, and Web (port 5173)"
trap 'kill 0' EXIT

uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload &
uv run python workers/local_worker.py &
pnpm --filter @fade/web dev &

wait
