#!/usr/bin/env bash
# One-time (or repeatable) local environment bootstrap.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> FADE setup"

if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
else
  echo "==> .env already exists (skipping)"
fi

echo "==> Creating runtime directories"
mkdir -p var/{artifacts,workspaces,logs,indexes}
mkdir -p backups

echo "==> Installing Python dependencies"
uv sync --all-extras

echo "==> Installing frontend dependencies"
pnpm install

echo "==> Applying database migrations"
uv run alembic upgrade head

echo ""
echo "Setup complete. Next steps:"
echo "  ./scripts/doctor.sh       # verify environment"
echo "  ./scripts/dev.sh          # API + worker + web"
echo "  ./scripts/test.sh         # full test suite"
