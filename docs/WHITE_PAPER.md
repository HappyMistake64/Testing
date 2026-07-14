# FADE - Master Technical White Paper

First Artificial David's Ecosystem

Lokální autonomní AI platforma pro řízení, analýzu, vývoj, testování, opravy a dlouhodobé zlepšování vybraných softwarových projektů.

Verze dokumentu: 1.0 | Stav: implementační specifikace | Primární prostředí: Ubuntu 24.04 LTS / Linux-first | Autor koncepce: David Volf

> FADE je lokální autonomní AI systém, který dokáže převzít softwarový projekt, pochopit jeho stav, navrhnout další kroky, vytvořit změny, otestovat je, opravit chyby, doložit výsledky a dlouhodobě se zlepšovat.

---

# 0. Řízení dokumentu

| Položka | Hodnota |
| --- | --- |
| Účel | Předat Cursoru a vývojáři jednoznačnou technickou specifikaci platformy FADE. |
| Typ dokumentu | Master Technical White Paper + Product Requirements Document + System Architecture Specification. |
| Rozhodovací autorita | Vlastník produktu David. Cursor provádí implementaci, ale nemění schválenou architekturu bez explicitního rozhodnutí. |
| Rozsah první implementace | Lokální single-user platforma, Linux-first, více samostatných projektových workspace, řízené AI workflow. |
| Zdroj pravdy | Tento dokument, soubor ARCHITECTURE_DECISIONS.md a backlog. Při rozporu má pořadí: rozhodnutí vlastníka > ADR > white paper > backlog > implementační detail. |
| Mimo rozsah MVP | Veřejný multi-tenant SaaS, marketplace, plně distribuovaný cluster, nekontrolované autonomní změny produkce, cloud-only provoz. |

## 0.1 Jak dokument použít v Cursoru

1. Vytvořit nový repozitář fade-platform pouze pro platformu. Spravované projekty se do něj nekopírují; registrují se cestou nebo Git URL.
2. Umístit Markdown verzi white paperu, ADR, backlog a Cursor rules do kořene repozitáře.
3. Nechat Cursor nejdřív vytvořit implementační plán pro aktuální milník a mapu dotčených souborů.
4. Implementovat vždy pouze jeden schválený milník. Po každém milníku spustit testy, vytvořit důkazní report a aktualizovat stav backlogu.
5. Neumožnit agentovi měnit soubory spravovaných projektů přímo. Změny musí vznikat jako patch, branch nebo izolovaná pracovní kopie.

## 0.2 Terminologie závaznosti

| Termín | Význam |
| --- | --- |
| MUST / MUSÍ | Povinný požadavek. Bez něj není funkce nebo milník hotový. |
| SHOULD / MĚL BY | Silně doporučené. Odchylka musí být zdokumentována. |
| MAY / MŮŽE | Volitelná schopnost. Nesmí blokovat MVP. |
| Project workspace | Izolované pracovní prostředí jednoho spravovaného projektu. |
| Control plane | Centrální řídicí vrstva FADE. |
| Evidence | Strojově i lidsky čitelný důkaz o příkazu, změně, testu, výsledku nebo rozhodnutí. |
| Autonomy level | Míra oprávnění FADE provádět akce bez ručního potvrzení. |

---

# 1. Executive Summary

FADE sjednocuje vybrané projekty do jedné velké lokální platformy, ale neslučuje jejich zdrojové kódy do jednoho chaotického repozitáře. Každý projekt zůstává samostatný, má vlastní Git historii, závislosti, testy, bezpečnostní pravidla a životní cyklus. FADE nad nimi vytváří společnou řídicí vrstvu: registr projektů, dashboard, znalostní index, plánování, agentní runtime, bezpečné provádění příkazů, patchování, testování, opravný cyklus, auditní stopu a dlouhodobou paměť.

Cílem není vytvořit další chat s AI. Cílem je operační systém pro softwarovou práci: uživatel zaregistruje projekt, FADE jej prozkoumá, vytvoří ověřitelný model jeho architektury a stavu, nabídne další kroky, připraví změny, spustí testy a uchová důkazy. Při vyšší úrovni autonomie může FADE opakovat implementační a opravné cykly, ale vždy uvnitř jasně definovaných oprávnění, rozpočtů a bezpečnostních hranic.

První produkčně použitelná verze je navržena pro jednoho vlastníka, 8 GB RAM, lokální SQLite, souborové úložiště, Git a Linux. Frontend je React + TypeScript. Backend a orchestrace jsou Python 3.12 + FastAPI. Dlouhé úlohy běží jako perzistentní joby s checkpointy. Modely se připojují přes model router; lokální model je výchozí, cloudové API je volitelné. Platforma nesmí vyžadovat cloud pro základní řízení projektů.

## 1.1 Hlavní přínos

- Jedno místo pro všechny vybrané projekty, jejich stav, cíle, testy, rizika, dokumentaci a historii práce.
- Jednotný proces od analýzy přes plán a implementaci až po ověření a důkazy.
- Oddělení projektů a omezení škod: chyba v jednom workspace nesmí poškodit ostatní projekty ani hostitelský systém.
- Schopnost pokračovat po restartu díky perzistentním jobům, checkpointům a auditnímu ledgeru.
- Postupné zvyšování autonomie podle důvěry, nikoli okamžitá neomezená autonomie.
- Znovupoužitelné znalosti: FADE si pamatuje ověřené postupy, rozhodnutí, známé chyby a charakteristiky každého projektu.

## 1.2 Co FADE není

- Není to univerzální chatbot bez vazby na repozitáře a důkazy.
- Není to systém, který bez kontroly přepisuje produkční kód.
- Není to povinný monorepo pro všechny projekty.
- Není to cloudová služba závislá na jednom poskytovateli modelu.
- Není to náhrada Gitu, CI, testovacích frameworků nebo operačního systému; tyto nástroje integruje a řídí.

---

# 2. Produktová vize a strategický cíl

## 2.1 Vize

FADE má být osobní softwarová továrna a řídicí centrum. Vlastník vidí celý ekosystém jako portfolio projektů. U každého projektu zná FADE účel, architekturu, aktuální stav, otevřené cíle, technický dluh, rizika, testovací pokrytí, poslední ověřené buildy a doporučený další krok. Uživatel může přepínat mezi projekty, spouštět řízené workflow a porovnávat jejich zdraví bez ručního přepisování kontextu mezi nástroji.

## 2.2 Strategické výsledky

| Výsledek | Měřitelný stav |
| --- | --- |
| Centralizace řízení | Všechny vybrané projekty jsou dostupné v jednom registru a dashboardu. |
| Reprodukovatelnost | Každá změna má vstup, plán, patch, příkazy, testy, výsledek a hash artefaktů. |
| Bezpečnost | Výchozí režim je read-only analýza; zápis vyžaduje přidělené oprávnění a izolovaný workspace. |
| Kontinuita | Job lze po pádu obnovit z posledního bezpečného checkpointu bez opakování již potvrzených kroků. |
| Kvalita | Žádná změna není označena jako hotová bez definovaných acceptance testů a verification gate. |
| Efektivita | Opakované analýzy používají inkrementální index a cache místo úplného zpracování repozitáře. |
| Přenositelnost | Projekt lze odpojit od FADE bez ztráty jeho vlastního repozitáře nebo závislosti na proprietárním formátu. |

## 2.3 Princip: platforma sjednocuje řízení, nikoli kód

FADE platform repository obsahuje pouze kód samotné platformy. Spravované projekty jsou externí entity registrované v Project Registry. Mohou být na lokálním disku, v Git repozitáři nebo později na vzdáleném hostingu. FADE si může vytvořit bezpečnou pracovní kopii, Git worktree nebo dočasnou větev, ale originální adresář projektu nesmí být modifikován mimo schválený workflow.

```
FADE platform repository
        |
        +-- Project Registry ----> TradePilot repository
        |                      --> NeuroString repository
        |                      --> CRATE repository
        |                      --> Continuity OS repository
        |                      --> any future project
        |
        +-- Shared control plane
        +-- Shared agents and tools
        +-- Shared evidence and memory
        +-- Per-project isolated workspaces
```

---

# 3. Uživatel, provozní model a hlavní flow

## 3.1 Primární uživatel

MVP je single-user systém. Primárním uživatelem je vlastník projektů a správce platformy. Není potřeba řešit registraci veřejných účtů, organizace ani billing. Přesto musí být interní datový model připraven na budoucí přidání rolí, protože akce jako schválení produkčního nasazení, práce se secrets nebo změna politik mohou později vyžadovat oddělená oprávnění.

## 3.2 Hlavní uživatelský flow

1. Uživatel otevře FADE Dashboard.
2. Přidá nový projekt zadáním lokální cesty nebo Git URL.
3. FADE provede bezpečný preflight: dostupnost, Git stav, velikost, jazyky, package manifests, testovací příkazy a citlivé soubory.
4. FADE vytvoří profil projektu, index symbolů, mapu architektury a baseline health report.
5. Uživatel definuje cíl nebo vybere doporučený další krok.
6. Planner připraví rozklad cíle, rizika, acceptance criteria, test plan a odhad rozpočtu.
7. Po schválení Agent Runtime vytvoří izolovanou změnu, spustí nástroje a průběžně ukládá checkpointy.
8. Verification Engine spustí požadované testy, lint, build, bezpečnostní kontroly a porovnání chování.
9. Pokud ověření selže, Repair Loop provede omezený počet diagnostických iterací.
10. FADE zobrazí diff, důkazy, rizika a doporučení: přijmout, upravit, vrátit nebo pokračovat.
11. Po přijetí se změna sloučí podle zvolené Git strategie. Ledger uchová kompletní auditní stopu.

## 3.3 Co se nesmí stát

- Agent nesmí zapisovat mimo přidělený workspace.
- Agent nesmí číst nebo exportovat secrets bez explicitního oprávnění.
- Agent nesmí označit úkol jako hotový pouze na základě vlastního textového tvrzení.
- Selhání modelu nebo UI nesmí ztratit historii jobu a již vytvořené artefakty.
- Projekt A nesmí získat kontext, secrets nebo soubory projektu B bez explicitního cross-project oprávnění.
- FADE nesmí automaticky spouštět destruktivní shell příkazy, publikovat balíčky, pushovat do chráněné větve nebo provádět produkční obchodování.
- Aktualizace platformy nesmí nevratně migrovat databázi bez zálohy a rollback strategie.

---

# 4. Rozsah produktu

## 4.1 MVP - povinné schopnosti

| Oblast | MVP schopnost |
| --- | --- |
| Project Registry | Přidání, odebrání, archivace, tagování a health stav projektů. |
| Project Analysis | Detekce jazyků, frameworků, struktur, Git stavu, příkazů a základní architektonické mapy. |
| Workspace Isolation | Bezpečná pracovní kopie nebo Git worktree na každý job. |
| Task Planning | Cíl -> plán -> kroky -> acceptance criteria -> test plan. |
| Agent Runtime | Role-based agentní workflow s limity, checkpointy a přerušením. |
| Tool Execution | Povolené shell příkazy, čtení/zápis souborů, Git diff, testy a build. |
| Patch Engine | Vytvoření, validace, zobrazení a aplikace patchů. |
| Verification | Test/lint/build příkazy, timeouty, výsledky, logy a gate. |
| Repair Loop | Omezená diagnostika a oprava po neúspěšném ověření. |
| Evidence Ledger | Append-only záznam událostí a artefaktů. |
| Dashboard | Portfolio projektů, detail projektu, joby, diff, logy, důkazy, nastavení. |
| Model Router | Minimálně jeden lokální provider a volitelný OpenAI-compatible provider. |
| Guardian | Autonomy levels, command policy, path policy, secret redaction, approval gates. |

