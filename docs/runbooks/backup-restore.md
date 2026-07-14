# Backup and Restore Runbook

## Backup

Create a timestamped archive of `var/fade.db` and the `var/` directory:

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

Backups are stored in `backups/fade-backup-<timestamp>.tar.gz`.

Retention is controlled by `FADE_BACKUP_RETENTION_COUNT` (default: 7).

## Restore

1. Stop the API and any workers.
2. Move current state aside:

```bash
mv var var.bak.$(date +%s)
mkdir -p var
```

3. Extract backup:

```bash
tar -xzf backups/fade-backup-<timestamp>.tar.gz -C .
```

4. Verify integrity:

```bash
uv run python -c "
import sqlite3
c = sqlite3.connect('var/fade.db')
print('integrity:', c.execute('PRAGMA integrity_check').fetchone()[0])
"
```

5. Run migrations to head (idempotent):

```bash
uv run alembic upgrade head
```

6. Start platform: `./scripts/dev.sh`

## Scheduled backups

For local development, add a cron entry:

```
0 2 * * * cd /path/to/fade-platform && ./scripts/backup.sh
```

## What is included

| Path | Contents |
|------|----------|
| `var/fade.db` | Project registry, profiles, goals, plans, jobs, policies |
| `var/` | Runtime artifacts, workspaces (if present) |

Source managed projects are **not** backed up — they remain in their original locations.
