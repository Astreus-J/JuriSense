# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository State

This is a **documentation-only repository** — there is no source code, build system, or test suite yet. The project (JuriSense, also referred to as "SchemaJud" in the README) is a Brazilian legal-tech SaaS platform in the planning/architecture phase. All documentation is written in **Portuguese (pt-BR)**; keep new documentation in Portuguese to match.

This directory is not a git repository.

## Documentation Structure

- `README.md` — Full product specification: functional requirements (125 RFs across 15 modules), non-functional requirements, business rules, use cases, actors, data model, market analysis, and business model.
- `docs/IMPLEMENTACAO_ARQUITETURA/` — Architecture documents, indexed by `00_INDICE.md`:
  - `01_GCP_INFRAESTRUTURA.md` — Cloud-native GCP infrastructure (Cloud Run, Cloud SQL, Pub/Sub, Storage)
  - `02_IA_ESTRATEGIA.md` — AI strategy (LLM models, RAG, prompts, jurimetria, LGPD compliance)
  - `03_BACKEND_DDD.md` — Domain-Driven Design backend architecture
  - `04_BRIEFING_IA_PARA_ESPECIALISTA.md` — Briefing for external AI specialist (API vs self-host decision, AI Gateway requirements)
  - `05_PLANO_HOSPEDAGEM_GCP.md` — GCP hosting plan
- `docs/diagramas/` — PlantUML diagrams: ER model, UML classes, domain/module relationships, component architecture, sequence diagrams for the main flows, and microservices diagrams.

## Planned Architecture (big picture)

- **Stack:** Python/FastAPI backend (async, stateless, JWT auth), Next.js + React + TypeScript web frontend, React Native mobile. PostgreSQL as primary DB, Redis for cache/queues, Celery for async work.
- **Backend design:** DDD with hexagonal/clean architecture. Five Bounded Contexts: **Accounts, Processes, Documents, Deadlines, IA_Services**. Domain logic is isolated from the ORM via repositories/data mappers; use cases orchestrate domain aggregates and publish domain events.
- **Async/event-driven:** Heavy operations (AI generation, OCR, court synchronization) run asynchronously via Celery, with GCP Pub/Sub / Cloud Tasks connecting decoupled components.
- **AI:** LLM APIs (GPT-4 / Claude) with RAG for document generation, predictive analysis (jurimetria), and chatbot. An AI Gateway with provider fallback is a key requirement; API-first with a defined cost threshold for migrating to self-hosted models.
- **Domain specifics:** Brazilian legal domain — CNJ process numbers, court (tribunal) integrations, procedural deadline calculation with holidays, ICP-Brasil digital signatures, OAB registration, LGPD compliance throughout.

## Known Documentation Inconsistencies

The docs were written at different times and contradict each other in places. When editing, prefer the newer architecture docs (`docs/IMPLEMENTACAO_ARQUITETURA/`) over the README:

- **Cloud provider:** README's infrastructure section says AWS (EKS, RDS, S3); the architecture docs standardize on **GCP** (Cloud Run, Cloud SQL, Cloud Storage). `04_BRIEFING` describes an even leaner initial setup (Hostinger frontend, Supabase Postgres/auth).
- **Backend framework:** the current decision (July 2026) is **FastAPI + Next.js** — the README reflects this, but the architecture docs in `docs/IMPLEMENTACAO_ARQUITETURA/` still reference Django throughout and have not been updated.
- The README index title ("SCHEMAJUD") differs from the product name used everywhere else (**JuriSense**).
