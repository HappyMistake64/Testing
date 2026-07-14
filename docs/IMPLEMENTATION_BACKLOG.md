# FADE - Implementation Backlog

## Status legend

- `[ ]` not started
- `[~]` in progress
- `[x]` verified complete
- `[!]` blocked

A task is complete only after its acceptance tests and evidence are present.

# Milestone 0 - Foundation and Architecture Lock

## M0-E1 Repository and toolchain
- [x] Create platform-only repository structure.
- [x] Configure Python 3.12 project with `uv`.
- [x] Configure pnpm workspace and React/Vite app.
- [x] Add `.editorconfig`, `.gitignore`, `.env.example` and version files.
- [x] Add `scripts/dev.sh`, `scripts/test.sh`, `scripts/doctor.sh`.

**Acceptance**
- Clean install works on Ubuntu 24.04/WSL2.
- No user-specific absolute paths.
- Lockfiles are committed.

## M0-E2 Domain and application boundaries
- [x] Create domain package with IDs, risk and autonomy value types.
- [x] Create application package skeleton with ports but no fake AI use cases.
- [x] Add architecture import-boundary test.

**Acceptance**
- Domain imports no framework/infrastructure package.
- Invalid enum/value construction is tested.

## M0-E3 API foundation
- [x] FastAPI composition root.
- [x] Correlation ID middleware.
- [x] Stable error response schema and exception mapping.
- [x] `/api/v1/system/health`.
- [x] `/api/v1/system/doctor`.
- [x] Structured safe logging.

**Acceptance**
- API tests cover success and representative failure.
- Health reports database state and capability flags.
- Logs do not expose configured secret values.

## M0-E4 Persistence foundation
- [x] SQLAlchemy async/sync strategy documented and implemented consistently.
- [x] SQLite WAL and foreign keys configuration.
- [x] Alembic setup.
- [x] Initial `projects` table migration.
- [x] Migration integration test.

**Acceptance**
- Fresh DB upgrades to head.
- SQLite integrity check passes.
- Migration is repeatable in test fixtures.

## M0-E5 Web shell
- [x] Application layout and navigation.
- [x] System Status route.
- [x] Typed API client.
- [x] Health/doctor loading, success and error states.
- [x] Component tests.

**Acceptance**
- Production frontend build succeeds.
- UI does not report planned capabilities as available.

## M0-E6 Documentation and verification
- [x] README clean setup and run commands.
- [x] Architecture overview and package dependency rules.
- [x] Run all tests, lint, typecheck and build.
- [x] Create milestone evidence report.

**Milestone 0 exit gate**
- Backend tests PASS.
- Frontend tests PASS.
- Typecheck/lint/build PASS.
- Doctor has no blocking issue in supported clean environment.
- Owner approves transition to Milestone 1.

# Milestone 1 - Project Registry and Preflight

## M1-E1 Project CRUD
- [x] Project domain entity and repository port.
- [x] SQLAlchemy repository.
- [x] List, get, register, patch metadata, archive API.
- [x] Idempotent registration behavior.

## M1-E2 Source and path safety
- [x] Allowed roots configuration.
- [x] Canonical path and symlink containment.
- [x] Local Git source validation.
- [x] Non-Git detection and explicit handling.

## M1-E3 Preflight pipeline
- [x] File count/size inventory.
- [x] Git revision/dirty/default branch.
- [x] Manifest detection.
- [x] Protected/sensitive file name scan without reading values.
- [x] Preflight status and errors.

## M1-E4 Add Project Wizard and portfolio
- [x] Register form.
- [x] Preflight progress.
- [x] Detected project summary.
- [x] Project cards, status and archive.

**Milestone 1 exit gate**
- Valid local Git project reaches READY/PREFLIGHT-complete.
- Malicious path fixture is rejected.
- Original project is unchanged.

# Milestone 2 - Analysis and Project Profile

- [ ] Ignore engine and file inventory cache.
- [ ] Python symbol parser.
- [ ] TypeScript symbol parser.
- [ ] Manifest and command discovery.
- [ ] Incremental content-hash index.
- [ ] Project profile versions and provenance.
- [ ] Baseline health components.
- [ ] Project Overview and Explorer.

# Milestone 3 - Durable Jobs and Evidence

- [ ] Durable DB queue.
- [ ] Worker claim, heartbeat, lease and recovery.
- [ ] Job state machine and invariants.
- [ ] Evidence event chain.
- [ ] Artifact store and manifest.
- [ ] SSE timeline with reconnect.
- [ ] Pause/cancel/recovery tests.

# Milestone 4 - Planning and Model Router

- [ ] Provider ports and capability model.
- [ ] Ollama adapter.
- [ ] Optional OpenAI-compatible adapter with explicit data policy.
- [ ] Context bundle schema.
- [ ] Goal and plan workflows.
- [ ] Structured model output validation.
- [ ] Plan approval UI.

# Milestone 5 - Workspace, Tools and Patch

- [ ] Git worktree workspace strategy.
- [ ] Lease/fencing enforcement.
- [ ] Tool Gateway read tools.
- [ ] Safe command wrapper.
- [ ] Workspace write tools.
- [ ] Patch Engine with base hashes.
- [ ] Diff Review UI.

# Milestone 6 - Verification and Repair

- [ ] Verification matrix and command profiles.
- [ ] Test/build/lint result parsers.
- [ ] Verification gates.
- [ ] Diagnosis schema and Debugger role.
- [ ] Repair iteration budgets and anti-loop hashes.
- [ ] Regression evidence.

# Milestone 7 - Guardian Hardening

- [ ] Autonomy levels and effective policy resolution.
- [ ] Secret store/redaction.
- [ ] Network policy.
- [ ] Protected actions and approval flows.
- [ ] Malicious repository security suite.
- [ ] Policy editor and explanation UI.

# Milestone 8 - Real project pilots

- [ ] Pilot 1 small fixture end-to-end.
- [ ] Pilot 2 NeuroString or selected Python project.
- [ ] Pilot 3 TradePilot paper-only profile.
- [ ] Project-specific manifests and verification profiles.
- [ ] Pilot outcome report and architecture adjustments via ADR only.

# Milestone 9 - Production Candidate

- [ ] Resource/performance budgets.
- [ ] Artifact retention and cleanup.
- [ ] Backup and restore test.
- [ ] Upgrade/migration tests.
- [ ] Release packaging.
- [ ] Runbooks and troubleshooting.
- [ ] Security and recovery release gate.
