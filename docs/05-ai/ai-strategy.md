# AI Strategy

This document defines the overall AI strategy for JuriSense Gate: where AI is used, where it is
explicitly forbidden, how models are selected per task, how cost is controlled, and how the AI
Gateway abstraction (`ADR-005`) is organized. It is the entry point for `docs/05-ai/*` — the other
seven documents in this directory elaborate specific parts of this strategy in implementation
detail.

## Product framing

JuriSense Gate's product promise is: `APPROVE / REVIEW / BLOCK`, always accompanied by **WHY,
EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER, AUDIT TRAIL, VERIFICATION**
(`docs/00-project/overview.md`). AI's job in that pipeline is narrow and specific: turn unstructured
contracts and supplier documents into **structured, provenance-tagged data** that a deterministic
Policy Engine can evaluate, and that a human reviewer can trust and verify. AI is an **interpretation
and drafting-support layer**, not a decision-maker. That single sentence is the organizing principle
behind every other choice in this document.

## Where AI is used

| Use case | Bounded context | AI Services operation (`ADR-005`) | Output consumed by |
|---|---|---|---|
| Contract structured extraction (parties, value, duration, liability, privacy, obligations, clauses, etc.) | AI Services → Contracts & Documents | `extract()` | `ContractVersion.extracted_data`, `Clause` (see `structured-extraction.md`, `document-intelligence.md`) |
| Contract type / risk-category classification | AI Services | `classify()` | Routing/prioritization hints for reviewers (never the Decision itself) |
| Contract and review summarization for human reviewers | AI Services | `summarize()` | `ApprovalRequest` UI, reviewer worklist context |
| Supplier data normalization assistance (mapping free-form registry/corporate fields to the normalized `SupplierProfile` schema when a source returns inconsistent formats) | AI Services → Suppliers | `extract()` | `SupplierProfile` fields, always with a deterministic validation pass afterward |
| Precedent/context retrieval for human reviewers (similar historical clauses and their outcomes) | AI Services (RAG) | retrieval, not generation | Reviewer UI only — see `rag.md` for the explicit boundary with the Policy Engine |

Every one of these produces **structured output** (JSON schema / tool-calling) with **provenance**
(source document id, page, text span, confidence) attached to every extracted field — never
freeform prose parsed downstream (`ADR-005`). See `structured-extraction.md` for the exact schema
and `guardrails.md` for the validation contract that enforces this.

## Where AI must NOT be used

These are hard architectural boundaries, not style preferences. Several are enforced in code
(`guardrails.md`), not just in this document.

1. **AI never decides the final `APPROVE`/`REVIEW`/`BLOCK` outcome.** That aggregation is a pure,
   deterministic function of `RuleEvaluation` outcomes owned by `Policy & Compliance`
   (`ADR-010`, `docs/03-domain/policy-engine.md`). `AI Services` produces structured extraction and
   nothing downstream of it is allowed to write to `Decision.status` — this is the **context
   boundary rule** referenced throughout the domain model (`docs/04-architecture/components.md`,
   `AI-004` in `docs/01-product/functional-requirements.md`). See `guardrails.md` for how this is
   enforced as a guardrail, not just documented as an architecture note.
2. **AI is never a substitute for legal advice.** JuriSense Gate is a compliance-operations and
   contract-intelligence tool, not a law firm; its stated product limitation
   (`docs/01-product/product-definition.md`) is that structured extraction, risk flagging, and
   policy evaluation support a human's decision — they do not constitute legal counsel, and nothing
   in the product should be presented to a customer as such. AI-generated summaries and extractions
   carry a "not legal advice" framing wherever they are surfaced in the product.
3. **AI never has direct write access to business-domain tables outside `AI Services`.** Extraction
   output lands in `AI Services`'s own result records; it is `Policy & Compliance`'s application
   layer that reads and normalizes it into the evaluation context
   (`docs/03-domain/policy-engine.md` § Evaluation context). AI Services cannot write a `Decision`,
   `RuleEvaluation`, or `ApprovalRequest` row.
