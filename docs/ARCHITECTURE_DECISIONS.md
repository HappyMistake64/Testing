# FADE - Architecture Decisions

These decisions are accepted for the first implementation. Change requires a new ADR proposal and explicit owner approval.

## ADR-001 Platform repository is separate from managed projects

**Decision:** FADE has its own repository. Managed project repositories remain independent and are registered by source location.

**Reason:** Preserves Git history, dependencies, ownership and portability. Prevents a giant coupled repository.

**Consequences:** Cross-project operations use registry/context adapters. Mutations use worktrees or isolated copies.

## ADR-002 Modular monolith for MVP

**Decision:** One FastAPI control-plane application plus a local durable worker and React frontend.

**Reason:** Fits an 8 GB local machine and is easier to debug and test than microservices.

**Rejected:** Kubernetes-first, many network services, mandatory message broker.

## ADR-003 Python/FastAPI backend and React/TypeScript frontend

**Decision:** Python 3.12 + FastAPI/Pydantic/SQLAlchemy; React + TypeScript + Vite.

**Reason:** Matches orchestration/AI ecosystem and provides a strong dashboard stack.

## ADR-004 SQLite WAL for MVP persistence

**Decision:** SQLite with WAL, Alembic migrations and filesystem artifacts.

**Reason:** Local-first, low operating cost, transactional and backup-friendly.

**Evolution:** A database port permits later PostgreSQL. Do not prematurely add it.

## ADR-005 Durable DB-backed jobs before external queue

**Decision:** Jobs, claims, leases and checkpoints live in the database for MVP.

**Reason:** Avoids mandatory Redis and ensures restart recovery.

## ADR-006 Tool Gateway is the mandatory side-effect boundary

**Decision:** Agents cannot directly run subprocesses or write arbitrary paths.

**Reason:** Central authorization, resource limits, redaction and audit.

## ADR-007 Isolated workspace for every mutating job

**Decision:** Prefer Git worktrees; filesystem copy is fallback.

**Reason:** Protect original repositories and make patches/reverts reproducible.

## ADR-008 Deterministic gates control state transitions

**Decision:** Model text cannot grant permission, apply external side effects or mark completion.

**Reason:** Models are probabilistic and can be manipulated by repository content.

## ADR-009 Local model is default; cloud is explicit opt-in

**Decision:** Provider router supports local first. No silent cloud fallback.

**Reason:** Privacy, cost, offline operation and user control.

## ADR-010 Evidence and continuity are foundational

**Decision:** Tool calls, patches, tests, approvals and state changes produce durable evidence from early milestones.

**Reason:** Autonomy without recoverability and proof is not trustworthy.

## ADR-011 FTS and symbols before mandatory embeddings

**Decision:** SQLite FTS5 and parser-based symbol relationships are baseline. Embeddings are optional.

**Reason:** Better determinism and lower memory use on 8 GB hardware.

## ADR-012 Single-user local ownership for MVP

**Decision:** No public account system or multi-tenancy in first release.

**Reason:** Focus scope on project orchestration and security boundaries. Internal actor fields remain future-ready.

## ADR proposal template

```markdown
# ADR-NNN Title

Status: Proposed | Accepted | Rejected | Superseded
Date:
Owner decision:

## Context
## Decision
## Alternatives considered
## Security and data impact
## Migration/rollback impact
## Consequences
## Required tests
```
