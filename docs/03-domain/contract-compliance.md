# Contract Compliance

This document specifies the full behavioral lifecycle of contract compliance in the **Contracts &
Documents** bounded context: document ingestion, `ContractVersion` creation, AI structured
extraction, clause-level provenance, and how extracted data becomes the normalized evaluation
context that **Policy & Compliance** consumes. See `docs/03-domain/domain-model.md` for entity
definitions (`Document`, `Contract`, `ContractVersion`, `Clause`), `docs/03-domain/business-rules.md`
for invariants (`BR-CON-*`), and `docs/03-domain/policy-engine.md` for the consuming side of this
pipeline.

## Purpose

Contract Intelligence is the half of JuriSense Gate that turns an uploaded contract file into
**structured, citable, machine-evaluable data** — never prose summaries — so that the Policy Engine
can evaluate it deterministically instead of a human re-reading the document every time
(`docs/00-project/overview.md` → "Contract Intelligence"). Every extracted fact remains traceable
back to the exact page and text span it came from, because a compliance decision that cannot point
to its source document is not defensible in an audit (see `docs/03-domain/evidence.md`).

## What is extracted

Per `docs/00-project/overview.md` and `docs/05-ai/structured-extraction.md` (schema owner), a
`ContractVersion`'s `extracted_data` covers: parties, value and currency, duration,
renewal/termination terms, liability (type — capped/unlimited — and cap amount if present),
confidentiality terms, IP ownership/licensing terms, data-processing/DPA terms (whether the
contract involves personal-data processing, and whether a DPA is present), jurisdiction/governing
law, guarantees, penalties, obligations, and deadlines. Every one of these fields is a candidate
input to a policy rule (see the worked examples in `docs/03-domain/policy-engine.md`: `LEGAL-008`
on `contract.liability.type`, `FIN-003`/`FIN-004` on `contract.value.brl`, `LGPD-001` on
`contract.processes_personal_data`/`contract.dpa_present`).

## Entities involved

