# AI Observability

This document specifies what gets logged and traced for the AI subsystem, why it is linked to the
`ContractVersion` it was run for, and how it becomes part of the **Decision Passport**
(`docs/03-domain/evidence.md`). It also recommends a lightweight dashboard for extraction volume,
cost, and confidence trends.

## Why this matters beyond ordinary application logging

Two things make AI observability here different from generic application logging:

1. **It's evidence, not just diagnostics.** `docs/00-project/overview.md` states that a
   `Decision Passport` includes "AI executions with model/prompt version" as part of what makes a
   compliance decision defensible months or years later. An AI call's log record is not disposable
   operational data — for any `ContractVersion` that fed into a `Decision`, its extraction call's log
   is part of the evidence a customer may need to produce to an auditor or regulator.
2. **It's the input to cost control and evaluation.** `ai-strategy.md`'s per-organization cost
   tracking and `evaluation.md`'s production spot-review sampling and confidence-trend monitoring both
   depend on this log existing, structured, and queryable — they are not separate logging efforts.

## What gets logged per AI Gateway call

Every `extract()`/`classify()`/`summarize()` call through the AI Gateway (`ADR-005`) produces one
structured log record (an `AIExecution` record) with:

| Field | Purpose |
|---|---|
| `execution_id` | Unique id for this call, referenced by the `extraction_run_id` in `structured-extraction.md`'s output |
| `organization_id` | Tenant scoping — required for cost accounting (`ai-strategy.md`) and tenant-isolated querying |
| `contract_version_id` (or the relevant entity id for non-extraction calls) | Links this execution to the domain entity it was run for — this is the join key into the Decision Passport |
| `operation` | `extract` \| `classify` \| `summarize` |
| `provider` | `openai` \| `anthropic` |
| `model_name` | Exact model identifier used |
| `prompt_version` | Version identifier of the prompt/schema used (matches `structured-extraction.md`'s `model.prompt_version`) — this is what makes a later regression traceable to a specific prompt change (`evaluation.md`) |
| `started_at` / `completed_at` / `latency_ms` | Timing |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | Token accounting |
| `estimated_cost` | Computed from provider pricing at call time — feeds `ai-strategy.md`'s per-organization cost tracking |
| `status` | `success` \| `schema_invalid_retry` \| `schema_invalid_failed` \| `provider_error_fallback` \| `provider_error_failed` \| `timeout` — see `guardrails.md` for what each of these triggers |
| `fallback_used` (boolean) | Whether the secondary provider was used for this execution |
| `confidence_summary` | Aggregate confidence for this execution (e.g. min/mean across extracted fields) — cheap to query for trend dashboards without pulling the full extraction payload |
| `retry_count` | Number of schema-validation retries this execution needed |

Fields are chosen so that **cost, latency, confidence, and reliability (fallback/retry rate) trends
are all queryable without joining back to the full extraction payload** — the full payload
(`structured-extraction.md`'s JSON) is stored separately (as part of `ContractVersion.extracted_data`)
and referenced by `execution_id`, not duplicated into the log record.

## Linkage to the Decision Passport

Per `docs/03-domain/evidence.md` (the `EvidencePackage` that backs every `Decision`,
`docs/03-domain/domain-model.md`), the `AIExecution` records tied to a `ContractVersion`'s
`extraction_run_id` are included as evidence when that `ContractVersion` contributes to a
`ComplianceReview`/`Decision`. Concretely, an `EvidencePackage` entry of `type: ai_execution`
references the `AIExecution.execution_id`, carrying enough of the record above (model, provider,
prompt version, confidence summary) to answer "which model and prompt version produced the extracted
data this decision relied on" without needing to separately archive full model transcripts in the
evidence package itself (the transcript/log remains queryable via `execution_id` in the AI
observability store, while the evidence package carries the lighter-weight citation).

This is what turns "AI executions with model/prompt version" from a documentation promise
(`docs/00-project/overview.md`) into a concrete, always-present field on every `Decision` that used
AI-derived evidence.

## Prompt injection and anomaly logging

As noted in `guardrails.md`, certain `AIExecution` records are flagged for security-relevant review,
not just quality review: repeated `schema_invalid_*` statuses from the same document, or a
schema-valid response whose content looks like it echoes injected instructions. These are logged with
the same `AIExecution` shape plus a `flagged_reason` field, and should be reviewable independently of
the cost/confidence dashboard (below) as a distinct, security-oriented view.

## Dashboard recommendation

A lightweight dashboard, scoped per organization (and a cross-organization operator view), showing:

- **Extraction volume over time** (count of `AIExecution` records by `operation`, by day/week) —
  ties directly to plan-limit consumption (`ai-strategy.md`, `BR-ORG-003`).
- **Cost over time**, same grouping, plus a running total against any configured budget
  (`ai-strategy.md`'s cost-control TBD).
- **Confidence trends** (`confidence_summary` distribution over time, per `operation` and, for
  extraction, per field where practical) — a downward drift is an early warning of model/provider
  drift even before a human spot-review (`evaluation.md`) catches it.
- **Reliability** (fallback rate, retry rate, failure rate) — a rising fallback rate is an early
  warning of a primary provider degrading before it becomes a customer-visible incident.

This does not need to be a bespoke analytics product for v1 — a simple internal view (even a
scheduled query + a small internal dashboard) satisfies the need; the requirement is that these four
views exist and are checked regularly, not that they are built on any particular platform.

> Status: TBD / Current preferred option: adopt a lightweight, purpose-built LLM observability tool
> (e.g. Langfuse or an equivalent) for the trace/cost/confidence views rather than building a custom
> dashboard from scratch, given how directly `AIExecution` records above map to what such tools
> already model (traces, token cost, prompt versions). / Why undecided: the choice depends on a quick
> evaluation of self-hosting/data-residency implications (contract-derived confidence summaries and
> metadata may need to stay within JuriSense Gate's own infrastructure boundary given LGPD
> considerations, `docs/06-blockchain/privacy.md`'s "no confidential data leaves the boundary
> unnecessarily" spirit) versus the integration effort of a fully custom solution. / Resolution:
> spike a lightweight LLM observability tool against the `AIExecution` schema above for one sprint,
> confirm it can be self-hosted or configured to avoid sending contract content off JuriSense Gate's
> infrastructure, and decide based on integration effort and data-residency fit. / Decision artifact:
> a dated addendum to this document, or a new ADR if the tooling choice introduces a new
> infrastructure dependency comparable in weight to the ones already covered by existing ADRs.

## Relationship to other guardrails and evaluation

- `guardrails.md` defines what happens *at the moment* a call fails or looks suspicious; this document
  defines how that moment is recorded so it can be reviewed, aggregated, and used as evidence
  afterward.
- `evaluation.md`'s golden-dataset and spot-review processes both consume this log (to find
  low-confidence or flagged executions worth reviewing, and to compare metrics across
  `prompt_version`s over time).
- `ai-strategy.md`'s cost-control section is only enforceable because every execution's token/cost
  data is captured here, per organization, at the point of the call.