## 4.2 Po MVP

- Víceuživatelské role, týmy a approval chain.
- Distribuované worker nodes a leasing úloh.
- Visual browser/computer-use agent.
- Marketplace agentů, tool pluginů a project adapterů.
- Automatické release workflow a deployment connectors.
- Cross-project dependency graph a koordinované změny více repozitářů.
- Pokročilý knowledge graph, embeddings a dlouhodobé učení z výsledků.
- Mobilní companion aplikace a vzdálené schvalování.

## 4.3 Explicitně mimo MVP

- Vlastní foundation model nebo trénování velkého modelu.
- Nahrazení IDE; první verze se integruje s Cursorem/VS Code, později může FADE IDE převzít část funkcí.
- Kubernetes jako povinná runtime vrstva.
- Plně automatické nasazení do produkce bez lidského gate.
- Neomezený přístup agentů k internetu a hostitelskému systému.

---

# 5. Architektonické principy

| Princip | Důsledek pro implementaci |
| --- | --- |
| Local-first | Základní data, historie, indexy a řízení musí fungovat lokálně. Cloudové modely a služby jsou volitelné adaptéry. |
| Evidence before trust | Každé tvrzení o funkčnosti musí mít odkaz na test, příkaz, log, diff nebo artefakt. |
| Isolation by default | Každý projekt, job a tool call má explicitní hranice cest, prostředí a oprávnění. |
| Git-native | Kódová změna se reprezentuje standardním diffem, commitem nebo větví. FADE nevytváří proprietární zdroj pravdy pro kód. |
| Deterministic control plane | Model může navrhovat, ale stavové přechody, oprávnění, rozpočty a gates řídí deterministický software. |
| Progressive autonomy | Autonomie roste po úspěšných ověřených úlohách a může být kdykoli snížena. |
| Recoverable workflows | Dlouhé úlohy jsou událostmi a checkpointy obnovitelné po restartu. |
| Replaceable providers | Model, index, sandbox i Git hosting mají rozhraní; nesmí být natvrdo svázány s jediným dodavatelem. |
| Resource awareness | Scheduler respektuje 8 GB RAM, CPU, disk a modelové limity. Výchozí konfigurace nesmí spouštět několik těžkých modelů současně. |
| Human-readable operation | Uživatel musí vždy vidět co FADE udělalo, proč, s jakým výsledkem a co navrhuje dál. |

---

# 6. System Context Architecture

FADE se skládá z webového uživatelského rozhraní, API/control plane, perzistentního job systému, agentního runtime, bezpečné tool gateway, workspace manageru a několika datových úložišť. Spravované projekty jsou externí systémy. Modely, Git hosting a volitelné cloudové služby jsou adaptéry.

```
+------------------------ USER -------------------------+
| Browser / Cursor / CLI                                 |
+---------------------------+----------------------------+
                            |
                            v
+---------------------- FADE CONTROL PLANE ----------------------+
| Web UI | FastAPI | Auth(local) | Project Registry | Job API    |
| Planner | Policy Engine | Scheduler | Event Stream | Reports    |
+---------------------+-------------------+-----------------------+
                      |                   |
                      v                   v
             +----------------+   +-----------------------+
             | Agent Runtime  |   | Knowledge & Context   |
             | role workflows |   | symbols, FTS, memory  |
             +-------+--------+   +-----------+-----------+
                     |                        |
                     v                        |
             +----------------+               |
             | Tool Gateway   |<--------------+
             | command policy |
             +-------+--------+
                     |
                     v
             +------------------------+
             | Isolated Workspaces    |
             | Git worktree/copy      |
             | build/test/patch       |
             +-----------+------------+
                         |
       +-----------------+-----------------------------+
       |                 |                 |           |
       v                 v                 v           v
   TradePilot       NeuroString         CRATE      Other repos

External adapters: Ollama/llama.cpp, OpenAI-compatible API, GitHub,
package registries, optional deployment targets.
```

## 6.1 Logické vrstvy

| Vrstva | Odpovědnost | Nesmí dělat |
| --- | --- | --- |
| Presentation | Dashboard, detail projektu, job timeline, diff, approvals, settings. | Rozhodovat o bezpečnostních oprávněních pouze na klientovi. |
| Application/Control | Use cases, stavové automaty, scheduler, approvals, orchestrace. | Spoléhat na nedeterministický model pro integritu stavu. |
| Domain | Project, Goal, Task, Job, Evidence, Policy, Workspace, ModelRun. | Importovat frameworkové detaily UI nebo databáze. |
| Infrastructure | SQLite, filesystem, Git, subprocess, model providers, event stream. | Obsahovat produktová rozhodnutí rozptýlená bez rozhraní. |
| Managed Projects | Vlastní kód a runtime jednotlivých projektů. | Znát interní databázi FADE nebo záviset na ní pro svůj běh. |

---

# 7. Navržený technologický stack

| Komponenta | Volba | Odůvodnění |
| --- | --- | --- |
| Frontend | React 19 + TypeScript + Vite | Rychlý lokální vývoj, silné typování, jednoduché SPA, vhodné pro dashboard a streamované logy. |
| UI state/data | TanStack Query + Zustand | Server state oddělený od lokálního UI state; nízká režie. |
| Styling | CSS variables + component primitives; bez těžkého design systému v MVP | Udržitelný vlastní vzhled a nízké nároky. |
| Backend API | Python 3.12 + FastAPI + Pydantic v2 | Výborné pro orchestrace, AI integrace, asynchronní API a validaci. |
| Persistence | SQLite WAL + SQLAlchemy 2 + Alembic | Lokální provoz, transakce, snadná záloha, migrace. |
| Queue/Jobs | DB-backed durable queue v MVP | Žádný Redis požadavek; stav přežije restart. Později adapter na NATS/Redis. |
| Git | Git CLI přes bezpečný wrapper | Plná kompatibilita a transparentnost; explicitní allowlist argumentů. |
| Search/index | SQLite FTS5 + tree-sitter/symbol extraction | Funguje na 8 GB bez samostatné vektorové databáze. Embeddings volitelně později. |
| Model runtime | Ollama/llama.cpp + OpenAI-compatible adapter | Lokální výchozí provoz, vyměnitelnost providerů. |
| Testing backend | pytest, pytest-asyncio, httpx, property tests dle potřeby | Reprodukovatelná doménová a integrační validace. |
| Testing frontend | Vitest + React Testing Library + Playwright | Komponentové i end-to-end testy. |
| Packaging | uv pro Python, pnpm pro Node | Rychlé a deterministické dependency management. |
| Observability | Structured JSON logs + OpenTelemetry-ready interfaces | Lokálně čitelné, připravené na budoucí tracing. |

## 7.1 Podporované prostředí

- Primární: Ubuntu 24.04 LTS, x86_64, 8 GB RAM, alespoň 20 GB volného místa.
- Sekundární: jiné moderní Linux distribuce po ověření.
- Windows: doporučen WSL2 pro plnou kompatibilitu. Nativní Windows executor je pozdější adapter.
- macOS: není priorita MVP, ale control plane by neměl používat Linux-specific API mimo infra adaptery.

---

# 8. Referenční repozitářová struktura FADE platformy

```
fade-platform/
├── README.md
├── pyproject.toml
├── uv.lock
├── package.json
├── pnpm-workspace.yaml
├── docker-compose.yml              # volitelné, ne povinné pro local dev
├── .env.example
├── .gitignore
├── .cursor/
│   └── rules/
│       └── fade-master.mdc
├── docs/
│   ├── WHITE_PAPER.md
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── IMPLEMENTATION_BACKLOG.md
│   ├── api/
│   ├── diagrams/
│   └── runbooks/
├── apps/
│   ├── api/                         # FastAPI composition root
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   └── routers/
│   └── web/                         # React/Vite frontend
│       ├── src/
│       └── tests/
├── packages/
│   ├── domain/                      # čisté doménové modely a pravidla
│   ├── application/                 # use cases, commands, queries
│   ├── infrastructure/              # db, git, filesystem, providers
│   ├── project_analysis/
│   ├── context_engine/
│   ├── planning/
│   ├── agent_runtime/
│   ├── tool_gateway/
│   ├── verification/
│   ├── repair_loop/
│   ├── guardian/
│   ├── continuity/
│   ├── evidence/
│   └── model_router/
├── workers/
│   └── local_worker.py
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   └── fixtures/
├── scripts/
│   ├── dev.sh
│   ├── test.sh
│   ├── backup.sh
│   └── doctor.sh
└── var/                              # runtime, gitignored
    ├── fade.db
    ├── workspaces/
    ├── artifacts/
    ├── logs/
    ├── indexes/
    └── backups/
```

## 8.1 Modulární pravidla

- packages/domain nesmí importovat FastAPI, SQLAlchemy, React ani konkrétní model provider.
- Application use case přijímá porty/interfaces; infrastructure je implementuje.
- Router nesmí obsahovat orchestrace delší než validace vstupu, zavolání use case a mapování výstupu.
- Tool Gateway je jediná cesta, kterou agent spouští příkazy nebo zapisuje soubory.
- Přímý subprocess.run mimo infrastructure/tool_gateway je zakázán lint pravidlem nebo code review gate.
- Každý package má vlastní testy a veřejné rozhraní; interní implementace se neimportuje napříč moduly.

---

# 9. Domain Model

Doménový model je explicitní a nezávislý na UI a databázi. Následující entity tvoří minimální jádro.

| Entita | Klíčová pole | Účel |
| --- | --- | --- |
| Project | id, name, slug, source_type, source_location, default_branch, status, tags | Registrovaný samostatný softwarový projekt. |
| ProjectProfile | languages, frameworks, manifests, commands, architecture_summary, risk_flags | Výsledek ověřené analýzy projektu. |
| Workspace | id, project_id, path, strategy, base_revision, state, lease | Izolované pracovní prostředí pro job. |
| Goal | id, project_id, title, intent, constraints, priority, status | Uživatelský nebo systémový cíl. |
| Plan | id, goal_id, version, assumptions, steps, test_plan, risk_level | Schválený postup dosažení cíle. |
| Task | id, plan_id, type, dependencies, acceptance_criteria, status | Jednotka práce v rámci plánu. |
| Job | id, task_id, state, autonomy_level, budgets, checkpoint, worker_id | Perzistentní provedení úkolu. |
| AgentRun | id, job_id, role, model_id, input_digest, output_digest, status | Jedna role/model interakce. |
| ToolCall | id, agent_run_id, tool, args_redacted, policy_decision, exit_code | Deterministicky řízená akce nástroje. |
| Artifact | id, job_id, type, path, hash, size, metadata | Diff, log, report, build, screenshot nebo jiný výstup. |
| EvidenceEvent | id, sequence, event_type, payload_hash, previous_hash, timestamp | Append-only auditní událost. |
| Policy | id, scope, rule_type, effect, parameters, version | Bezpečnostní a provozní pravidla. |
| Approval | id, subject_type, subject_id, decision, reason, actor, timestamp | Lidské nebo policy schválení. |
| MemoryItem | id, project_id, category, claim, evidence_refs, confidence, validity | Dlouhodobá ověřená znalost. |

