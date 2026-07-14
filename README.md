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

## API endpointy

### System (M0)

| Endpoint | Popis |
|----------|-------|
| `GET /api/v1/system/health` | Stav platformy, databáze, capabilities |
| `GET /api/v1/system/doctor` | Rozšířená diagnostika s issues |

### Projects (M1)

| Endpoint | Popis |
|----------|-------|
| `GET /api/v1/projects` | Seznam registrovaných projektů |
| `POST /api/v1/projects` | Registrace + preflight |
| `GET /api/v1/projects/{id}` | Detail projektu |
| `PATCH /api/v1/projects/{id}` | Aktualizace metadat |
| `POST /api/v1/projects/{id}/archive` | Archivace projektu |

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

**Milestones M0–M9 — Production Candidate** ✅

| Milník | Stav | Popis |
|--------|------|-------|
| M0 | ✅ | Základ, health API, System Status |
| M1 | ✅ | Project Registry, preflight, portfolio |
| M2 | ✅ | Analýza, symbol parsery, Explorer |
| M3 | ✅ | Durable jobs, evidence chain, worker |
| M4 | ✅ | Model router, goals & plans |
| M5 | ✅ | Tool Gateway, workspaces, patch engine |
| M6 | ✅ | Verification gates, repair loop |
| M7 | ✅ | Guardian policies, security suite |
| M8 | ✅ | Pilot E2E flow |
| M9 | ✅ | Backup, security scan, runbooks |

**Testy:** 90 (89 backend + 1 e2e), security scan PASS

```bash
./scripts/test.sh          # všechny testy
./scripts/security-scan.sh # pip-audit + npm audit
./scripts/backup.sh        # záloha DB a artefaktů
```

## Licence

Proprietární — David Volf
