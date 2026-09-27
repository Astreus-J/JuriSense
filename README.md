# JuriSense

**AI-powered Vendor, Contract & Compliance Operations Platform.**

JuriSense turns contracts, supplier data, and company policies into auditable compliance
decisions. The first product built on it is **JuriSense Gate**: a B2B platform that automates the
analysis and approval of suppliers and contracts using AI, an executable company policy engine,
official data sources, approval workflows, an audit trail, and a blockchain-based verifiability
layer.

> Full product, architecture, and business documentation lives in [`docs/`](docs/README.md) —
> start with [`docs/00-project/overview.md`](docs/00-project/overview.md).

## The problem

Companies buy from many outside vendors — SaaS, consultancies, outsourcing, cloud providers,
developers, partners — and are supposed to check registration data, sanctions lists, compliance
posture, LGPD exposure, security, SLAs, liability terms, and internal approvals before signing.
Today this happens manually across Procurement, Legal, Compliance, Finance, Security, and Privacy
teams, over email and spreadsheets, with no reproducible record of *why* a vendor was approved.
See [`docs/00-project/problem.md`](docs/00-project/problem.md) for the full analysis.

## The solution

```
Supplier → Company verification → Documents/Contract ingestion → AI structured extraction
  → Policy Engine → Compliance Engine → Risk analysis → APPROVE / REVIEW / BLOCK
  → Human approval → Decision Passport → Audit Trail → Blockchain verification
```

Every decision comes with **WHY, EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER, AUDIT
TRAIL, VERIFICATION** — never a bare status. See
[`docs/00-project/solution.md`](docs/00-project/solution.md) and
[`docs/03-domain/policy-engine.md`](docs/03-domain/policy-engine.md).

## Architecture summary

Python 3.13 + FastAPI **modular monolith**, organized into 8 internal bounded contexts (Identity &
Organizations, Suppliers, Contracts & Documents, Policy & Compliance, Approvals & Decisions,
Evidence & Audit, AI Services, Integrations), Next.js 16 + React 19 + TypeScript frontend,
PostgreSQL (external, Neon) + pgvector, Redis + Celery, S3-compatible object storage, a
provider-agnostic blockchain anchoring layer. Full detail and the reasoning behind every choice:
[`docs/04-architecture/`](docs/04-architecture/) and [`docs/adr/`](docs/adr/) (16 ADRs).

## Main modules

| Module | What it does |
|---|---|
| Supplier Intelligence | Registers and verifies suppliers against official/public sources (company registry, sanctions lists) |
| Contract Intelligence | Ingests contracts and extracts structured, cited data via AI |
| Policy Engine | Turns company policy into versioned, executable rules |
| Compliance Engine | Aggregates rule evaluations into APPROVE/REVIEW/BLOCK, deterministically |
| Approvals | Routes REVIEW outcomes to the right human approver(s) |
| Evidence & Audit | Builds the Decision Passport and anchors its hash on-chain for independent verification |

Full spec: [`docs/01-product/modules.md`](docs/01-product/modules.md).

## Repository structure

```
backend/    FastAPI application (Python 3.13, uv-managed)
frontend/   Next.js 16 + React 19 + TypeScript + Tailwind v4
docs/       Product, architecture, business, and planning documentation (see docs/README.md)
```

## Setup

**Backend**
```
cd backend
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
```

**Frontend**
```
cd frontend
npm run dev
npm run build
npm run lint
```

**Everything together** (frontend, backend, Redis, and dev volumes):
```
docker compose up -d
```

The database is an external managed PostgreSQL (Neon) — no local Postgres container. See
`backend/.env` (gitignored) for `DATABASE_URL` and `docs/04-architecture/deployment.md` for the
full hosting model.

## Development

- All new code, documentation, comments, identifiers, tests, commits, and PRs are written in
  **English** — see [`docs/07-engineering/coding-standards.md`](docs/07-engineering/coding-standards.md).
- Every sprint ends with a security audit before the next one starts — see
  [`docs/adr/ADR-016-security-audit-as-sprint-gate.md`](docs/adr/ADR-016-security-audit-as-sprint-gate.md)
  and existing reports in [`docs/auditorias/`](docs/auditorias/).
- See [`docs/07-engineering/development-workflow.md`](docs/07-engineering/development-workflow.md)
  for local DX, seed data, and the sprint workflow.

## Documentation

Full documentation index: [`docs/README.md`](docs/README.md). Highlights:

- [`docs/00-project/overview.md`](docs/00-project/overview.md) — start here.
- [`docs/03-domain/domain-model.md`](docs/03-domain/domain-model.md) and
  [`policy-engine.md`](docs/03-domain/policy-engine.md) — the core domain behavior.
- [`docs/09-planning/roadmap.md`](docs/09-planning/roadmap.md) and
  [`backlog.md`](docs/09-planning/backlog.md) — where the product is going, phase by phase.
- [`docs/08-hackathon/`](docs/08-hackathon/) — the BLI Legal Tech Hackathon 2 / Legal Hack 2026
  submission strategy.

## Project status

JuriSense pivoted on 2026-09-27 from an earlier legal-ERP concept (for Brazilian law firms) to the
vendor/contract compliance platform described above. The identity/organization/user management
layer (JWT auth, RBAC, multi-tenancy) is already implemented and security-audited, being adapted to
the new domain per [`docs/09-planning/pivot-migration.md`](docs/09-planning/pivot-migration.md).
Product, architecture, and business documentation is complete; implementation of the new bounded
contexts is the current phase — see [`docs/09-planning/implementation-plan.md`](docs/09-planning/implementation-plan.md).
The previous product concept is archived, not deleted, at [`docs/_legacy/`](docs/_legacy/).