## 9.1 Identita a stavové invariants

- Všechna ID jsou UUIDv7 nebo ULID pro časové řazení.
- Job se nesmí dostat do COMPLETED bez VerificationResult PASS nebo explicitního override approval se zdůvodněním.
- Workspace může být přidělen nejvýše jednomu aktivnímu jobu, pokud není explicitně read-only shared.
- Artifact hash se počítá při vytvoření; změna souboru po registraci vytvoří nový artifact record.
- MemoryItem bez evidence_refs nesmí mít confidence=verified.
- Project removal je soft-delete/archive; fyzické mazání workspace a artefaktů je samostatná potvrzená operace.

---

## 9.2 Stavové automaty

```
PROJECT:
NEW -> PREFLIGHT -> INDEXING -> READY -> DEGRADED -> ARCHIVED
                    |            ^
                    +-> FAILED ---+

JOB:
QUEUED -> PREPARING -> RUNNING -> VERIFYING -> COMPLETED
   |          |           |            |
   |          |           +-> REPAIRING+
   |          +-> BLOCKED
   +-> CANCELLED
Any active state -> PAUSED -> previous safe state
Any active state -> FAILED

WORKSPACE:
CREATING -> READY -> LEASED -> DIRTY -> VERIFIED -> MERGED -> CLEANED
                    |          |            |
                    +-> BROKEN +-> REJECTED
```

# 10. Project Registry

## 10.1 Odpovědnost

Project Registry je centrální katalog všech projektů vybraných uživatelem. Uchovává metadata, zdroj, Git identitu, stav, profil, příkazy, politiky a vazby na joby. Není vlastníkem zdrojového kódu. Každý záznam musí být přenositelný a exportovatelný do YAML/JSON.

## 10.2 Přidání projektu

1. Normalizovat zadanou lokální cestu nebo Git URL.
2. Ověřit, že zdroj existuje a je čitelný.
3. Detekovat Git repository a aktuální revision. Pokud Git chybí, nabídnout inicializaci, ale neprovést ji bez schválení.
4. Spustit secret-aware scan názvů souborů a vzorů bez odesílání obsahu modelu.
5. Zjistit velikost, počet souborů a potenciálně nebezpečné typy souborů.
6. Vytvořit Project record ve stavu PREFLIGHT.
7. Spustit analyzéry a vytvořit baseline ProjectProfile.
8. Po úspěchu změnit stav na READY; při částečném výsledku na DEGRADED s přesným důvodem.

## 10.3 Projektový manifest

```yaml
schema_version: 1
project:
  name: TradePilot
  slug: tradepilot
  source:
    type: local_git
    path: /home/david/projects/tradepilot
  default_branch: main
  languages: [python, javascript]
  autonomy_default: assisted
commands:
  install: ["uv sync", "pnpm install --frozen-lockfile"]
  test: ["uv run pytest -q", "pnpm test --run"]
  lint: ["uv run ruff check .", "pnpm lint"]
  build: ["pnpm build"]
policies:
  network: deny_by_default
  protected_paths:
    - .env
    - secrets/
    - production/
  forbidden_commands:
    - "rm -rf /"
    - "git push --force"
  approvals:
    required_for:
      - apply_patch_to_primary
      - git_push
      - production_action
context:
  ignore:
    - .venv/
    - node_modules/
    - dist/
    - build/
    - "*.log"
```

---

# 11. Project Analysis Engine

## 11.1 Cíl

Analysis Engine vytváří ověřený, inkrementálně aktualizovaný model projektu. Nejde pouze o sumarizaci README. Analýza kombinuje deterministické detektory, Git metadata, parsery symbolů, manifests, testovací konfiguraci a modelové vysvětlení. Každý závěr musí rozlišovat mezi faktem, inferencí a neověřeným předpokladem.

## 11.2 Pipeline

| Fáze | Deterministický výstup | Volitelný modelový výstup |
| --- | --- | --- |
| Inventory | Seznam souborů, velikosti, typy, ignorované cesty. | Popis pravděpodobných subsystémů. |
| Language detection | Jazyky podle přípon a parserů. | Dopad kombinace jazyků na build. |
| Manifest scan | pyproject, package.json, pubspec, Cargo, Makefile, Docker. | Interpretace runtime a toolchainu. |
| Symbol index | Třídy, funkce, moduly, importy, routes, testy. | Architektonické role a hranice. |
| Git analysis | Branch, revision, dirty state, recent commits. | Shrnutí vývoje a rizik změn. |
| Command discovery | Test/build/lint scripts z manifestů a CI. | Doporučená verification matrix. |
| Risk scan | Secrets patterns, binaries, generated files, large files. | Prioritizace rizik. |
| Baseline execution | Bezpečné read-only nebo schválené testy. | Vysvětlení selhání a návrh dalších kroků. |

## 11.3 Inkrementální indexace

- Každý soubor má content hash, parser version a last indexed revision.
- Při změně se znovu parsují pouze změněné soubory a závislé symboly.
- Binary, dependency a build adresáře se ignorují podle globálních i projektových pravidel.
- Indexace se musí dát přerušit a obnovit.
- Modelové shrnutí se invaliduje pouze tehdy, když se změnily jeho zdrojové symboly nebo dokumenty.

## 11.4 Project health score

Health score je vysvětlitelný kompozitní ukazatel, nikoli marketingové číslo. Každá komponenta má samostatnou hodnotu a důkazy.

| Komponenta | Váha v první verzi | Příklad důkazu |
| --- | --- | --- |
| Build health | 20 % | Poslední build příkaz a exit code. |
| Test health | 25 % | Počet testů, pass/fail, flaky history. |
| Static quality | 10 % | Lint/typecheck výsledky. |
| Security posture | 15 % | Secrets scan, dependency audit, policy violations. |
| Documentation | 10 % | README, setup, architecture, command validity. |
| Reproducibility | 10 % | Lockfiles, clean install, deterministic scripts. |
| Maintenance risk | 10 % | Large modules, stale TODO, dependency age - pouze pokud data existují. |

# 12. Knowledge and Context Engine

## 12.1 Účel

Context Engine vybírá nejmenší dostatečný a důvěryhodný kontext pro konkrétní úkol. Nesmí posílat celý repozitář modelu ani spoléhat pouze na embeddings. Pro malé lokální modely je přesný výběr kontextu zásadní.

## 12.2 Typy kontextu

- Project identity: účel, stack, architektonické hranice a pravidla.
- Task context: cíl, constraints, acceptance criteria a schválený plán.
- Code context: relevantní symboly, importy, callers/callees, tests a config.
- Operational context: OS, příkazy, environment, poslední chyby a build stav.
- Historical context: předchozí podobné změny, známé opravy a rozhodnutí.
- Policy context: co je povoleno, zakázáno a co vyžaduje approval.

## 12.3 Retrieval strategie

1. Začít explicitními soubory a symboly z plánu.
2. Rozšířit o import graph a související testy.
3. Použít FTS nad dokumentací, commit messages a evidence.
4. Použít symbol relevance scoring podle typu úkolu.
5. Embeddings použít pouze jako doplňkový signál, nikoli jediný zdroj.
6. Sestavit context bundle s tokenovým rozpočtem, citacemi a důvěrou.
7. Po modelovém výstupu ověřit, zda navržené soubory skutečně existují a zda nebyly vynechány kritické závislosti.

## 12.4 Context bundle contract

```json
{
  "project": {"id": "...", "revision": "abc123", "profile_version": 7},
  "goal": {"id": "...", "intent": "...", "constraints": []},
  "plan": {"id": "...", "step": 3, "acceptance_criteria": []},
  "files": [
    {"path": "scanner.py", "hash": "...", "reason": "target symbol", "content": "..."}
  ],
  "symbols": [
    {"fq_name": "scanner.scan_market", "kind": "function", "source_ref": "scanner.py:80-145"}
  ],
  "tests": [],
  "history": [],
  "policies": [],
  "budget": {"max_input_tokens": 12000, "max_output_tokens": 4000},
  "provenance": {"generated_at": "...", "retriever_version": "..."}
}
```

---

# 13. Goal, Planning and Decision Engine

## 13.1 Goal contract

Každý implementační cíl musí být převzat z uživatelského požadavku do strukturovaného kontraktu. Nejasnosti se řeší před zápisem do kódu nebo jako explicitní assumptions, které musí být viditelné uživateli.

| Pole | Povinnost | Příklad |
| --- | --- | --- |
| Intent | MUST | Přidat import existujícího Git projektu. |
| Business/user outcome | MUST | Projekt se objeví na dashboardu a lze analyzovat jeho stav. |
| Scope | MUST | Backend endpoint, DB, UI form, testy. |
| Out of scope | MUST | Klonování privátního repozitáře přes OAuth. |
| Constraints | MUST | Linux-first, SQLite, bez Redis. |
| Acceptance criteria | MUST | Konkrétní ověřitelné výroky. |
| Risk level | MUST | low / medium / high / critical. |
| Approval gates | MUST | Před zápisem, před merge, před externí akcí. |

## 13.2 Planner output

Planner nevydává pouze seznam úkolů. Výstup je verzovaný plán s dependency graph, změnovou plochou, testy, rollbackem a rozpočty.

```
Plan
- Summary
- Assumptions and unresolved questions
- Affected modules and files
- Ordered steps
- Dependencies between steps
- Data migration impact
- Security impact
- Test matrix
- Rollback strategy
- Estimated tool/model budget
- Approval gates
- Definition of done
```

## 13.3 Plánovací pravidla

- Jedna task položka má mít výsledek ověřitelný jedním nebo několika konkrétními testy.
- Planner nesmí kombinovat rozsáhlou refaktorizaci a novou funkci bez oddělených kroků.
- Změna databázového schématu vyžaduje migraci, backup/rollback poznámku a integrační test.
- High-risk cíl se automaticky rozděluje na read-only průzkum, návrh, implementaci a schválení.
- Pokud chybí spustitelné testy, první krok je vytvoření nebo oprava minimálního testovacího harnessu.
- Plán musí uvést, které části jsou deterministicky ověřitelné a které vyžadují lidské posouzení.

---

# 14. Agent Runtime

## 14.1 Zásada

Agent Runtime je workflow engine, nikoli skupina nekontrolovaných procesů. Agent je role se vstupním kontraktem, nástroji, rozpočtem, povoleným kontextem a výstupním schématem. V MVP mohou všechny role používat stejný model, ale odlišné systémové instrukce a tool permissions.

## 14.2 Role agentů

