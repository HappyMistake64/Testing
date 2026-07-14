#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> FADE test suite"

mkdir -p var

# Backend
echo "==> Backend: unit + integration tests"
uv run pytest tests/ -v --tb=short

# Frontend
echo "==> Frontend: component tests"
pnpm --filter @fade/web test

# Typecheck
echo "==> Frontend: typecheck"
pnpm --filter @fade/web typecheck

# Build
echo "==> Frontend: production build"
pnpm --filter @fade/web build

# Lint
echo "==> Backend: ruff"
uv run ruff check apps packages tests workers migrations

echo "==> All tests passed"
