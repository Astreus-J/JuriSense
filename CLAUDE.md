# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository State

JuriSense (also referred to as "SchemaJud" in the README) is a Brazilian legal-tech SaaS platform in early implementation. All documentation and user-facing copy is written in **Portuguese (pt-BR)**; keep new content in Portuguese to match. Git branch in use: `develop`.

## Repository Structure

- `frontend/` — Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 app containing the landing page. Landing content data lives in `src/lib/landing-data.ts` (features, the 4 pricing plans, FAQ, contact) and section components in `src/components/landing/`. `next.config.ts` uses `output: "standalone"`; the multi-stage `Dockerfile` builds on node:24-alpine and runs on a distroless Node 24 image as non-root (`docker build -t jurisense-frontend .`). Commands: `npm run dev` / `npm run build` / `npm run lint`.
- `backend/` — empty; planned Python/FastAPI API.
- `JuriSense_frontend/` — legacy Vite + React prototype, superseded by `frontend/`; kept as a reference for components and image assets (`public/img/`).
- `README.md` — Full product specification: functional requirements (125 RFs across 15 modules), non-functional requirements, business rules, use cases, actors, data model, pricing plans, market analysis, and business model.
- `docs/IMPLEMENTACAO_ARQUITETURA/` — Architecture documents, indexed by `00_INDICE.md`:
  - `01_GCP_INFRAESTRUTURA.md` — Cloud-native GCP infrastructure (Cloud Run, Cloud SQL, Pub/Sub, Storage)
  - `02_IA_ESTRATEGIA.md` — AI strategy (LLM models, RAG, prompts, jurimetria, LGPD compliance)
  - `03_BACKEND_DDD.md` — Domain-Driven Design backend architecture
  - `04_BRIEFING_IA_PARA_ESPECIALISTA.md` — Briefing for external AI specialist (API vs self-host decision, AI Gateway requirements)
  - `05_PLANO_HOSPEDAGEM_GCP.md` — GCP hosting plan
- `docs/diagramas/` — PlantUML diagrams: ER model, UML classes, domain/module relationships, component architecture, sequence diagrams for the main flows, and microservices diagrams.

## Planned Architecture (big picture)

- **Stack:** Python/FastAPI backend (async, stateless, JWT auth), Next.js + React + TypeScript web frontend, React Native mobile. PostgreSQL as primary DB, Redis for cache/queues, Celery for async work.
- **Hosting:** a single VPS (Docker Compose) runs frontend, backend, Celery workers, Redis, and Nginx. Only two things are external: the managed PostgreSQL database and the AI APIs (OpenAI/Anthropic). Document storage lives on the VPS filesystem in per-company directories (e.g. `/dados/empresas/{organizacao_id}/`), with encrypted backups shipped off-VPS. Cloudflare fronts the VPS as CDN/WAF.
- **Backend design:** DDD with hexagonal/clean architecture. Five Bounded Contexts: **Accounts, Processes, Documents, Deadlines, IA_Services**. Domain logic is isolated from the ORM via repositories/data mappers; use cases orchestrate domain aggregates and publish domain events.
- **Async/event-driven:** Heavy operations (AI generation, OCR, court synchronization) run asynchronously via Celery, with GCP Pub/Sub / Cloud Tasks connecting decoupled components.
- **AI:** LLM APIs (GPT-4 / Claude) with RAG for document generation, predictive analysis (jurimetria), and chatbot. An AI Gateway with provider fallback is a key requirement; API-first with a defined cost threshold for migrating to self-hosted models.
- **Domain specifics:** Brazilian legal domain — CNJ process numbers, court (tribunal) integrations, procedural deadline calculation with holidays, ICP-Brasil digital signatures, OAB registration, LGPD compliance throughout.

## Known Documentation Inconsistencies

The docs were written at different times and contradict each other in places. When editing, prefer the newer architecture docs (`docs/IMPLEMENTACAO_ARQUITETURA/`) over the README:

- **Hosting:** the current decision (July 2026) is a **single VPS** with only the database and AI external — the README reflects this, but the architecture docs in `docs/IMPLEMENTACAO_ARQUITETURA/` still describe a full GCP deployment (Cloud Run, Cloud SQL, Pub/Sub) and have not been updated.
- **Backend framework:** the current decision (July 2026) is **FastAPI + Next.js** — the README reflects this, but the architecture docs in `docs/IMPLEMENTACAO_ARQUITETURA/` still reference Django throughout and have not been updated.
- The README index title ("SCHEMAJUD") differs from the product name used everywhere else (**JuriSense**).