| Role | Odpovědnost | Povolené akce v MVP |
| --- | --- | --- |
| Analyzer | Zmapuje stav projektu a shromáždí důkazy. | Read files, Git read, safe discovery commands. |
| Architect | Navrhne hranice, kontrakty a dopady. | Read-only; vytváří decision proposal. |
| Planner | Rozloží cíl a vytvoří testovatelný plán. | Read-only; zapisuje Plan artifact. |
| Implementer | Vytvoří omezený patch podle plánu. | Write pouze workspace; žádný push. |
| Tester | Spustí předem povolenou verification matrix. | Command allowlist; read outputs. |
| Debugger | Diagnostikuje konkrétní failure evidence. | Read logs/code; omezené experimenty. |
| Reviewer | Kontroluje diff proti plánu a invariants. | Read-only; může blokovat gate. |
| Security Auditor | Kontroluje policies, secrets a rizikové změny. | Read-only scanners; blokující výstup. |
| Documenter | Aktualizuje dokumentaci odpovídající změně. | Write docs v workspace. |
| Release Coordinator | Připraví commit/release report. | Bez publikace v MVP bez approval. |

## 14.3 Standardní implementační workflow

```
ANALYZE
  -> PLAN
  -> PLAN_REVIEW_GATE
  -> PREPARE_WORKSPACE
  -> IMPLEMENT
  -> STATIC_REVIEW
  -> VERIFY
      -> PASS -> HUMAN/Policy APPROVAL -> APPLY/MERGE
      -> FAIL -> DIAGNOSE -> REPAIR -> VERIFY
                    \-> budget exhausted -> BLOCKED/FAILED
```

## 14.4 Rozpočty a limity

| Limit | Výchozí hodnota MVP | Chování při překročení |
| --- | --- | --- |
| Max model calls per task | 20 | Job se pozastaví a vytvoří budget report. |
| Max repair iterations | 3 | Job BLOCKED s nejlepší diagnózou a zbývajícími možnostmi. |
| Max command runtime | 120 s běžně; per-command override | Process terminate -> kill; uložit stdout/stderr. |
| Max workspace disk growth | 2 GB | Zastavit zápis, reportovat největší soubory. |
| Max concurrent heavy jobs on 8 GB | 1 | Ostatní zůstávají QUEUED. |
| Max context input | Provider-specific | Context Engine zkrátí a uvede vynechané zdroje. |
| Max patch size before manual review | 500 changed lines default | Vyžádat approval nebo rozdělení úkolu. |

---

# 15. Model Router

## 15.1 Požadavky

- Jednotné rozhraní pro chat/completion, structured output, embeddings volitelně a health check.
- Provider konfigurace nesmí být rozptýlená v agentním kódu.
- Každý model run zaznamená provider, model, parametry, token usage pokud dostupné, latency a hash prompt bundle.
- Secrets se předávají provider adapteru přes secret store a nikdy se neukládají do evidence v otevřené podobě.
- Router musí umět fallback pouze podle explicitní policy; nesmí tajně odeslat lokální data do cloudu.

## 15.2 Routing policy

| Typ úkolu | Preferovaný model | Fallback |
| --- | --- | --- |
| Rychlá klasifikace a sumarizace | Malý lokální model | Větší lokální model. |
| Plánování středního úkolu | Nejlepší dostupný lokální reasoning model | Cloud pouze po povolení projektu. |
| Generování patchů | Coding model s přesným structured output | Jiný coding provider po explicitní policy. |
| Security review | Samostatný review pass; ideálně jiný model/konfigurace | Deterministické scanners zůstávají povinné. |
| Embeddings | Lokální embedding model | FTS-only mode. |

## 15.3 Structured output

Modelové výstupy pro plán, patch proposal, diagnosis a review musí být validovány Pydantic schématy. Pokud validace selže, runtime smí provést nejvýše definovaný počet repair prompts. Nevalidní text nesmí přímo měnit stav jobu.

---

# 16. Tool Gateway a bezpečné provádění příkazů

## 16.1 Jediný exekuční bod

Veškeré agentní interakce s filesystemem, Gitem, shellem, testy a externí sítí procházejí Tool Gateway. Gateway provede autorizaci, normalizaci argumentů, path containment, resource limits, secret redaction, audit a vytvoření ToolCall evidence.

## 16.2 Kategorie nástrojů

| Kategorie | Příklady | Výchozí policy |
| --- | --- | --- |
| Read | read_file, list_tree, grep, symbol_lookup | Povoleno uvnitř projektového scope, secrets redacted. |
| Git read | status, diff, log, show, rev-parse | Povoleno. |
| Workspace write | write_file, apply_patch, mkdir, delete generated file | Pouze leased workspace a approved task. |
| Command | pytest, npm test, build, lint | Allowlist podle project manifestu. |
| Git mutation | branch, add, commit, merge | Vyžaduje úroveň autonomie a gates. |
| Network | package install, HTTP API, Git fetch | Deny by default; per-project allowlist. |
| External side effect | deploy, publish, send email, trade order | Zakázáno v MVP nebo explicitní critical approval. |

## 16.3 Command policy

- Preferovat argv pole bez shell=True.
- Při nutnosti shell syntaxe použít explicitní shell tool s přísnější policy a logem.
- Canonicalize pracovní adresář a všechny path argumenty; ověřit containment po vyhodnocení symlinků.
- Zakázat environment inheritance; vytvořit allowlist environment proměnných.
- Maskovat hodnoty odpovídající secret registry ve stdout/stderr.
- Limitovat CPU, paměť, počet procesů, čas a velikost výstupu podle možností OS.
- Příkaz s neznámou binárkou vyžaduje approval nebo doplnění manifestu.
- Instalační příkazy jsou oddělené od testů a mají síťovou policy.

## 16.4 Minimální command decision record

```json
{
  "decision": "allow | deny | require_approval",
  "rule_ids": ["CMD-ALLOW-PYTEST", "PATH-WORKSPACE-ONLY"],
  "normalized_argv": ["uv", "run", "pytest", "-q"],
  "cwd": "/.../var/workspaces/job-123/repo",
  "limits": {"timeout_s": 120, "max_output_bytes": 5000000},
  "network": "deny",
  "redactions": ["OPENAI_API_KEY"],
  "reason": "Project manifest test command"
}
```

---

# 17. Workspace Manager

## 17.1 Strategie workspace

| Strategie | Použití | Výhody | Rizika |
| --- | --- | --- | --- |
| Git worktree | Čistý Git projekt a lokální branch. | Rychlé, sdílí objekty, standardní diff. | Je nutná správná správa větví a cleanup. |
| Filesystem copy | Non-Git projekt nebo experiment. | Jednoduchá izolace. | Disk, pomalé kopie, nutnost vlastního diffu. |
| Container bind workspace | Vyšší izolace později. | Oddělení runtime. | Vyšší režie, komplexita. |
| Read-only direct | Analýza bez zápisu. | Minimální disk a čas. | Nesmí být použito pro implementaci. |

## 17.2 Lease a fencing

Každý mutující job získá lease na workspace s fencing tokenem. Tool Gateway kontroluje token při každé write akci. Po vypršení nebo ztrátě lease se zápis zamítne. Tím se brání tomu, aby po restartu pokračoval starý worker a současně nový worker zapisoval do stejného workspace.

## 17.3 Cleanup policy

- Úspěšný merged workspace lze automaticky odstranit až po retention době.
- Failed nebo rejected workspace se zachová pro debugging podle diskového limitu.
- Cleanup nikdy nemaže originální projektovou cestu.
- Před mazáním vznikne workspace manifest s branch, revision, artifact refs a důvodem.

---

# 18. Patch Engine

## 18.1 Požadavky

- Přijímá unified diff nebo strukturované file operations.
- Ověřuje base file hashes před aplikací, aby zabránil patchování změněného kontextu.
- Zakazuje zápis mimo workspace a do protected paths.
- Po aplikaci vytvoří nový diff vůči base revision, nikoli pouze důvěru v modelový patch.
- Detekuje binární změny, velké generated soubory a změny lockfile.
- Umožňuje revert celé změny nebo jednotlivých file operations.

## 18.2 Patch review metadata

| Položka | Obsah |
| --- | --- |
| Intent link | Který goal/task a acceptance criterion změna plní. |
| Files changed | Počet a seznam, insertions/deletions. |
| Risk flags | Auth, secrets, DB migration, network, finance, destructive behavior. |
| Generated files | Explicitní označení a důvod. |
| Tests affected | Nové/upravené testy a jejich relevance. |
| Reviewer findings | Blockers, warnings, suggestions. |
| Verification result | Přesný run a artifact refs. |

---

# 19. Verification Engine

## 19.1 Verification matrix

Verification Engine rozhoduje na základě manifestu projektu, typu změny a risk policy. Jediný příkaz pytest není univerzální důkaz. Matice může kombinovat rychlé checks a pomalejší gates.

| Vrstva | Příklady | Kdy povinná |
| --- | --- | --- |
| Syntax/format | ruff format --check, prettier --check | Každý relevantní projekt. |
| Static analysis | ruff, mypy/pyright, eslint, tsc | Pokud je v projektu nakonfigurováno. |
| Unit tests | pytest unit, vitest | Každá změna doménové logiky. |
| Integration tests | API + DB, filesystem/Git adapter | Změna rozhraní nebo infrastruktury. |
| E2E | Playwright hlavní flow | UI workflow nebo release candidate. |
| Build | Vite build, package build | Před merge pro buildované projekty. |
| Security | secret scan, dependency audit, policy scan | Risk medium+ a release. |
| Regression | Test reprodukující původní chybu | Bug fix. |
| Performance | Budget benchmark | Hot path nebo explicitní performance task. |

## 19.2 Result classification

| Stav | Význam |
| --- | --- |
| PASS | Všechny povinné checks prošly a žádný blocking policy finding. |
| PASS_WITH_WARNINGS | Povinné checks prošly; warnings musí být viditelné a nesmí být blocker. |
| FAIL_CODE | Selhání způsobené změnou nebo projektem. |
| FAIL_ENVIRONMENT | Chybí dependency, služba, místo, oprávnění nebo runtime. |
| FAIL_FLAKY | Výsledek není stabilní; vyžaduje opakování a označení flaky evidence. |
| BLOCKED_POLICY | Test nebo příkaz nelze spustit kvůli policy. |
| INCONCLUSIVE | Nedostatek důkazů; nesmí být považováno za PASS. |

## 19.3 Verification report

```
Verification Report
- Project revision and workspace revision
- Change digest
- Environment fingerprint
- Commands executed in order
- Exit codes, duration, truncated output references
- Test counts and failures
- Policy findings
- Artifact hashes
- Result classification
- Remaining uncertainty
- Reproduction command
```

---

# 20. Repair Loop

## 20.1 Cíl

Repair Loop automatizuje omezený cyklus diagnose -> hypothesis -> minimal fix -> verify. Nesmí se stát nekonečným generátorem změn. Každá iterace musí vycházet z konkrétního failure evidence a změnit hypotézu nebo zásah.

## 20.2 Algoritmus

