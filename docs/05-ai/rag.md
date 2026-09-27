# Retrieval-Augmented Generation (RAG)

This document specifies JuriSense Gate's retrieval strategy: what gets embedded, how hybrid search
works, and — most importantly — the explicit boundary between retrieval used **for human context**
and the Policy Engine, which never uses retrieval in its evaluation logic. See `ADR-009` for the
accepted infrastructure decision (`PostgreSQL + pgvector`, no standalone vector database) that this
document elaborates.

## What gets embedded

| Corpus | Purpose | Scope |
|---|---|---|
| **Policy playbooks** — the organization's own policy rationale/guidance text (not the executable `Rule` DSL itself, which the Policy Engine evaluates directly and deterministically, but any surrounding explanatory/playbook text a compliance team maintains) | Let a reviewer ask "what does our policy generally say about X" and get relevant playbook passages | Per-organization |
| **Prior `ComplianceReview`/`Decision` records** (rationale text, `RuleEvaluation.rationale`, override justifications) | Precedent lookup: "how have we handled this kind of situation before" | Per-organization |
| **Contract clause libraries** — the accumulated set of previously-extracted `Clause` text spans, tagged by `clause_type` and linked to the `Decision` outcome their contract eventually received | The concrete use case below: surfacing similar historical clauses and their outcomes | Per-organization |
| **(Future) regulatory/legislative text** | Referenced in `ADR-009`'s context as a later feature; not built in v1 | Cross-organization (public text), filtered by jurisdiction pack |

Embeddings are computed once per source item at creation/update time (e.g. once a `Decision` is
finalized, once a `Clause` is extracted) and stored in `pgvector`-backed tables, not recomputed on
every query.

## Storage and indexing (per `ADR-009`)

- **PostgreSQL + `pgvector`** stores embedding vectors alongside the row's own metadata columns
  (`organization_id`, `source_type`, `source_id`, `clause_type` where applicable,
  `decision_outcome` where applicable, `created_at`). No standalone vector database (Pinecone,
  Weaviate, Qdrant) is used for v1 — the current and near-future data volume (hundreds to low
  thousands of documents per organization) does not justify the added operational dependency
  (`ADR-009`).
- **Full-text search** uses Postgres's native `tsvector`/`tsquery` machinery over the same source
  text, indexed alongside the vector column.
- **Metadata filters** (`organization_id` mandatory on every query — this is a tenant-isolation
  requirement, not an optimization; document type; policy version; clause type) are applied as
  ordinary `WHERE` predicates before or alongside the similarity/full-text ranking, never as an
  afterthought filter on unfiltered results.

## Hybrid retrieval

A retrieval query combines three signals rather than relying on vector similarity alone, because
short legal clause text often has near-identical vocabulary across very different clauses (e.g. two
liability clauses can be lexically similar but differ in the one number/word that matters):

1. **Vector similarity** (`pgvector` cosine distance) over the query embedding vs. stored embeddings
   — captures semantic similarity.
2. **Full-text search** (`ts_rank` over `tsvector`) over the same query text — anchors on exact
   legal terminology, defined-term names, and numeric values that embeddings alone can under-weight.
3. **Metadata filters** — `organization_id` (mandatory, tenant isolation), plus optional filters
   such as `clause_type`, `document type`, or `policy_version`.

The two ranked signals (vector, full-text) are combined via score fusion (e.g. reciprocal rank
fusion over the two ranked lists) into a single ranked result set, then truncated to top-k. This
hybrid approach is deliberately simple — it does not require a re-ranking model call, keeping
retrieval latency and cost low (consistent with `ai-strategy.md`'s cost-control posture: retrieval
for human context should be cheap enough to run on every review, not gated behind its own
plan-limited "AI execution").

## Concrete use case: liability clause precedent lookup

> When evaluating a new contract's liability clause, retrieve similar historical clauses and their
> decisions as supporting context for a human reviewer.

Flow:

1. A `ComplianceReview` produces a `RuleEvaluation` with outcome `REVIEW` for `LEGAL-008`
   ("Unlimited Liability Requires Legal Review", `docs/03-domain/policy-engine.md`), tied to a
   specific `Clause` of `clause_type: liability`.
2. When the assigned reviewer opens the resulting `ApprovalRequest`, the reviewer UI issues a hybrid
   retrieval query: `clause_type = liability`, `organization_id = <this org>`, query text = the
   flagged clause's `text_span` content, top-k (e.g. 5).
3. The system returns the most similar historical liability clauses **from this organization's own
   contract history**, each annotated with: the source contract/clause citation (page/span,
   `document-intelligence.md`), the `Decision` outcome that contract eventually received, and (if
   applicable) any override justification recorded against that decision.
4. This is displayed to the reviewer as a **"similar past clauses" panel** alongside the current
   review — pure supporting context. The reviewer reads it, forms their own judgment, and still
   resolves the `ApprovalRequest` (`approved`/`rejected`) themselves (`BR-APR-001`).

## The explicit boundary: retrieval is for humans, never for policy evaluation

This is the single most important rule in this document, and it is stated in three places in this
codebase's documentation deliberately (here, `docs/03-domain/policy-engine.md`, and
`ai-strategy.md`) because it is easy to accidentally erode:

- The **Policy Engine's evaluation logic never performs retrieval and never uses fuzzy/semantic
  matching**. Every `Rule`'s `when` clause is evaluated against the **normalized evaluation
  context** — exact, typed fields such as `contract.liability.type`, `contract.value.brl`,
  `supplier.sanctions_hit` (`docs/03-domain/policy-engine.md` § Evaluation context) — built entirely
  from `SupplierProfile`/`SupplierCheck` and `ContractVersion.extracted_data`/`Clause`. There is no
  code path where a `pgvector` similarity score or a retrieved precedent feeds into a
  `RuleEvaluation.outcome`.
- Retrieval output (the "similar past clauses" panel, playbook search results) is **display-only**
  data returned to a UI layer for a human. It is never written back into `ContractVersion.extracted_data`,
  never passed to a `Rule`'s `when` evaluation, and never used to auto-populate a normalized
  evaluation-context field.
- This mirrors, and is a direct consequence of, the broader context-boundary rule that `AI Services`
  never decides a compliance outcome (`ai-strategy.md`, `AI-004`) — RAG output is AI Services
  output, so the same boundary applies to it without exception.

## Tenant isolation in retrieval

Because embeddings for policy playbooks, prior decisions, and clause libraries are all
organization-owned data, **every retrieval query is scoped by `organization_id` at the query level**
(`WHERE organization_id = :org_id`, applied before ranking, not after) — never relying on
application-layer filtering of an already-fetched, unscoped result set. This mirrors the tenant
isolation requirement already stated for every tenant-owned table (`SEC-001`,
`docs/01-product/functional-requirements.md`) and applies even though the future regulatory-text
corpus (cross-organization, public) is an intentional, documented exception.

## Reindexing / freshness

- A new `Clause` embedding is created when its parent `ContractVersion` completes extraction
  (`contract.analysis_completed`).
- A `Decision`'s rationale/outcome embedding (and the clause-outcome link used by the precedent
  lookup above) is created/updated when the `Decision` is created (`decision.created`) and again if
  overridden (`decision.overridden`), so the precedent panel always reflects the final, current
  state of a past decision.
- Policy playbook embeddings are refreshed when the organization edits its playbook text (this is
  separate from `PolicyVersion` publication — the executable `Rule` DSL is never embedded/retrieved,
  only the surrounding human-readable playbook guidance is).
