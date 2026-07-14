# FADE Platform

**FADE — First Artificial David's Ecosystem**

Lokální autonomní AI platforma pro řízení, analýzu, vývoj, testování a dlouhodobé zlepšování vybraných softwarových projektů.

## Požadavky

- Ubuntu 24.04 LTS nebo WSL2
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+
- [pnpm](https://pnpm.io/) 9+
- Git

## Rychlý start

```bash
# 1. Klonovat repozitář
git clone <repo-url> fade-platform
cd fade-platform

# 2. Zkopírovat konfiguraci
cp .env.example .env

# 3. Nainstalovat závislosti
uv sync --all-extras
pnpm install

# 4. Spustit migrace
uv run alembic upgrade head

# 5. Spustit vývojové prostředí (API + Web)
chmod +x scripts/*.sh
./scripts/dev.sh
```

Otevřete http://localhost:5173 pro dashboard. API běží na http://127.0.0.1:8000.

## Ověření instalace

```bash
./scripts/doctor.sh    # Kontrola prostředí
./scripts/test.sh      # Všechny testy, lint, build
```

## API endpointy (Milestone 0)

| Endpoint | Popis |
|----------|-------|
| `GET /api/v1/system/health` | Stav platformy, databáze, capabilities |
| `GET /api/v1/system/doctor` | Rozšířená diagnostika s issues |

## Architektura

```
apps/
  api/          FastAPI composition root
  web/          React + Vite frontend
packages/
  domain/       Čisté doménové modely (bez framework importů)
  application/  Use cases a port interfaces
  infrastructure/ DB, settings, logging, adapters
migrations/     Alembic migrace
tests/          Unit a integrační testy
workers/        Lokální durable worker (M3+)
```

### Pravidla závislostí

- `domain` nesmí importovat FastAPI, SQLAlchemy ani infrastructure
- API routery jsou tenké — validace, use case, mapování
- Veškeré agentní side effects (M5+) procházejí Tool Gateway

## Dokumentace

- [White Paper](docs/WHITE_PAPER.md) — kompletní technická specifikace
- [Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md) — zamčená rozhodnutí
- [Implementation Backlog](docs/IMPLEMENTATION_BACKLOG.md) — milníky a úkoly
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) — plán implementace

## Aktuální stav

**Milestone 0 — Foundation and Architecture Lock** ✅

**Milestone 1 — Project Registry and Preflight** ✅

- Project CRUD API s idempotentní registrací
- Path safety (allowed roots, symlink containment)
- Preflight pipeline (inventory, Git metadata, manifests, sensitive scan)
- Portfolio dashboard, Add Project wizard, Project detail
- 33 backend testů, security fixtures

## Licence

Proprietární — David Volf