1. Klasifikovat failure: code, test, environment, flaky, policy nebo unknown.
2. Extrahovat minimální relevantní log a source context.
3. Vytvořit seřazené hypotézy s supporting/contradicting evidence.
4. Vybrat nejmenší bezpečný experiment nebo patch.
5. Aplikovat změnu v samostatném repair checkpointu.
6. Spustit nejprve targeted test, poté plnou požadovanou verification matrix.
7. Při úspěchu vytvořit explanation a regression evidence.
8. Při selhání aktualizovat hypotézy; neopakovat stejný patch.
9. Po vyčerpání rozpočtu označit BLOCKED a předat uživateli nejlepší diagnózu a konkrétní možnosti.

## 20.3 Anti-loop pravidla

- Hash patchů a příkazů brání opakování stejné iterace.
- Každá iterace má limit změněných řádků.
- Repair nesmí rozšiřovat původní scope bez approval.
- Pokud je failure environmentální, nesmí implementer měnit produkční kód jen proto, aby test prošel.
- Zakázáno je vypínání testů, snižování assertions nebo catch-all potlačení chyb bez explicitního schválení.

---

# 21. Guardian Security and Governance

## 21.1 Autonomy levels

| Úroveň | Název | Povolení |
| --- | --- | --- |
| 0 | Observe | Pouze inventura, čtení, indexace a report. |
| 1 | Plan | Může vytvářet plány, ale žádné změny workspace. |
| 2 | Assisted | Může vytvořit patch v workspace; každý významný krok vyžaduje approval. |
| 3 | Supervised autonomous | Může provést schválený plán a repair v limitech; merge/push vyžaduje approval. |
| 4 | Trusted local autonomous | Může automaticky aplikovat low-risk změny do lokální branch po plném PASS. |
| 5 | External side effects | Deployment, publikace nebo produkční akce. Není součástí MVP a vždy critical policy. |

## 21.2 Policy scopes

- Global: platí pro celou instalaci.
- Project: pravidla konkrétního projektu.
- Workspace/job: dočasné omezení pro jednu úlohu.
- Tool: povolené argumenty, síť, cesty, timeout.
- Data classification: public, internal, confidential, secret.
- Action risk: low, medium, high, critical.

## 21.3 Threat model

| Hrozba | Kontrola |
| --- | --- |
| Prompt injection v repozitáři | Repo text je nedůvěryhodný data context, nikoli systémová instrukce; tool calls vždy policy-check. |
| Path traversal / symlink escape | Canonical path containment a zákaz zápisu přes symlink mimo workspace. |
| Secret exfiltration | Secret detection, redaction, provider data policy, network deny. |
| Destruktivní příkaz | Command allowlist, argv parsing, no shell by default, approval. |
| Supply-chain skript při install | Oddělený install gate, network policy, sandbox, log. |
| Malicious test | Resource limits, workspace isolation, volitelný container. |
| Stale worker zápis | Lease + fencing token. |
| Audit tampering | Hash-chained evidence events a artifact hashes. |
| Model halucinace | Existence checks, schema validation, tests, reviewer role. |
| Cross-project data leak | Project-scoped context, separate secret scopes, explicit cross-project links. |

## 21.4 Protected actions

- Čtení .env, SSH klíčů, cloud credentials a browser profiles.
- Mazání nebo přepis originálního repozitáře.
- Git push, force push, tag, release a merge do chráněné větve.
- Package publication, deployment, odeslání e-mailu nebo zprávy.
- Finanční transakce, live trading, změna účtu nebo API oprávnění.
- Změna Guardian policies a auditního ledgeru.

---

# 22. Evidence Ledger a auditovatelnost

## 22.1 Událostní model

Evidence Ledger je append-only chronologický záznam. Operační databáze může uchovávat aktuální stav, ale důležité přechody musí být rekonstruovatelné z událostí. Každá událost odkazuje na předchozí hash a obsahuje hash payloadu.

```
EvidenceEvent {
  id,
  sequence,
  timestamp,
  project_id,
  job_id,
  actor_type,        # user | policy | agent | worker | system
  actor_id,
  event_type,
  payload_json,
  payload_hash,
  previous_event_hash,
  event_hash,
  artifact_refs[]
}
```

## 22.2 Povinné event types

- PROJECT_REGISTERED, PROJECT_ANALYZED, PROFILE_UPDATED
- GOAL_CREATED, PLAN_PROPOSED, PLAN_APPROVED, PLAN_REJECTED
- JOB_QUEUED, JOB_STARTED, JOB_PAUSED, JOB_RESUMED, JOB_FINISHED
- WORKSPACE_CREATED, WORKSPACE_LEASED, WORKSPACE_RELEASED
- MODEL_RUN_STARTED, MODEL_RUN_FINISHED, MODEL_OUTPUT_REJECTED
- TOOL_REQUESTED, TOOL_ALLOWED, TOOL_DENIED, TOOL_FINISHED
- PATCH_PROPOSED, PATCH_APPLIED, PATCH_REVERTED
- VERIFICATION_STARTED, CHECK_FINISHED, VERIFICATION_FINISHED
- APPROVAL_REQUESTED, APPROVAL_DECIDED
- MEMORY_PROPOSED, MEMORY_VERIFIED, MEMORY_INVALIDATED

## 22.3 Důkazní balíček úkolu

Po ukončení jobu FADE vytvoří adresář nebo archiv obsahující plan.json, environment.json, diff.patch, commands.jsonl, verification.json, report.md, artifact manifest a ledger slice. Tento balíček musí být čitelný i bez běžícího FADE serveru.

---

# 23. Continuity, checkpointy a recovery

## 23.1 Checkpoint contract

| Checkpoint obsah | Poznámka |
| --- | --- |
| Job state + current step | Stav se ukládá transakčně. |
| Workspace revision/hash | Ověření, že workspace nebyl změněn mimo FADE. |
| Completed tool calls | Idempotency keys zabraňují opakování side effects. |
| Agent summary | Strukturovaný stav, nikoli pouze celý chat. |
| Budgets consumed | Model calls, čas, disk, repair iterations. |
| Pending approval | Obnova přesně na gate. |
| Artifact refs | Všechny doposud vzniklé důkazy. |

## 23.2 Recovery při startu

1. Otevřít SQLite a ověřit migrace/integritu.
2. Najít joby v aktivním stavu bez platného worker heartbeat.
3. Označit je RECOVERING, nikoli okamžitě FAILED.
4. Ověřit workspace path, lease, revision a artifact hashes.
5. Zneplatnit starý fencing token a vydat nový.
6. Pokud poslední akce byla idempotentní a dokončení je doložené, pokračovat dalším krokem.
7. Pokud stav nelze bezpečně určit, přejít do BLOCKED a vyžádat ruční rozhodnutí.

## 23.3 Backup

- Pravidelný SQLite online backup nebo VACUUM INTO.
- Kopie config, policies, project registry exports a encryption metadata.
- Artefakty mohou mít retention; ledger a final reports mají delší retention.
- Restore runbook musí být testován automatizovaným integračním testem.

---

# 24. Persistence a fyzický datový model

## 24.1 SQLite režim

- WAL mode, foreign_keys=ON, busy_timeout nastavený.
- Jeden migrační proces; workers používají krátké transakce.
- Velké logy a artefakty nejsou BLOB v hlavních tabulkách; jsou na disku s hash referencí.
- JSON pole jsou používána omezeně; často dotazované hodnoty mají vlastní sloupce.

## 24.2 Minimální schéma - koncept

```sql
projects(id, slug, name, source_type, source_location, status,
         default_branch, created_at, updated_at, archived_at)
project_profiles(id, project_id, version, revision, profile_json, created_at)
goals(id, project_id, title, intent, constraints_json, priority, status, created_at)
plans(id, goal_id, version, status, plan_json, created_at, approved_at)
tasks(id, plan_id, ordinal, type, status, task_json)
jobs(id, task_id, workspace_id, state, autonomy_level,
     budget_json, checkpoint_json, worker_id, created_at, updated_at)
workspaces(id, project_id, path, strategy, base_revision, branch,
           state, lease_token, lease_expires_at)
agent_runs(id, job_id, role, provider, model, status, metrics_json,
           input_digest, output_digest, created_at, finished_at)
tool_calls(id, agent_run_id, tool_name, decision, request_json,
           result_json, exit_code, created_at, finished_at)
artifacts(id, project_id, job_id, type, path, sha256, size_bytes,
          metadata_json, created_at)
evidence_events(id, sequence, project_id, job_id, event_type,
                payload_json, payload_hash, previous_hash, event_hash, created_at)
policies(id, scope_type, scope_id, rule_type, effect, parameters_json,
         version, enabled, created_at)
approvals(id, subject_type, subject_id, decision, reason, actor,
          created_at)
memory_items(id, project_id, category, claim, confidence, validity,
             evidence_refs_json, created_at, invalidated_at)
```

## 24.3 Filesystem layout

```
~/.fade/
├── config.toml
├── secrets/                 # permissions 0700, encrypted where possible
├── fade.db
├── workspaces/
│   └── <project>/<job-id>/
├── artifacts/
│   └── <project>/<yyyy>/<mm>/<job-id>/
├── indexes/
│   └── <project-id>/
├── logs/
├── backups/
└── locks/
```

---

# 25. API Specification

## 25.1 API zásady

- REST JSON pro commands/queries a Server-Sent Events nebo WebSocket pro job timeline/log stream.
- Pydantic request/response modely; žádné nevalidované dict payloady v aplikační vrstvě.
- Idempotency-Key pro create job, approval a mutující operace, kde může klient opakovat request.
- Optimistic concurrency přes version/ETag u editace manifestu a policies.
- Chyby mají stable error_code, human_message, details a correlation_id.

## 25.2 Core endpoints

| Method | Path | Účel |
| --- | --- | --- |
| GET | /api/v1/system/health | Health a capability summary. |
| GET | /api/v1/system/doctor | Diagnostika runtime, Git, Python, Node, disk, model providers. |
| GET | /api/v1/projects | Seznam a filtry projektů. |
| POST | /api/v1/projects | Registrace projektu a spuštění preflightu. |
| GET | /api/v1/projects/{id} | Detail projektu. |
| PATCH | /api/v1/projects/{id} | Metadata, tags, policies reference. |
| POST | /api/v1/projects/{id}/analyze | Nová nebo inkrementální analýza. |
| GET | /api/v1/projects/{id}/profile | Poslední ověřený profil. |
| GET | /api/v1/projects/{id}/health | Health components a evidence. |
| POST | /api/v1/projects/{id}/goals | Vytvoření cíle. |
| POST | /api/v1/goals/{id}/plan | Vytvoření plan proposal. |
| POST | /api/v1/plans/{id}/approve | Schválení plánu. |
| POST | /api/v1/plans/{id}/jobs | Spuštění implementačního jobu. |
| GET | /api/v1/jobs/{id} | Stav a checkpoint summary. |
| POST | /api/v1/jobs/{id}/pause | Bezpečné pozastavení. |
| POST | /api/v1/jobs/{id}/resume | Pokračování. |
| POST | /api/v1/jobs/{id}/cancel | Cancel s cleanup policy. |
| GET | /api/v1/jobs/{id}/events | Timeline nebo SSE stream. |
| GET | /api/v1/jobs/{id}/artifacts | Artefakty jobu. |
| GET | /api/v1/jobs/{id}/diff | Normalizovaný diff a review metadata. |
| POST | /api/v1/jobs/{id}/approvals | Rozhodnutí o pending gate. |
| POST | /api/v1/jobs/{id}/apply | Aplikace/merge ověřené změny podle policy. |
| GET | /api/v1/policies | Efektivní policies. |
| PUT | /api/v1/projects/{id}/manifest | Verzovaná změna projektového manifestu. |
| GET | /api/v1/models | Providers, modely, health a capabilities. |
| POST | /api/v1/models/test | Bezpečný provider test bez projektových dat. |

