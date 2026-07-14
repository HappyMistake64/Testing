#!/usr/bin/env bash
# Package FADE platform release archive.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${FADE_VERSION:-$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")}"
DIST_DIR="$ROOT/dist"
ARCHIVE="$DIST_DIR/fade-platform-$VERSION.tar.gz"

mkdir -p "$DIST_DIR"

echo "==> Building frontend"
pnpm --filter @fade/web build

echo "==> Creating release archive"
tar -czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.venv' \
  --exclude='var' \
  --exclude='backups' \
  --exclude='dist' \
  -C "$ROOT" \
  apps packages migrations scripts pyproject.toml pnpm-lock.yaml pnpm-workspace.yaml package.json README.md docs .env.example

echo "Release package: $ARCHIVE"
shasum -a 256 "$ARCHIVE" > "$ARCHIVE.sha256"
cat "$ARCHIVE.sha256"
