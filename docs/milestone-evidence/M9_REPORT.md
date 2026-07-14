# Milestone 9 — Production Candidate Report

**Date:** 2026-07-14  
**Branch:** cursor/fade-platform-m2-m9-3637  
**Status:** PASS

## Deliverables

| Item | Location | Status |
|------|----------|--------|
| Resource budgets | `packages/infrastructure/src/fade_infrastructure/settings.py` | PASS |
| Backup script | `scripts/backup.sh` | PASS |
| Security scan gate | `scripts/security-scan.sh` | PASS |
| Release packaging | `scripts/package-release.sh` | PASS |
| Troubleshooting runbook | `docs/runbooks/troubleshooting.md` | PASS |
| Backup/restore runbook | `docs/runbooks/backup-restore.md` | PASS |
| Backup/restore tests | `tests/integration/test_backup_restore.py` | PASS |
| Upgrade tests | `tests/integration/test_upgrade.py` | PASS |

## Resource Budgets (defaults)

| Setting | Default | Purpose |
|---------|---------|---------|
| `FADE_MAX_CONCURRENT_HEAVY_JOBS` | 1 | 8 GB RAM constraint |
| `FADE_MAX_CONCURRENT_LIGHT_JOBS` | 2 | Parallel read-only work |
| `FADE_ARTIFACT_RETENTION_DAYS` | 30 | Artifact cleanup |
| `FADE_MAX_ARTIFACT_STORAGE_MB` | 2048 | Disk soft cap |
| `FADE_BACKUP_RETENTION_COUNT` | 7 | Backup rotation |

Doctor endpoint exposes `resource_budgets` in diagnostics.

## Release Gate Checklist

- [x] Backup and restore tested
- [x] Migration upgrade path verified
- [x] Security scan script present
- [x] Release packaging script present
- [x] Runbooks documented
- [x] Known limitations documented in troubleshooting runbook

## Known Limitations

- Single-node SQLite; no horizontal scaling
- Job worker is in-process simulation for pilot scope
- Real-project pilots (NeuroString, TradePilot) require owner paths

## Exit Gate

**PASS** — Production candidate artifacts complete for local deployment.
