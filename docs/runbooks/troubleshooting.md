# Troubleshooting Runbook

## API will not start

1. Run `./scripts/doctor.sh` and resolve blocking issues.
2. Verify `var/` exists and is writable: `mkdir -p var`
3. Run migrations: `uv run alembic upgrade head`
4. Check port 8000 is free: `ss -tlnp | grep 8000`

## Database errors

- **Integrity check failed**: Restore from backup (see `backup-restore.md`).
- **WAL mode warning**: Ensure only one writer; restart API after unclean shutdown.
- **Migration failed**: Check `alembic current` vs `alembic heads`.

## Project registration fails

- Confirm path is under `FADE_PROJECT_ALLOWED_ROOTS` if configured.
- Path must be a Git repository when `require_git=true`.
- Symlinks escaping allowed roots are rejected by design.

## Jobs stuck in queued

- Check `FADE_MAX_CONCURRENT_HEAVY_JOBS` budget in settings.
- Inspect job events: `GET /api/v1/jobs/{id}/events`
- Cancel and retry: `POST /api/v1/jobs/{id}/cancel`

## Frontend cannot reach API

- Set `VITE_API_BASE_URL=http://127.0.0.1:8000` in `.env`
- Ensure CORS allows `localhost:5173`
- Verify API health: `curl http://127.0.0.1:8000/api/v1/system/health`

## Security scan failures

Run `./scripts/security-scan.sh` manually. Update dependencies or document accepted risk in ADR before release.

## Logs

Structured JSON logs include `correlation_id`. Search by correlation ID from API error responses.