- **`Document`** (*Contracts & Documents*) — the immutable uploaded file plus its `content_hash`
  (SHA-256), `storage_key`, and `mime_type`. A `Document` never mutates after upload; a corrected or
  renegotiated contract is always a **new** `Document` backing a **new** `ContractVersion`
  (`domain-model.md`: "a `Document` is itself an immutable version; re-upload creates a new
  `Document`").
- **`Contract`** — the logical, durable agreement with a `Supplier`, spanning many versions over
  its lifetime. Its own lifecycle (`draft → under_review → active → renewed|terminated|expired`) is
  the commercial/legal status of the relationship, distinct from any single version's
  extraction/analysis status.
- **`ContractVersion`** — one immutable snapshot: a `document_id` reference, `version_number`,
  `extracted_data` (the structured JSON), and `extraction_confidence`. This is the versioning unit
  for `Contract` (`BR-CON-002`: "every negotiation round creates a new `ContractVersion`; existing
  versions are never edited in place").
- **`Clause`** — one AI-identified, citable clause (liability, DPA, termination, etc.) inside a
  `ContractVersion`, carrying `clause_type`, `page`, `text_span`, and `confidence`. A `Clause` is
  what a `RuleEvaluation` cites as evidence when a rule fires based on contract content
  (`domain-model.md`: "referenced by `RuleEvaluation` as evidence").

## Pipeline: ingestion → extraction → evaluable context

```
Document uploaded (PDF/DOCX/TXT)
    ↓
document.uploaded  →  malware/type-spoofing scan (SEC-003)  →  document.processed
    ↓
ContractVersion created (contract.created on first version / contract.version_created on later ones)
    ↓
AI structured extraction runs via the AI Gateway (ADR-005)
    ↓
extracted_data populated + per-field confidence scores + Clause records with page/span provenance
    ↓
extraction_confidence evaluated against the minimum threshold (BR-CON-003)
    ↓
  ┌─ meets threshold ──────────────► ContractVersion: analyzed  ─┐
  │                                                               │
  └─ below threshold on any field ─► human confirmation required │
                                       (blocks "analyzed" state)  │
                                                                   ↓
                                               contract.analysis_completed
                                                                   ↓
                              Policy & Compliance builds the normalized evaluation context
                              (docs/03-domain/policy-engine.md) from extracted_data + Clause list
                                                                   ↓
                                                    ComplianceReview can now run
```

Step-by-step:

1. **Upload.** An authorized user uploads a contract file (`CON-001`). A `Document` is created with
   its `content_hash` computed immediately and never recomputed (`domain-model.md` invariant) —
   this hash is what later anchors into the `EvidencePackage` (`docs/03-domain/evidence.md`).
   `document.uploaded` fires, then the file is scanned for malware/type-spoofing before any content
   processing begins (`SEC-003`); `document.processed` fires once the scan clears.
2. **`ContractVersion` creation.** A new `ContractVersion` is created referencing this `Document`.
   If this is the first version of a new logical agreement, a `Contract` is also created
   (`contract.created`); every subsequent negotiation round on the same `Contract` creates another
   `ContractVersion` and fires `contract.version_created` — the prior version is never edited
   (`BR-CON-002`).
3. **AI structured extraction.** `AI Services` runs extraction through the AI Gateway abstraction
   (`ADR-005`), never called directly by `Contracts & Documents` or `Policy & Compliance`
   (`AI-001`). The output populates `extracted_data` and creates one `Clause` per identified
   citable clause, each carrying its own `confidence` and page/text-span provenance (`AI-002`,
   `CON-004`). `AI-004` and the context boundary rule (`docs/04-architecture/components.md`) are
   absolute here: AI Services produces facts and confidence scores — it never sets a `Decision`
   status, directly or indirectly.
4. **Confidence gate.** `BR-CON-003` governs the transition to `analyzed`: a `ContractVersion`
   cannot be marked `analyzed` until either (a) every extracted field meets the minimum confidence
   threshold, or (b) a human has manually confirmed each low-confidence field. Confirmed fields are
   recorded as human-confirmed (not silently promoted to "AI-confident"), preserving an honest
   provenance trail — the `EvidencePackage` for any `Decision` that used this version can later show
   exactly which facts were AI-extracted at what confidence versus human-confirmed.
5. **`contract.analysis_completed`.** Fires once the `ContractVersion` reaches `analyzed`. This is
   the signal that `Policy & Compliance` may now build an evaluation context from this version.
6. **Normalization into the evaluation context.** Per `docs/03-domain/policy-engine.md`'s
   "Evaluation context & input normalization" section, `Policy & Compliance`'s application layer —
   not `AI Services` — builds the flat, typed evaluation context from
   `ContractVersion.extracted_data` and its `Clause` list (e.g. `contract.liability.type`,
   `contract.value.brl`, `contract.value.currency`, `contract.processes_personal_data`,
   `contract.dpa_present`), combined with the `Supplier`/`SupplierProfile`/`SupplierCheck` fields
   from `docs/03-domain/supplier-compliance.md`. `BR-CMP-001` makes this mandatory: a
   `ComplianceReview` always evaluates against this normalized context, **never** against raw,
   unnormalized AI output. This is also the architectural line that keeps `AI-004` true in
   practice — normalization is a deliberate, reviewable mapping step, not a pass-through.

## Contract lifecycle states

`Contract.status`: `draft → under_review → active → renewed|terminated|expired`. This is the
commercial lifecycle and is largely independent of any one `ContractVersion`'s extraction state,
though in practice a `Contract` cannot productively reach `active` until at least one of its
versions is `analyzed` and has passed a `ComplianceReview` with an `APPROVE` (or an overridden)
`Decision` — that gating is an application-layer workflow rule, not a domain invariant.

`ContractVersion.status`: `extracted → analyzed → (superseded by next version)`. Only the current
(latest, `analyzed`) version of an active `Contract` is normally the subject of a live
`ComplianceReview`; superseded versions remain immutable historical record, retained exactly as
they were evaluated, because past `Decision`s reference them by id (`BR-DEC-001`).

## What triggers re-analysis

- **New `ContractVersion`.** Every renegotiation round is a distinct extraction + analysis cycle;
  nothing about a prior version's `extracted_data`, `Clause` set, or `ComplianceReview` history is
  reused or assumed still valid.
- **Renewal.** A `renewed` `Contract` conventionally introduces a new `ContractVersion` (even if
  terms are unchanged on paper, the renewal itself is a new negotiation event with a new duration/
  term window) and therefore a fresh extraction + `ComplianceReview` cycle.
- **Decision expiration or policy change.** Per `BR-DEC-004`, a `Decision`'s `valid_until` expiring,
  or a newly published `PolicyVersion` that affects rules the `Decision` used, emits
  `compliance.review_required` even without a new `ContractVersion` — the existing, already-
  `analyzed` `ContractVersion` is simply re-evaluated against the current (or a specified) policy.
  This case does not re-run AI extraction; it re-runs policy evaluation over already-normalized
  data.
- **Supplier-side change.** A material `supplier.profile_updated` event (most notably a new
  sanctions hit — `docs/03-domain/supplier-compliance.md`) on the `Contract`'s `Supplier` can also
  trigger `compliance.review_required`, independent of any contract-side change.

## Confidence thresholds gating human confirmation

`BR-CON-003` is the controlling rule: *"A `ContractVersion` cannot be marked `analyzed` until AI
extraction has produced a structured result meeting the minimum confidence threshold (`TBD` — see
`docs/05-ai/evaluation.md`) or a human has manually confirmed low-confidence fields."*

Status: TBD / Current preferred option: a per-field numeric confidence threshold (candidate default
in the 0.80–0.85 range on a 0–1 confidence score, applied per extracted field rather than as one
document-level average, so that one weak field — e.g., an ambiguous liability cap — cannot be
masked by high confidence on unrelated fields like party names) / Why undecided: the right
threshold depends on the extraction model(s) selected and calibrated in `docs/05-ai/ai-strategy.md`
and `docs/05-ai/evaluation.md`, which requires empirical evaluation against a labeled contract
sample not yet assembled / Resolution: `docs/05-ai/evaluation.md` will define the threshold(s) once
model selection and a calibration/eval pass are complete; this document defers to it and does not
invent a number / Decision artifact: `docs/05-ai/evaluation.md` (to be authored), cross-referenced
from `BR-CON-003`.

Operationally, regardless of where the exact number lands: fields below threshold block the
`analyzed` transition until a human reviewer either (a) confirms the AI-extracted value as correct,
or (b) corrects it. A corrected value is recorded as human-provided, not as an AI extraction with
adjusted confidence — this distinction is preserved permanently in `extracted_data`'s field-level
metadata and surfaces later in the `EvidencePackage` (`docs/03-domain/evidence.md`) as part of
"how was this fact established?".

## Relationship to other domain documents

- `CON-001` through `CON-005` (`docs/01-product/functional-requirements.md`) are the capability
  requirements this pipeline implements.
- `BR-CON-001` through `BR-CON-004` are the authoritative invariants; this document elaborates their
  behavior end to end.
- The consuming side — how the normalized context is combined with supplier evidence and evaluated
  rule-by-rule — is specified in `docs/03-domain/policy-engine.md` and `ADR-010`.
- What happens when a `ComplianceReview` over this data produces `REVIEW` or `BLOCK` is specified in
  `docs/03-domain/approvals.md`.
- How `Document` hashes, `Clause` citations, and extraction provenance become durable evidence is
  specified in `docs/03-domain/evidence.md`.
