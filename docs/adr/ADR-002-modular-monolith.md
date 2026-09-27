# ADR-002 — Modular Monolith with Internal Bounded Contexts

## Status
Accepted

## Context
The product has 8 clearly separable domains of responsibility (see `docs/03-domain/domain-model.md`),
and the mission brief explicitly warns against both premature microservices and academic DDD
over-engineering. The team is small, the hackathon timeline is tight (first cut due by early
November 2026), and the existing `Accounts` code is already a single FastAPI app.

## Decision
Build JuriSense Gate as a **modular monolith**: one deployable FastAPI application, internally
organized into 8 bounded contexts as separate Python packages under `app/`, each following the
existing `domain/application/infrastructure/api` layering. Contexts communicate only through
in-process application-layer interfaces (ports), never by reaching into another context's ORM
models directly (see `docs/04-architecture/components.md` for the explicit boundary rules).

## Alternatives Considered
- **Microservices per bounded context**: better long-term scaling/deployment isolation, but adds
  network calls, distributed transactions, service discovery, and operational overhead the team
  cannot absorb before the hackathon deadline, for a product that has zero production traffic yet.
- **Single undifferentiated codebase (no internal module boundaries)**: fastest to start, but
  reproduces the coupling risk the pivot is trying to avoid (the old product's code was not audited
  for this, but the new domain has enough moving parts — supplier data, contract AI, policy
  evaluation, approvals, evidence — that undisciplined coupling would make the Policy/Compliance
  engine hard to test and reason about independently).

## Consequences
- A single deployment unit and single database keep operational complexity low for the VPS/Docker
  Compose hosting model already in place.
- Enforcing "no cross-context ORM access" requires discipline and code review; it is not enforced
  by a network boundary. `07-engineering/coding-standards.md` documents lint/review rules to catch
  violations.
- If a specific context (most likely `AI Services`, due to compute cost/scaling profile) later needs
  independent scaling, it can be extracted into its own service without a full rewrite, because the
  application-layer interface already exists as the seam.
