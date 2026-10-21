# JuriSense Documentation

This is the navigation index for the active JuriSense documentation. All of it describes
**JuriSense Gate**, the AI-powered Vendor, Contract & Compliance Operations Platform (see
`00-project/overview.md` for the full picture). Everything here is written in English (see
`07-engineering/coding-standards.md` for the project-wide language rule).

**Start here**: `00-project/overview.md` — the single entry point for understanding what JuriSense
is, why it exists, how it works, and where it's going.

For the previous product concept (a generic legal-ERP for Brazilian law firms, discontinued
2026-09-27), see `_legacy/README.md`.

## Structure

| Folder | Contents |
|---|---|
| [`00-project/`](00-project/) | Vision, problem, solution, principles, glossary |
| [`01-product/`](01-product/) | Product definition, personas, use cases, journeys, modules, requirements (functional & non-functional), future vision |
| [`02-business/`](02-business/) | Business model, business case, Brazil/international market, pricing, go-to-market, competitive landscape, differentiation, expansion, legal posture |
| [`03-domain/`](03-domain/) | Domain model (24 entities), business rules, policy engine, supplier/contract compliance, approvals, audit event catalog, evidence |
| [`04-architecture/`](04-architecture/) | Architecture overview, C4 diagrams (context/containers/components), data architecture, integrations, AI/blockchain/security architecture, deployment |
| [`05-ai/`](05-ai/) | AI strategy, agent architecture, document intelligence, RAG, structured extraction schema, evaluation, guardrails, observability |
| [`06-blockchain/`](06-blockchain/) | Why blockchain, evidence model, anchoring provider comparison, smart contract sketch, privacy boundary, public verification |
| [`07-engineering/`](07-engineering/) | Technology stack, coding standards, repository structure, API/database standards, testing, observability, security, CI/CD, dev workflow, deployment runbook |
| [`08-hackathon/`](08-hackathon/) | Hackathon strategy, requirements, submission plan, demo script, pitch, fallback MVP |
| [`09-planning/`](09-planning/) | Roadmap (12 phases), backlog (EPIC→FEATURE→STORY→TASK), dependency graph, implementation plan, milestones, risks, pivot migration inventory |
| [`adr/`](adr/) | 16 Architecture Decision Records (ADR-001 through ADR-016) |
| [`auditorias/`](auditorias/) | Existing security audit reports for the reused Identity & Organizations (Accounts) code — kept in place, still relevant |
| [`_legacy/`](_legacy/) | Archived pre-pivot documentation (the old legal-ERP product concept) — historical reference only |

## Reading order for someone new to the project

1. `00-project/overview.md`, then `00-project/vision.md` and `problem.md`/`solution.md`.
2. `03-domain/domain-model.md` and `policy-engine.md` — the core of how the product actually behaves.
3. `01-product/use-cases.md` — the most detailed behavioral spec.
4. `docs/adr/` — why the architecture looks the way it does.
5. `04-architecture/architecture-overview.md` — how it's built.
6. `09-planning/roadmap.md` and `08-hackathon/hackathon-strategy.md` — where it's going and the
   immediate hackathon milestone.