4. **AI does not autonomously take side-effecting actions** (sending emails, calling external
   sanctions APIs, modifying a `Policy`, contacting a supplier) in v1. Any future capability that
   would need this is an agent-loop question, addressed explicitly (and deferred) in
   `agent-architecture.md`.
5. **AI does not see or process data outside the requesting organization's tenant.** Every AI
   Services call is scoped by `organization_id`; retrieval (`rag.md`) is filtered by tenant at the
   query layer, not by convention.
6. **AI is not used for authentication, authorization, or any security-control decision** — those
   remain fully deterministic (`ADR-003`, `ADR-011`, `ADR-012`).

## Model selection strategy

Different tasks in the list above have very different accuracy/latency/cost profiles, so JuriSense
Gate does not use one model for everything. The strategy is **task-appropriate model tiering**,
configured per operation in the AI Gateway (`ADR-005`), not hardcoded per call site:

- **Tier 1 — fast/cheap classification model**: contract type classification, coarse risk-category
  tagging, and any task that is effectively a bounded multiple-choice decision over short input.
  Optimized for latency and cost; run synchronously in the ingestion pipeline where possible.
- **Tier 2 — strong extraction model**: full structured contract extraction (the schema in
  `structured-extraction.md`), where the cost of a wrong field (e.g. missing an unlimited-liability
  clause) is high and the input is long and structurally complex. Optimized for accuracy and
  instruction-following on structured output, at higher latency/cost.
- **Tier 3 — summarization model**: reviewer-facing summaries. Optimized for fluency/conciseness;
  lower accuracy bar than Tier 2 because summaries are supporting context, never the extraction of
  record (the structured fields from Tier 2 remain the source of truth for policy evaluation).

Model **selection per tier is configuration, not code** — the AI Gateway resolves "which model for
extraction" from per-environment config, so a model swap (e.g. a new provider release, or a fallback
during an outage) never requires a code change in `Policy & Compliance` or any other consuming
context.

> Status: TBD / Current preferred option: OpenAI GPT-5-class model for Tier 2 extraction with
> Anthropic Claude as the Tier 2 fallback (or vice versa, whichever benchmarks better on the golden
> dataset — see `evaluation.md`), and a smaller/cheaper model from the same two providers for Tier 1
> classification / Tier 3 summarization / embeddings. / Why undecided: exact model names and
> versions change faster than this document should, and the right choice depends on the golden
> dataset's first accuracy/cost results, which do not exist yet. / Resolution: run the golden
> dataset (`evaluation.md`) against the top 2–3 candidate models per tier from OpenAI and Anthropic
> before committing a default in configuration. / Decision artifact: a dated addendum to this file
> (or a new ADR if the choice materially changes provider-abstraction assumptions) once the
> benchmark exists.

## Cost control

AI is a direct, per-call variable cost, and the pricing model
(`docs/02-business/pricing-strategy.md`) explicitly meters **AI executions per period** as a
plan-limited resource, alongside suppliers analyzed and contracts reviewed
(`BR-ORG-003`, `docs/03-domain/business-rules.md`). Cost control is therefore both an engineering and
a product-limits concern:

1. **Per-call token accounting**: every AI Gateway call records prompt tokens, completion tokens,
   provider, model, and computed cost (using the provider's published per-token pricing at call
   time) against the `organization_id` that triggered it. This is the same event this document's
   `observability.md` companion describes as part of the AI execution log.
2. **Plan-limit enforcement**: `AI executions` (one execution = one Gateway call, regardless of
   which of `extract()`/`classify()`/`summarize()` was used) are counted per organization per
   billing period and enforced at the point of triggering a new execution — mirroring the existing
   enforcement pattern for other plan-limited resources (`BR-ORG-003`: blocks new creation, never
   deletes existing data). Exceeding the limit blocks new AI-triggering actions (e.g., uploading
   another contract for extraction) with a clear upgrade prompt, not a silent degradation.
