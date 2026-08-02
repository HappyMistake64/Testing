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

- [x] Ignore engine and file inventory cache.
- [x] Python symbol parser.
- [x] TypeScript symbol parser.
- [x] Manifest and command discovery.
- [x] Incremental content-hash index.
- [x] Project profile versions and provenance.
- [x] Baseline health components.
- [x] Project Overview and Explorer.

# Milestone 3 - Durable Jobs and Evidence

- [x] Durable DB queue.
- [x] Worker claim, heartbeat, lease and recovery.
- [x] Job state machine and invariants.
- [x] Evidence event chain.
- [x] Artifact store and manifest.
- [x] SSE timeline with reconnect.
- [x] Pause/cancel/recovery tests.

# Milestone 4 - Planning and Model Router

- [x] Provider ports and capability model.
- [x] Ollama adapter.
- [x] Optional OpenAI-compatible adapter with explicit data policy.
- [x] Context bundle schema.
- [x] Goal and plan workflows.
- [x] Structured model output validation.
- [x] Plan approval UI.

# Milestone 5 - Workspace, Tools and Patch

- [x] Git worktree workspace strategy.
- [x] Lease/fencing enforcement.
- [x] Tool Gateway read tools.
- [x] Safe command wrapper.
- [x] Workspace write tools.
- [x] Patch Engine with base hashes.
- [x] Diff Review UI.

# Milestone 6 - Verification and Repair

- [x] Verification matrix and command profiles.
- [x] Test/build/lint result parsers.
- [x] Verification gates.
- [x] Diagnosis schema and Debugger role.
- [x] Repair iteration budgets and anti-loop hashes.
- [x] Regression evidence.

# Milestone 7 - Guardian Hardening

- [x] Autonomy levels and effective policy resolution.
- [x] Secret store/redaction.
- [x] Network policy.
- [x] Protected actions and approval flows.
- [x] Malicious repository security suite.
- [x] Policy editor and explanation UI.

# Milestone 8 - Real project pilots

- [x] Pilot 1 small fixture end-to-end.
- [~] Pilot 2 NeuroString or selected Python project.
- [~] Pilot 3 TradePilot paper-only profile.
- [x] Project-specific manifests and verification profiles.
- [x] Pilot outcome report and architecture adjustments via ADR only.

# Milestone 9 - Production Candidate

- [x] Resource/performance budgets.
- [x] Artifact retention and cleanup.
- [x] Backup and restore test.
- [x] Upgrade/migration tests.
- [x] Release packaging.
- [x] Runbooks and troubleshooting.
- [x] Security and recovery release gate.

# Milestone 10 - Agent Runtime (completed)

- [x] Agent loop with tool-based context gathering.
- [x] Structured implementation output and patch application.
- [x] Deterministic verification and repair in isolated workspaces.

# Milestone 11 - Platform completion (completed)

- [x] Diff approve/reject/apply-to-source workflow with promoted files.
- [x] NeuroString and TradePilot pilot fixtures end-to-end.
- [x] GitHub Actions CI (backend, frontend, security).
- [x] Diff review and job console UI with verification detail.

# Milestone 12 - Command-driven personal assistant (ADR-013, ADR-014)

- [x] Assistant domain models: sessions, turns, capabilities, approvals, memory.
- [x] Migration 008: assistant tables + memory FTS5 index.
- [x] Typed tool registry with capability classes and exact-args approval binding.
- [x] Deterministic intent compilation (CZ/EN) with model-answer fallback.
- [x] Durable assistant turns as jobs; approval recovery re-queues blocked jobs.
- [x] Emergency stop: pause switch blocks tools and revokes pending approvals.
- [x] Local connectors (calendar, email, notifications, smart home) with
      opt-in Home Assistant/webhook adapters behind host allowlists.
- [x] Durable memory with provenance, expiry, and local FTS retrieval.
- [x] User-created automations (once/interval) scheduled by the local worker.
- [x] Voice/vision ports with honest local defaults (browser STT/TTS).
- [x] Assistant chat UI: approvals, memory, automations, capabilities,
      emergency stop, voice input/output.
- [x] Unit + integration test coverage for approvals, memory, automations,
      turn lifecycle, and API surface.
