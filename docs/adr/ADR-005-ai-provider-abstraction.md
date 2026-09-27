# ADR-005 — AI Provider Abstraction

## Status
Accepted (direction) — implementation details pending spike

## Context
The old architecture docs (`docs/_legacy/IMPLEMENTACAO_ARQUITETURA/04_BRIEFING_IA_PARA_ESPECIALISTA.md`)
already required an "AI Gateway with provider fallback" and an API-first approach with a defined
cost threshold before considering self-hosted models — that reasoning is domain-agnostic and still
applies. JuriSense Gate's core AI job is different from the old product's (petição drafting →
structured contract/supplier data extraction with provenance), but the provider-abstraction
principle carries over unchanged.

## Decision
Build a thin **AI Gateway abstraction** inside the `AI Services` bounded context: a single internal
interface (`extract()`, `classify()`, `summarize()`) with pluggable provider adapters for
**OpenAI** and **Anthropic Claude**, selected per task type via configuration, with automatic
fallback to a secondary provider on error/timeout. All extraction calls require **structured output**
(JSON schema / tool-calling), never freeform text parsing, and every output must carry provenance
metadata (source document id, page, span, confidence) per `docs/05-ai/document-intelligence.md`.

## Alternatives Considered
- **Single hardcoded provider**: simpler, but a single point of failure/pricing-change risk for a
  commercial product whose core value proposition depends on extraction quality.
- **Self-hosted open-weight models**: rejected for v1 — no current volume justifies the
  infrastructure/ops cost; revisit only if per-extraction API cost crosses a documented threshold
  (tracked as a future ADR trigger, consistent with the legacy briefing's original reasoning).

## Consequences
- The Policy/Compliance Engine only ever consumes structured, schema-validated AI output — it never
  parses free text, which keeps AI Services swappable without touching downstream logic (see the
  context-boundary rule in `04-architecture/components.md`: "AI Services must not directly decide
  final compliance outcomes").
- Provider API keys/config become a per-environment secret, not a code constant.
- Exact model selection per task (e.g., which model for extraction vs. summarization) and cost
  thresholds are a `TBD` in `05-ai/ai-strategy.md`, resolved once real extraction volume/accuracy
  data exists.