## 25.3 Příklad vytvoření cíle

```json
POST /api/v1/projects/{project_id}/goals
{
  "title": "Přidat bezpečný import lokálního Git projektu",
  "intent": "Uživatel vybere cestu a po preflightu se projekt objeví v registru.",
  "constraints": [
    "Nevytvářet kopii zdrojů při read-only preflightu",
    "Nečíst obsah .env",
    "Linux-first"
  ],
  "acceptance_criteria": [
    "Validní Git cesta vrátí 201 a Project ve stavu PREFLIGHT",
    "Neexistující cesta vrátí stable error PROJECT_PATH_NOT_FOUND",
    "Symlink mimo allowed roots je zamítnut",
    "UI zobrazí průběh a konečný stav"
  ],
  "priority": "high"
}
```

---

# 26. Frontend a UX architektura

## 26.1 Hlavní obrazovky

| Obrazovka | Obsah | Primární akce |
| --- | --- | --- |
| Portfolio Dashboard | Project cards, health, active jobs, risks, recent evidence. | Přidat projekt, otevřít projekt, pokračovat v jobu. |
| Add Project Wizard | Source, preflight, detected stack, manifest review. | Registrovat nebo opravit vstup. |
| Project Overview | Purpose, architecture map, health, goals, commands, policies. | Analyze, create goal, edit manifest. |
| Project Explorer | Read-only tree, symbols, search, dependency relations. | Přidat soubor/symbol do goal contextu. |
| Goal & Plan | Intent, assumptions, scope, steps, test plan, risks. | Approve, reject, edit constraints. |
| Job Console | State, current step, live events, budgets, approvals. | Pause, cancel, approve gate. |
| Diff Review | Files, side-by-side diff, findings, test result. | Accept, request repair, reject. |
| Evidence Report | Commands, logs, tests, hashes, timeline. | Export package. |
| Models & Tools | Provider health, routing, tool capabilities. | Test provider, change defaults. |
| Guardian Policies | Autonomy, protected actions, effective rules. | Edit policy with confirmation. |
| System Doctor | Dependencies, disk, workers, DB, backups. | Run repairable diagnostics. |

## 26.2 UX pravidla

- Nikdy neskrývat rozdíl mezi návrhem modelu a skutečně provedenou akcí.
- Každý stav má lidské vysvětlení a další možnou akci.
- Blocking approval musí ukázat přesně, která policy jej vyvolala.
- Live log je doplněk; důležité výsledky jsou strukturované karty a reporty.
- Risk barvy nejsou jediný nositel informace; vždy textový štítek a důvod.
- Dashboard nesmí načítat celé logy nebo diffs; používá stránkování a lazy loading.
- Uživatel musí před externí nebo destruktivní akcí vidět shrnutí dopadu v běžném jazyce.

## 26.3 Frontend route map

```
/
/projects/new
/projects/:projectId
/projects/:projectId/explorer
/projects/:projectId/goals
/goals/:goalId/plan
/jobs/:jobId
/jobs/:jobId/diff
/jobs/:jobId/evidence
/models
/policies
/system/doctor
/settings
```

---

# 27. Eventing, jobs a worker runtime

## 27.1 DB-backed queue MVP

MVP nepoužívá Redis. Tabulka jobs a atomický claim mechanismus tvoří durable queue. Worker vybírá QUEUED job, v transakci nastaví worker_id, lease a PREPARING. Heartbeat obnovuje lease. Po pádu lze job reclaimnout podle recovery pravidel.

## 27.2 Event delivery

- Každá významná změna stavu zapíše evidence event v téže transakci nebo přes outbox pattern.
- Frontend získává stream přes SSE. Při reconnectu posílá last_event_id a doplní chybějící události.
- Log chunks mají sekvenční číslo a velikostní limit.
- Consumer nesmí předpokládat přesně jednou doručení; UI a workers jsou idempotentní.

## 27.3 Scheduler

- Rozlišuje light, medium a heavy job podle modelu, build příkazů a projektu.
- Na 8 GB je výchozí max_concurrent_heavy=1 a max_concurrent_light=2.
- Projekt může mít jen jeden mutující job na stejnou base branch.
- Read-only analýzy lze paralelizovat, pokud nevyčerpají memory budget.
- Scheduler kontroluje volný disk před vytvořením workspace a modelu.

---

# 28. Integrace s Git

## 28.1 Git workflow MVP

1. Zachytit base revision a dirty state originálního projektu.
2. Pokud originální projekt obsahuje necommitnuté změny, read-only analýza je možná, mutující job vyžaduje explicitní strategii.
3. Vytvořit worktree a branch fade/<job-id>-<slug>.
4. Aplikovat změny pouze ve worktree.
5. Po PASS vytvořit volitelný lokální commit se standardní message a trailers.
6. Zobrazit diff a evidence.
7. Po approval merge/cherry-pick do zvolené lokální větve. Push není default.

## 28.2 Commit metadata

```
feat(project): concise summary

Why:
- linked goal outcome

Verification:
- command and PASS result

FADE-Goal: <goal-id>
FADE-Job: <job-id>
FADE-Evidence: <artifact-hash>
```

## 28.3 Konflikty

Pokud se base branch od vytvoření workspace změnila, FADE nesmí slepě mergeovat. Vytvoří stale-base finding, nabídne rebase v izolaci a zopakuje verification. Konfliktní automatická oprava je nový risk gate.

---

# 29. Secrets, konfigurace a data classification

## 29.1 Secret storage

- MVP podporuje environment variables a lokální secret file s permissions 0600/0700.
- Preferovaná budoucí integrace je OS keyring nebo age/sops encrypted store.
- API nikdy nevrací secret value po uložení; pouze status a poslední ověření.
- Secret je scopeován globálně, providerem nebo projektem.
- Tool dostane pouze secrets explicitně deklarované v command capability.

## 29.2 Redaction

- Redaction registry obsahuje přesné hodnoty i patterny tokenů.
- Maskování proběhne před persistencí stdout/stderr a před odesláním do modelu.
- Při nalezení pravděpodobného nového secretu se job zastaví podle severity a vytvoří finding bez celé hodnoty.

## 29.3 Konfigurace

```toml
[system]
data_dir = "~/.fade"
log_level = "INFO"
max_concurrent_light = 2
max_concurrent_heavy = 1

[database]
url = "sqlite:///~/.fade/fade.db"
wal = true

[guardian]
default_autonomy = 1
network_default = "deny"
workspace_roots = ["~/projects", "~/fade-workspaces"]

[models.local]
provider = "ollama"
base_url = "http://127.0.0.1:11434"
default_model = "small-coder"

[artifacts]
retention_days_failed = 30
retention_days_success = 90
max_total_gb = 20
```

---

# 30. Observability a provozní diagnostika

## 30.1 Structured logging

Každý log record má timestamp, level, service, correlation_id, project_id, job_id, event a safe fields. Model prompt ani secret se neloguje. Velké stdout/stderr je artifact, nikoli jeden log record.

## 30.2 Metriky

| Metrika | Účel |
| --- | --- |
| fade_jobs_total{state,type} | Objem a výsledky práce. |
| fade_job_duration_seconds | Doba podle typu a fáze. |
| fade_tool_calls_total{tool,decision} | Povolené/zakázané akce. |
| fade_model_calls_total{provider,model,status} | Spolehlivost a použití modelů. |
| fade_verification_checks_total{result} | Kvalita změn a flaky rate. |
| fade_repair_iterations | Kolik oprav je potřeba. |
| fade_workspace_bytes | Disková spotřeba. |
| fade_queue_depth | Zatížení scheduleru. |

## 30.3 System Doctor checks

- Python, uv, Node, pnpm a Git verze.
- Zápis do data dir, permissions secrets, volný disk.
- SQLite integrity_check a migration status.
- Worker heartbeat a stale leases.
- Ollama/provider health a model availability.
- Testovací vytvoření a cleanup workspace.
- Poslední backup a test restore metadata.

---

# 31. Výkonnostní a resource budgets

## 31.1 Cíle pro 8 GB RAM

| Operace | Cíl |
| --- | --- |
| Cold start API | < 5 s bez startu modelu. |
| Dashboard first meaningful data | < 2 s pro 100 projektů z lokální DB. |
| Register small project preflight | < 10 s bez modelové sumarizace. |
| Incremental analysis | Zpracovat pouze změněné soubory; UI průběžně reaguje. |
| Idle memory control plane + UI | Cílit pod 1 GB celkem. |
| Heavy model concurrency | 1 lokální modelová úloha současně. |
| SSE event latency | < 1 s lokálně. |
| Cancellation response | Proces terminate do 2 s, kill fallback do dalších 5 s. |

## 31.2 Strategie úspor

- Lazy load parserů a providerů.
- Inkrementální index a content hashes.
- FTS5 jako baseline místo povinné vektorové DB.
- Subprocess izolace těžkých analýz, aby šla paměť uvolnit ukončením procesu.
- Omezené log bufferování a stream do souboru.
- Model unload/keepalive konfigurace podle dostupné RAM.

---

# 32. Testovací strategie FADE platformy

## 32.1 Test pyramid

| Vrstva | Obsah | Frekvence |
| --- | --- | --- |
| Unit | Domain invariants, policies, state machines, parsers, scoring. | Každý commit. |
| Component | Use cases s fake ports, React components. | Každý commit. |
| Integration | SQLite, Git wrapper, filesystem, subprocess, provider fake. | Každý PR/milník. |
| Security | Path escape, command injection, secret redaction, policy bypass. | Každý security-relevant change. |
| E2E | Add project -> analyze -> goal -> plan -> patch -> verify -> evidence. | Release candidate a významné změny flow. |
| Chaos/recovery | Kill worker, restart API, stale lease, partial artifact. | Milníky continuity a release. |
| Compatibility fixtures | Python, Node, mixed, Flutter, C project fixtures. | Analysis/tool changes. |

## 32.2 Povinné kritické testy

- Symlink z workspace mimo povolený root nemůže být zapsán.
- Příkaz s shell injection payloadem je zamítnut nebo bezpečně předán jako argv.
- Secret ve stdout je v persisted artifact redacted.
- Dva workers nemohou současně držet validní lease na mutující workspace.
- Po kill -9 workeru se job obnoví bez opakování dokončeného patch apply.
- Job nemůže přejít do COMPLETED s neúspěšným verification gate.
- Repo obsahující prompt injection text nezmění system policies ani tool permissions.
- Projekt A nemůže načíst soubor projektu B přes API ID manipulaci.
- Database migration má upgrade i ověřený backup/restore postup.