3. **Avoiding redundant calls**: a `ContractVersion` is extracted exactly once (extraction output is
   immutable, per `docs/03-domain/domain-model.md`); re-analysis only happens on an explicit new
   negotiation round (new `ContractVersion`) or an explicit manual re-run, never automatically on
   every read.
4. **Chunk-size discipline**: `document-intelligence.md`'s chunking strategy is sized to minimize
   redundant token overlap while preserving citation accuracy — chunk overlap is a tuned parameter,
   not maximized "just in case."
5. **Model tiering itself is a cost control**: routing classification/summarization to cheaper
   models (see above) is as much a cost decision as an accuracy one.
6. **Retrieval reuses stored embeddings** (`rag.md`) rather than re-embedding the same content on
   every query.

> Status: TBD / Current preferred option: a soft per-organization monthly AI-cost budget with an
> internal alert (not a hard customer-facing cutoff separate from the plan's AI-execution limit) so
> Engineering notices cost anomalies before Finance does. / Why undecided: no real usage data exists
> yet to size a sane default budget per plan tier. / Resolution: set an initial conservative budget
> once the first cohort of paying organizations has a full billing period of AI usage data.
> / Decision artifact: an update to `docs/02-business/pricing-strategy.md` plus the alerting
> threshold recorded in `observability.md`.

## AI Gateway architecture (recap of `ADR-005`)

All AI usage in JuriSense Gate goes through a single internal **AI Gateway** abstraction inside the
`AI Services` bounded context:

```
Consumer (e.g. Contracts & Documents ingestion pipeline)
    │  calls
    ▼
AI Gateway interface:  extract(schema, input, context)
                        classify(labels, input, context)
                        summarize(input, context)
    │  resolves provider/model from config
    ▼
Provider Adapter (OpenAIAdapter | AnthropicAdapter)
    │  structured output only (JSON schema / tool-calling) — never freeform text parsing
    ▼
Provider API (OpenAI | Anthropic)
```

Key properties (all from `ADR-005`, restated here because they drive everything else in this
directory):

- **Pluggable adapters** for OpenAI and Anthropic Claude, selected per task type via configuration.
- **Automatic fallback** to a secondary provider on error/timeout — no manual intervention required
  to keep extraction flowing during a provider outage (see `guardrails.md` and `observability.md`
  for how a fallback event is logged and surfaced).
- **Structured output only.** Every Gateway call declares a JSON schema (or tool/function
  definition); the Gateway rejects and retries on a response that fails schema validation
  (`guardrails.md`). Free-text parsing of model output is architecturally disallowed.
- **Provenance is a Gateway-level contract, not a per-call convention**: every `extract()` response
  is required to carry, per field, a confidence score and a source citation (document id, page,
  text span). A provider adapter that cannot produce this shape is not usable for extraction calls.
- **AI Services never decides a compliance outcome** — see "Where AI must NOT be used" above; this
  is the load-bearing consequence of the Gateway design, not a separate rule.

## Relationship to the rest of `docs/05-ai/`

- `agent-architecture.md` — whether a given AI-touching process should be a pipeline, a single
  tool-calling step, or a true multi-step agent (the answer for v1 is almost always "not an agent").
- `document-intelligence.md` — the concrete ingestion/extraction pipeline this strategy assumes.
- `rag.md` — the retrieval layer behind the precedent-lookup use case above.
- `structured-extraction.md` — the exact schema referenced throughout this document.
- `evaluation.md` — how "is the AI good enough" is measured, including the golden dataset that
  resolves the model-selection TBD above.
- `guardrails.md` — how the "must NOT" boundaries above are technically enforced.
- `observability.md` — how every AI call is logged, costed, and linked to the Decision Passport.
