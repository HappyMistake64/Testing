#!/usr/bin/env bash
# Backup fade.db and var/ directory for disaster recovery.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${FADE_BACKUP_DIR:-$ROOT/backups}"
ARCHIVE="$BACKUP_DIR/fade-backup-$TIMESTAMP.tar.gz"
RETENTION="${FADE_BACKUP_RETENTION_COUNT:-7}"

mkdir -p "$BACKUP_DIR" var

if [[ ! -f var/fade.db ]]; then
  echo "Warning: var/fade.db not found — backing up var/ only" >&2
fi

tar -czf "$ARCHIVE" -C "$ROOT" var/fade.db var 2>/dev/null || \
  tar -czf "$ARCHIVE" -C "$ROOT" var

echo "Backup created: $ARCHIVE"

# Prune old backups
mapfile -t OLD < <(ls -1t "$BACKUP_DIR"/fade-backup-*.tar.gz 2>/dev/null | tail -n +$((RETENTION + 1)) || true)
for f in "${OLD[@]}"; do
  rm -f "$f"
  echo "Pruned old backup: $f"
done