## 32.3 Golden fixture projects

- tiny-python: FastAPI + pytest.
- tiny-node: Vite/TypeScript + Vitest.
- mixed-stack: Python backend + JS frontend.
- broken-build: známá reprodukovatelná chyba pro Repair Loop.
- malicious-repo: prompt injection, symlink, fake secrets, destructive scripts.
- non-git-project: filesystem copy strategy.
- large-tree-synthetic: výkon indexace a ignore rules.

---

# 33. Definition of Done

## 33.1 DoD pro jednu funkci

- Požadavek je propojen s goal/task a acceptance criteria.
- Architektonická hranice je zachována; odchylka má ADR.
- Kód má unit/integration test podle dopadu.
- Relevantní lint/typecheck/build prochází.
- Security impact je posouzen a policies nejsou obcházeny.
- API a UI chybové stavy jsou implementované, nejen happy path.
- Dokumentace a project manifest jsou aktualizované.
- Evidence report obsahuje reprodukční příkazy.
- Žádné secrets, debug hacks, vypnuté testy nebo nezdokumentované TODO blokující kvalitu.

## 33.2 DoD pro milník

- Všechny milestone acceptance tests prošly v čistém prostředí.
- Upgrade od předchozího milníku je otestován.
- System Doctor nehlásí blocker.
- Backup/restore je otestován, pokud milník mění persistenci.
- E2E hlavní flow funguje bez ručních DB zásahů.
- Známá omezení a rizika jsou uvedena v release notes.
- Backlog a dokumentace odpovídají skutečnému stavu, ne plánovanému stavu.

---

# 34. Implementační roadmapa

## 34.1 Fáze 0 - Foundation and Architecture Lock

- Inicializovat repository, uv/pnpm workspace, CI local scripts a docs.
- Implementovat domain model skeleton, settings, structured logging a error format.
- Založit ADR proces a architektonické dependency tests.
- Výstup: API health, web shell, test harness, doctor skeleton.

## 34.2 Fáze 1 - Project Registry and Preflight

- SQLite/Alembic, Project CRUD, local path source, archive.
- Preflight detektory, Git status, manifests, protected files.
- Add Project Wizard a portfolio dashboard.
- Výstup: bezpečné přidání projektů a základní portfolio.

## 34.3 Fáze 2 - Analysis and Project Profile

- File inventory, ignore rules, language/framework detection.
- Symbol extraction pro Python a TypeScript jako první.
- Command discovery a baseline health checks.
- Project Overview, Explorer a export profile.

## 34.4 Fáze 3 - Durable Jobs and Evidence

- DB queue, worker lease, events, SSE, artifact store.
- Job console, pause/cancel, restart recovery.
- Hash-chained evidence ledger a final report export.

## 34.5 Fáze 4 - Planning and Model Router

- Provider interface, Ollama adapter, OpenAI-compatible optional adapter.
- Context bundles, goal and plan schemas, structured output validation.
- Plan UI a approval gates.

## 34.6 Fáze 5 - Isolated Implementation and Patch Review

- Workspace Manager s Git worktree.
- Tool Gateway read/write primitives a command policy.
- Implementer role, Patch Engine a Diff Review UI.

## 34.7 Fáze 6 - Verification and Repair Loop

- Project command matrix, test result parsers, verification report.
- Debugger/Repair workflow s max iteracemi.
- Regression evidence a anti-loop kontroly.

## 34.8 Fáze 7 - Guardian Hardening

- Autonomy levels, approvals, secrets, network policies.
- Security test suite, malicious repository fixture, path/shell hardening.
- Policy editor a effective policy explanation.

## 34.9 Fáze 8 - First Real Project Adapters

- Připojit vybraný pilotní projekt, doporučeně TradePilot nebo NeuroString v read-only/assisted režimu.
- Doplnit jeho manifest, commands, risk policy a acceptance suite.
- Prokázat celý flow na reálné malé změně.

## 34.10 Fáze 9 - Production Candidate

- Performance, disk retention, backup/restore, upgrade tests.
- Stabilní release packaging a one-command local start.
- Dokumentované runbooky a známá omezení.

---

# 35. Detailní milník 0 - přesný první implementační řez

## 35.1 Cíl

Vytvořit spustitelný, testovatelný základ FADE bez předstírání AI funkcí. Milník musí dokázat, že architektonické hranice, konfigurace, API, frontend a testy fungují dohromady.

## 35.2 Deliverables

- Monorepo struktura podle kapitoly 8.
- FastAPI /api/v1/system/health a /doctor endpointy.
- React shell s navigation a System Status stránkou.
- Domain typy ProjectId, JobId, RiskLevel, AutonomyLevel, ErrorCode.
- Settings načítané z config + env s bezpečným výpisem.
- Structured logger s correlation_id middleware.
- SQLite connection, Alembic init a první migration tabulky projects.
- Backend unit/integration test a frontend component test.
- scripts/dev.sh, scripts/test.sh a README quickstart.

## 35.3 Acceptance criteria

- Na čistém Ubuntu/WSL2 lze spustit uv sync a pnpm install bez ručních zásahů do zdrojů.
- Jedním příkazem se spustí API a web nebo jsou popsány dva přesné příkazy.
- GET /api/v1/system/health vrací version, status, db status a capability flags.
- Neplatná konfigurace skončí fail-fast s konkrétní chybou, ne stack trace bez vysvětlení.
- pytest a Vitest procházejí.
- Architecture dependency test zabrání importu infrastructure do domain.
- README neobsahuje funkce, které ještě nejsou implementované, bez označení planned.

## 35.4 Zakázané zkratky

- Nevytvářet fake AI response endpointy jako hotovou funkci.
- Nevkládat vše do main.py.
- Nepřidávat Redis, Celery, Kubernetes nebo mikroservisy.
- Nepřeskakovat test setup a migrace.
- Nevytvářet hard-coded cesty uživatele.

---

# 36. Integrace vybraných existujících projektů

FADE musí podporovat libovolný projekt přes obecný manifest. U významných projektů lze přidat adapter, který rozumí jejich příkazům, rizikům a artefaktům. Adapter nesmí obejít Tool Gateway ani Guardian.

| Projekt | Typ | Adapter focus | Specifické riziko | Verification profile |
| --- | --- | --- | --- | --- |
| TradePilot | Python/FastAPI + HTML/JS trading software | Live market API, paper trading, strategie, reporty | Finanční side effects; live executor zakázán bez critical policy | Scanner/test/report workflow |
| NeuroString | Python experimentální síť/ledger | Core algorithms, persistence, demos, network | Korektnost ledgeru, double-spend, determinismus | Unit + persistence + doublespend demos |
| Continuity OS / CodeOS | Python orchestration platform | Goals, policies, long-running tasks | Reentrancy, recovery, policy correctness | Recovery and policy test suite |
| FADE-Cortex | Agentní reasoning/runtime | Model router, memory, repair, audit | Self-modification and recursion | Benchmark harness + audit evidence |
| FADE IDE | Web/desktop IDE | Monaco, terminal, LSP, patch engine | Arbitrary command execution | Editor/terminal/LSP integration tests |
| VentureForge | FastAPI + React product builder | Discovery, planning, generation, build loop | Generated code integrity | Generated fixture project build |
| OpenClaw / Mythos | Runtime/governance/cognition | Kernel, continuity, swarm | Autonomy and capability control | Governance + continuity scenarios |
| Verse Empire / AgentOS | Multi-agent enterprise simulation | Companies, agents, governance | Scale and runaway jobs | Deterministic simulation fixtures |
| CRATE | Flutter music-card application | Local artist/track DB, rarity/drop rules, card UI | Dataset size and deterministic economy | Dart unit + widget tests |
| Neon Shadows | JavaScript game | Game loop, systems, UI | Runtime regression and asset paths | Browser smoke/E2E |

## 36.1 Doporučené pořadí pilotů

1. Malý fixture projekt - ověření platformy bez business rizika.
2. NeuroString nebo jiný čistě lokální Python projekt - ověření analýzy, patch a tests.
3. TradePilot pouze v paper/simulation režimu - ověření složitějšího projektu a financial policies.
4. Continuity OS - ověření recovery scénářů a porovnání architektur.
5. Flutter/JS projekty - rozšíření parserů a command profilů.

## 36.2 Cross-project funkce

Cross-project znalost je v první verzi read-only a explicitní. Uživatel může označit zdrojový projekt jako referenci pro jiný projekt, například převzít ověřený checkpoint pattern z Continuity OS do FADE. Context Engine vloží pouze vybrané dokumenty nebo symboly a evidence označí jejich původ. Automatická změna několika projektů v jednom jobu je až budoucí fáze.

---

# 37. Selhání a očekávané chování

| Situace | Požadované chování |
| --- | --- |
| Model nedostupný | Job čeká/retry podle policy; deterministické funkce zůstávají dostupné. |
| Model vrátí nevalidní JSON | Structured output repair; po limitu BLOCKED, žádný stavový přechod z textu. |
| Disk téměř plný | Scheduler zastaví nové workspaces, System Doctor ukáže cleanup options. |
| Projektová cesta zmizí | Project DEGRADED, existující evidence zůstane. |
| Git branch se změnila | Stale base, rebase gate a re-verification. |
| Test timeout | Kill process tree, uložit partial logs, klasifikovat. |
| Worker crash | Lease expiry, recovery a checkpoint validation. |
| API restart | Frontend reconnect SSE, durable job pokračuje. |
| SQLite locked | Short transactions, retry with bounded backoff; po limitu explicitní failure. |
| Malicious output | Redaction + content size limits; UI bezpečně escapuje. |
| Patch nelze aplikovat | Base hash mismatch, nový context refresh; nezkoušet fuzzy write bez review. |
| Flaky test | Opakovat podle policy, označit flaky; není automaticky PASS. |
| Approval nepřijde | Job PAUSED/BLOCKED, lease uvolněn podle bezpečného checkpointu. |

---

# 38. Etika, odpovědnost a bezpečný autonomní provoz

FADE je nástroj pro zesílení schopností vlastníka, nikoli náhrada odpovědnosti. V oblastech s finančním, bezpečnostním, právním nebo produkčním dopadem musí systém jasně oddělit simulaci od skutečné akce. UI i evidence musí uvádět, zda výsledek vznikl v testu, sandboxu, paper režimu nebo produkci.

- Modelový návrh je doporučení; deterministické gates rozhodují o povolení akce.
- Autonomie se uděluje konkrétním projektům a akcím, ne globálním pocitem důvěry.
- Systém nesmí skrývat nejistotu ani zaměnit neprovedený test za důkaz.
- Uživatel musí mít kill switch, pause a možnost exportovat data mimo platformu.
- FADE musí podporovat úplné vypnutí cloudových providerů a síťových tools.

---

# 39. Budoucí rozšíření

## 39.1 FADE IDE

Až je control plane stabilní, FADE IDE může využít stejné API pro project explorer, goal creation, diff review, terminal a agentní timeline. IDE nesmí duplikovat doménovou logiku; je dalším klientem platformy.

## 39.2 Distribuovaní workers

