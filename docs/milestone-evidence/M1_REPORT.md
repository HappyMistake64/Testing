# Milestone 1 Evidence Report

**Date**: 2026-07-14  
**Milestone**: M1 — Project Registry and Preflight  
**Status**: Complete

## Deliverables Checklist

### M1-E1 Project CRUD
- [x] Project domain entity and repository port
- [x] SQLAlchemy repository
- [x] List, get, register, patch metadata, archive API
- [x] Idempotent registration by source path

### M1-E2 Source and path safety
- [x] `FADE_PROJECT_ALLOWED_ROOTS` configuration
- [x] Canonical path resolution and symlink containment
- [x] Filesystem-based Git repo detection
- [x] Non-Git projects fail preflight with explicit error

### M1-E3 Preflight pipeline
- [x] File count and size inventory with limits
- [x] Git branch/revision from `.git/HEAD` (no subprocess)
- [x] Manifest detection (pyproject.toml, package.json, etc.)
- [x] Sensitive filename scan (names only, no content read)
- [x] Preflight status: pass/warn/fail with issues list

### M1-E4 UI
- [x] Portfolio dashboard with project cards
- [x] Add Project wizard with preflight progress
- [x] Project detail page with preflight summary
- [x] Archive action

## API Endpoints Added

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/projects` | Register + preflight |
| GET | `/api/v1/projects/{id}` | Project detail |
| PATCH | `/api/v1/projects/{id}` | Update metadata |
| POST | `/api/v1/projects/{id}/archive` | Archive project |

## Test Results

```
Backend:  33 passed (unit + integration + security fixtures)
Frontend:  3 passed, build OK
Ruff:     PASS
```

## Exit Gate Verification

- [x] Valid local Git fixture reaches `ready` status
- [x] Path outside allowed roots rejected (400)
- [x] Symlink escape rejected
- [x] Original project files unchanged after registration

## Known Limitations

- Git dirty detection is best-effort without git CLI (M5 Tool Gateway)
- No incremental analysis yet (Milestone 2)
- No project manifest editor UI yet

## Recommendation

Milestone 1 exit gate criteria met. Ready for owner approval to proceed to Milestone 2.
