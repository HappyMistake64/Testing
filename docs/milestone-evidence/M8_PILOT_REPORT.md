# Milestone 8 — Pilot Report

**Date:** 2026-07-14  
**Branch:** cursor/fade-platform-m2-m9-3637  
**Status:** PASS

## Pilot 1 — Small Fixture (pilot_small)

| Step | Result |
|------|--------|
| Register project | PASS — status `ready` |
| Analyze | PASS — Python detected, symbols indexed |
| Health components | PASS — inventory, python_tests |
| Explorer | PASS — file tree with symbols |
| Create goal | PASS |
| Plan proposal | PASS — 3 steps generated |
| Approve + job | PASS — state `awaiting_review` |
| Job events | PASS — evidence chain populated |
| Diff review | PASS — patch metadata returned |
| Source unchanged | PASS — original repo not modified |

**Fixture:** `tests/fixtures/pilot_small/`  
**E2E test:** `tests/e2e/test_pilot_flow.py`

## Pilot Manifest Templates

| Template | Profile | Notes |
|----------|---------|-------|
| `pilot_manifest_small.yaml` | python | Minimal verification |
| `pilot_manifest_python.yaml` | python | test + lint gates |
| `pilot_manifest_tradepilot.yaml` | python_web_financial | Paper-only, production trading denied |

## Pilots 2–3 (Deferred)

NeuroString and TradePilot require owner-provided local paths (see `docs/project-registry.template.yaml`). Templates and verification profiles are ready; full real-project pilots pending path configuration.

## Architecture Adjustments

None required beyond M2–M7 implementation. No ADR changes.

## Exit Gate

- [x] Pilot 1 small fixture end-to-end
- [x] Project-specific manifest templates
- [x] Pilot outcome report
- [~] Pilot 2 NeuroString — template ready, path TBD
- [~] Pilot 3 TradePilot — paper-only template ready, path TBD