Pozdější verze může přidat worker registry, capability advertisement, signed leases a central coordination. Fencing a evidence navržené v MVP připravují základ. Pro skutečný cluster bude SQLite nahrazena nebo doplněna konsenzuálním storem pro leases, ale project metadata mohou zůstat v transakční DB.

## 39.3 Product Factory

VentureForge/Product Factory lze připojit jako workflow šablonu: discovery -> PRD -> architecture -> scaffold -> implementation -> verification -> package. Výstup musí stále procházet stejnými Guardian, Workspace a Evidence službami.

## 39.4 Učení z výsledků

FADE se dlouhodobě zlepšuje ukládáním ověřených MemoryItem, nikoli nekontrolovaným přepisem modelu. Učení zahrnuje úspěšné příkazy, známé failure signatures, efektivní context selection, project conventions a review findings. Každá znalost má provenance, confidence a invalidation podmínku.

---

# 40. Měřítka úspěchu

| KPI | Definice | Cílový signál po pilotu |
| --- | --- | --- |
| Project onboarding success | Podíl projektů, které dosáhnou READY bez ruční DB opravy. | > 90 % u podporovaných stacků. |
| Verified task completion | Úkoly dokončené s PASS evidence / zahájené úkoly. | Roste po každém milníku; sledovat podle risku. |
| Repair effectiveness | Failure opravené do povoleného počtu iterací. | Měřit, neoptimalizovat přes vypínání testů. |
| False completion rate | Úkol označený hotový, který následně selže reprodukci. | 0 u kritických workflow. |
| Recovery success | Aktivní joby správně obnovené po kontrolovaném crash testu. | 100 % podporovaných checkpoint bodů. |
| Policy bypass incidents | Akce provedené přes policy denial. | 0. |
| Context efficiency | Relevantní context / celkový context a token budget. | Postupně zlepšovat; zachovat přesnost. |
| User intervention quality | Kolik approval žádostí je konkrétních a rozhodnutelných. | Žádné vágní „continue?“ bez dopadu. |

---

# 41. Architektonická rozhodnutí, která Cursor nesmí svévolně změnit

- Platform repo a spravované project repos zůstávají oddělené.
- Backend je Python/FastAPI; frontend React/TypeScript; SQLite je MVP persistence.
- MVP je modulární monolit s lokálním workerem, ne síť mikroservis.
- Tool Gateway je povinná pro všechny agentní side effects.
- Kód je měněn v izolovaném workspace, ne přímo v originálním projektu.
- Joby a approvals jsou perzistentní a obnovitelné.
- Model nerozhoduje o oprávněních ani dokončení bez deterministických gates.
- Cloud není povinný a nesmí být implicitní fallback.
- Autonomie je víceúrovňová a výchozí režim je Analyze/Plan.
- Evidence je součást funkce, nikoli dodatečný log.

## 41.1 Kdy vytvořit nové ADR

- Změna databáze nebo queue technologie.
- Přidání nové runtime služby nebo procesu.
- Změna bezpečnostní hranice, secrets nebo network policy.
- Změna reprezentace workspace/patch/Git workflow.
- Změna veřejného API nebo doménového stavového automatu.
- Zavedení cross-project mutací nebo produkčních side effects.

---

# 42. Instrukce pro Cursor - pracovní protokol

1. Před změnou přečti WHITE_PAPER.md, ARCHITECTURE_DECISIONS.md a aktuální milestone v IMPLEMENTATION_BACKLOG.md.
2. Zkontroluj aktuální repository tree a existující kód. Nevytvářej paralelní druhou implementaci stejné služby.
3. Napiš stručný impact plan: soubory, kontrakty, migrace, testy a rizika.
4. Implementuj nejmenší kompletní vertikální řez; ne širokou sadu prázdných skeletonů bez funkčního flow.
5. Po každé významné změně spusť relevantní testy. Nečekej až na konec celé fáze.
6. Neopravuj neúspěšné testy jejich vypnutím nebo snížením požadavků.
7. Při rozporu s architekturou zastav změnu a vytvoř ADR proposal.
8. Na konci vypiš: změněné soubory, důvody, testy a výsledky, známá omezení, doporučený další krok.

## 42.1 Povinný formát každého Cursor kroku

```
1. Current state observed
2. Goal and acceptance criteria
3. Impacted modules/files
4. Implementation plan
5. Patch/diff
6. Commands executed
7. Test and verification results
8. Risks or unresolved items
9. Backlog/documentation update
10. Stop at the milestone boundary
```

---

# 43. První prompt, který vložit do Cursoru

> Samostatný přesný prompt je dodán v souboru 02_CURSOR_MASTER_PROMPT.md. Cursor musí nejdřív vytvořit pouze Milestone 0 a nesmí předstírat implementaci pozdějších AI funkcí.

# 44. Závěr

FADE má být jedna velká platforma pro všechny projekty, které si uživatel vybere, ale její síla vznikne z disciplinovaného oddělení odpovědností. Zdrojové projekty zůstávají samostatné. FADE poskytuje společný control plane, znalosti, agentní workflow, bezpečný execution, ověření, audit a kontinuitu. Tato architektura umožňuje začít na jednom notebooku s 8 GB RAM a postupně růst bez nutnosti projekt později celý přepisovat.

První úspěch není „AI napsala hodně kódu“. První úspěch je, že FADE dokáže bezpečně přidat projekt, pravdivě popsat jeho stav, vytvořit testovatelný plán, připravit izolovanou změnu, prokázat její správnost a zanechat auditní stopu. Teprve na tomto základě se zvyšuje autonomie a připojují další projekty.

---

# Příloha A - Funkční požadavky

| ID | Požadavek |
| --- | --- |
| FR-001 | Systém umožní registrovat lokální Git projekt bez změny jeho obsahu. |
| FR-002 | Systém ověří cestu, typ zdroje, Git stav a základní manifests. |
| FR-003 | Systém vytvoří verzovaný profil projektu s provenance. |
| FR-004 | Uživatel může archivovat a znovu aktivovat projekt. |
| FR-005 | Systém umožní definovat goal s constraints a acceptance criteria. |
| FR-006 | Planner vytvoří verzovaný plan a dependency order. |
| FR-007 | Plan nelze spustit bez požadovaného approval. |
| FR-008 | Mutující job používá izolovaný workspace. |
| FR-009 | Agent může používat pouze tools přidělené roli a policy. |
| FR-010 | Každý tool call je auditován a má policy decision. |
| FR-011 | Patch se aplikuje pouze při shodě base hashes. |
| FR-012 | Systém zobrazí diff a jeho vazbu na acceptance criteria. |
| FR-013 | Verification Engine spustí definovanou matici kontrol. |
| FR-014 | Job bez PASS nemůže být standardně COMPLETED. |
| FR-015 | Repair Loop má omezený počet iterací a anti-loop kontrolu. |
| FR-016 | Job lze pause, resume a cancel. |
| FR-017 | Aktivní job lze obnovit po restartu workeru. |
| FR-018 | Uživatel může exportovat evidence package. |
| FR-019 | Systém podporuje lokální model provider. |
| FR-020 | Cloud provider je per-project opt-in. |
| FR-021 | Secrets jsou redacted před persistencí a modelovým přenosem. |
| FR-022 | Guardian vysvětlí důvod allow/deny/approval. |
| FR-023 | Dashboard ukáže health a jeho komponenty s evidence. |
| FR-024 | Project manifest lze verzovaně upravit a validovat. |
| FR-025 | Systém podporuje minimálně Python a TypeScript analysis. |
| FR-026 | Systém rozpozná test/build/lint commands z manifestů. |
| FR-027 | System Doctor ověří runtime dependencies a DB. |
| FR-028 | Uživatel může nastavit autonomy level globálně i per project. |
| FR-029 | Original project není nikdy odstraněn cleanup rutinou. |
| FR-030 | Cross-project context je explicitní a auditovaný. |

---

# Příloha B - Nefunkční požadavky

| ID | Požadavek |
| --- | --- |
| NFR-001 Security | Deny-by-default pro síť a externí side effects. |
| NFR-002 Reliability | Durable job state a crash recovery. |
| NFR-003 Performance | Provozní control plane vhodný pro 8 GB RAM. |
| NFR-004 Portability | Linux-first bez povinného Docker/Kubernetes. |
| NFR-005 Auditability | Hashované artefakty a append-only events. |
| NFR-006 Maintainability | Modulární monolit s dependency boundaries. |
| NFR-007 Testability | Infrastructure za ports a fake adapters. |
| NFR-008 Usability | Každý blocker má vysvětlení a konkrétní další akci. |
| NFR-009 Privacy | Žádný implicitní cloudový přenos projektových dat. |
| NFR-010 Compatibility | Projekt zůstává použitelný bez FADE. |
| NFR-011 Recoverability | Záloha a restore SQLite/config/evidence. |
| NFR-012 Extensibility | Provider a project adapter rozhraní. |
| NFR-013 Consistency | Stavový přechod a event jsou atomické/outbox-safe. |
| NFR-014 Accessibility | UI ovladatelné klávesnicí, textové statusy, ne pouze barvy. |
| NFR-015 Observability | Correlation IDs a structured logs. |

# Příloha C - Acceptance scénáře

| ID | Scénář |
| --- | --- |
| AC-001 Happy onboarding | Given valid clean local Git repo, when user registers it, then project reaches READY and profile contains detected stack, revision and commands. |
| AC-002 Missing path | Given missing path, registration fails with PROJECT_PATH_NOT_FOUND and no project side effects. |
| AC-003 Secret protection | Given .env and token in test stdout, then contents are not sent to provider and persisted logs contain redaction. |
| AC-004 Safe patch | Given approved low-risk plan, implementer creates worktree patch, original repo remains unchanged until apply approval. |
| AC-005 Verification failure | Given failing test, job enters REPAIRING or BLOCKED, never standard COMPLETED. |
| AC-006 Crash recovery | Given worker killed after patch checkpoint, new worker resumes verification without applying patch twice. |
| AC-007 Policy denial | Given request git push in autonomy 2, Tool Gateway returns require_approval/deny and records rule id. |
| AC-008 Cross-project isolation | Given project A job, attempt to read project B path is denied and audited. |
| AC-009 Stale base | Given base branch advanced, apply is blocked until rebase and re-verification. |
| AC-010 Evidence export | Given finished job, exported package independently contains plan, diff, commands, verification and hashes. |

---

# Příloha D - Glossary

| Termín | Definice |
| --- | --- |
| Agent | Role-based model execution controlled by runtime and policies. |
| Artifact | File output with content hash and metadata. |
| Control plane | Central API and workflow/state management. |
| Evidence | Proof tied to an action or claim. |
| Fencing token | Monotonic token preventing stale worker writes. |
| Goal | Desired outcome with constraints and acceptance criteria. |
| Job | Durable execution of a task. |
| Manifest | Project-specific commands, policies and context rules. |
| Memory item | Persisted claim with provenance and confidence. |
| Plan | Versioned decomposition of a goal. |
| Project adapter | Optional logic for a known project type. |
| Tool Gateway | Policy enforcement point for side effects. |
| Verification gate | Deterministic condition required for state transition. |
| Workspace | Isolated project copy/worktree used by a job. |
