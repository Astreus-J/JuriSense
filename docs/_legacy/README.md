# Legacy documentation — pre-pivot JuriSense (legal-ERP concept)

**Status: archived, historical reference only. Not part of the active product documentation.**

## Why this exists

On 2026-09-27, JuriSense pivoted away from its original concept — a generic legal-tech ERP for
Brazilian law firms (process management, deadlines, jurimetria, billing, legal CRM) — to a new
product:

**JuriSense — AI-powered Vendor, Contract & Compliance Operations Platform**, starting with
**JuriSense Gate**, a B2B platform that automates supplier and contract compliance review using
AI, an executable policy engine, approval workflows, audit trails, and a blockchain evidence
verification layer.

The new active documentation lives in `docs/00-project/` through `docs/09-planning/`, `docs/adr/`,
and the repository root `README.md`. See `docs/09-planning/pivot-migration.md` for the full
inventory of what was reused, adapted, or discarded from the legacy product.

## What's in this folder

| File / folder | What it was |
|---|---|
| `README-schemajud-legacy.md` | The original root `README.md` — full spec of the legal-ERP product (internally called "SCHEMAJUD"): 125 functional requirements across 15 modules, business rules, use cases, market analysis, pricing. |
| `CLAUDE-legacy.md` | The original root `CLAUDE.md` describing the legal-ERP repository. |
| `PLANO_EVOLUCAO_JURISENSE.md` | Strategic product roadmap for the legal-ERP vision (MVP Previdenciário → V1–V4 practice-area verticals). |
| `IMPLEMENTACAO_ARQUITETURA/` | Architecture docs for the legal-ERP product: GCP infrastructure (already stale before the pivot — actual hosting decision was a single VPS), AI strategy, backend DDD (5 bounded contexts: Accounts/Processes/Documents/Deadlines/IA_Services), AI specialist briefing, GCP hosting plan. |
| `diagramas/` | PlantUML/Mermaid diagrams (ER model, UML classes, domain relationships, sequence diagrams, use-case diagram, microservices diagram) — all modeling the legal-ERP domain (Processo, Prazo, Jurimetria, Timesheet, etc). |
| `tradeoffs.md` | 6 informal architecture decisions made during the Accounts bounded context build (JWT strategy, RBAC-as-data, multi-tenancy, payment gateway deferral, security-audit-as-gate, and schema alignment to a Django prototype). These decisions still apply to the reused Accounts code and have been formalized as ADR-011 through ADR-016 in `docs/adr/`. |
| `implementation-plan.md` | Sprint plan for the Accounts bounded context (already executed — see git log). Kept as historical record of how Accounts was built. |

## What was NOT archived

`docs/auditorias/sprint-01.md` and `sprint-02.md` (security audits of the Accounts context) remain
in place under `docs/auditorias/` — they audit code that continues to be reused in the new product,
so they are still technically relevant, not legacy.

## Note on the dangling `JuriSense_frontend` / `JuriSense_backend` references

Some legacy documents (and prior project memory) refer to a `JuriSense_frontend/` Vite+React
prototype and a `JuriSense_backend` Django prototype as if they existed in or alongside this
repository. A full repository audit (2026-09-27) confirmed **neither exists** anywhere in this
repo or its git history. Treat any remaining mention of them, in this archive or elsewhere, as a
dangling reference to something that was never committed here — not as a real, recoverable asset.
