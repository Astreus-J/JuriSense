# AI Evaluation

This document specifies how AI quality is measured before a change ships (prompt edit, model swap,
schema change) and monitored after it ships. It resolves the confidence-threshold `TBD`s referenced
in `BR-CON-003` (`docs/03-domain/business-rules.md`) and `ai-strategy.md`'s model-selection `TBD`,
and it is the authority `document-intelligence.md` and `guardrails.md` point to for "what confidence
is good enough."

## What is measured

| Metric | Definition | Why it matters here specifically |
|---|---|---|
| **Extraction accuracy** | Per-field accuracy: does the extracted `value` match the human-verified expected value (exact match for enums/dates/booleans/amounts; a defined similarity threshold for free-text fields like `termination_for_cause_conditions`) | This is the metric closest to the product's core promise — a wrong `contract.liability.type` can silently misroute a `ComplianceReview` |
| **Classification accuracy** | Standard precision/recall/F1 per label for contract-type and risk-category classification | Cheap Tier-1 model choice (`ai-strategy.md`) is only justified if accuracy holds up |
| **Hallucination rate** | Fraction of extracted fields whose `value` is not actually supported by the cited `text_span` (i.e., the model invented or over-generalized a value) | Directly threatens the "EVIDENCE" pillar of the product promise (`docs/00-project/overview.md`) — a plausible-looking but unsupported value is worse than a missing one, because it can pass a confidence check without being true |
| **Citation correctness** | Fraction of `clauses[]`/field `provenance` entries whose cited `page`/`text_span` actually contains the claimed clause/value when the span is re-read from the source document | The mechanical, checkable half of hallucination detection — this can be verified by exact string comparison, no judgment call needed |
| **False positive rate on risk flags** | Fraction of AI-driven risk classifications/flags that a human reviewer disagrees with as *not actually risky* | High false-positive rates erode reviewer trust and cause "approval fatigue" (rubber-stamping) |
| **False negative rate on risk flags** | Fraction of contracts a human later flags as risky that AI extraction did not surface (e.g., a liability clause it mis-typed as `capped` when it was actually `unlimited`) | This is the more dangerous failure direction — it lets a real risk pass silently through the Policy Engine, which only ever sees what extraction reports |

Extraction accuracy and citation correctness are the two metrics with the most direct load-bearing
role, because everything downstream (`policy-engine.md`'s normalized context, `RuleEvaluation`,
ultimately `Decision`) is built entirely from extraction output.

## Method 1: golden datasets

A **golden dataset** is a curated set of real (or realistic, anonymized/synthetic where a real
contract can't be used) contracts, each with a **human-verified expected extraction** — the full
`structured-extraction.md` schema, filled in by a person with the legal/compliance background to get
it right, for every field and every clause.

- The golden dataset is built incrementally, starting from the diversity that matters most: contract
  types the target market (`docs/00-project/overview.md`'s 50–1,000-employee tech companies) actually
  signs — SaaS subscriptions, MSAs, consultancy agreements, NDAs, DPAs — and deliberately includes
  edge cases: unlimited liability, missing DPA despite personal-data processing, auto-renewal traps,
  scanned/OCR'd contracts, non-Portuguese contracts if the customer base needs them.
  It is versioned (e.g. in a repository directory, not ad hoc spreadsheets) so a dataset version can
  itself be cited by a regression run.
- Running the current extraction pipeline against the golden dataset produces the per-field accuracy,
  hallucination, and citation-correctness metrics above, comparable across model/prompt versions.

## Method 2: CI regression suites

Whenever a **prompt version** or **model** changes (`structured-extraction.md`'s `model.prompt_version`
field is exactly what makes a change identifiable), a regression suite runs the full golden dataset
through the candidate configuration and reports the metrics above **before** the change is allowed to
reach production configuration:

- A regression run is a pass/fail gate in CI, mirroring how `docs/03-domain/policy-engine.md`
  describes policy **fixture cases** running in CI for `PolicyVersion` changes — the same discipline
  applies to prompt/model changes, because an extraction regression is exactly as consequential as a
  policy regression.
- A regression that shows a **metric regression beyond a configured tolerance** on any of the metrics
  above blocks promotion of the new prompt/model version to production configuration, requiring an
  explicit override with justification (mirroring `ADR-010`'s override discipline for decisions —
  changes that affect what the system considers "true" deserve the same rigor).
- Golden-dataset results are stored per prompt/model version, so accuracy trends over time are
  directly comparable, not just pass/fail snapshots.

## Method 3: LLM-as-judge (used cautiously)

An LLM can be used to **triage** candidate extraction errors at a scale a human reviewer can't match
alone — e.g., flagging which of a large regression run's outputs look most likely to be wrong,
scoring free-text field similarity where exact match isn't meaningful (e.g.,
`termination_for_cause_conditions`), or pre-sorting hallucination candidates for human review.

**LLM-as-judge is never the final quality gate.** It is a triage/prioritization aid that narrows what
a human needs to look at; the human spot-review (Method 4) and the exact-match/citation-correctness
checks (Method 1/2, which are mechanical, not model-judged) remain the actual gate. This restriction
exists because an LLM judge shares failure modes with the system it's judging (the same kind of
misreading or overconfidence), so it cannot be trusted as sole arbiter of its own family's output
quality.

## Method 4: human spot-review sampling

In production, a sample of completed extractions is routed to human spot-review independent of the
confidence-threshold gate (`guardrails.md`) that already forces low-confidence fields to human
confirmation — spot-review exists specifically to catch **high-confidence wrong answers** that the
threshold gate, by construction, does not catch.

- Sampling rate is higher immediately after any prompt/model change (to catch a regression that
  slipped past the golden dataset) and can taper for a stable configuration, but never drops to zero
  — confidence calibration can drift silently over time even with no code change (e.g. a provider
  updates a model under a versioned name).
- Spot-review findings feed back into the golden dataset (a real production miss becomes a new golden
  dataset case) so the dataset grows from real failures, not just initial curation.

## What "good enough to ship" means

Qualitatively, a prompt/model configuration is good enough to promote to production when:

- Extraction accuracy on required fields (the fields the Policy Engine actually reads —
  `contract.value.*`, `contract.liability.*`, `contract.processes_personal_data`,
  `contract.dpa_present`, and any clause type referenced by an active `Rule`) is high enough that the
  **residual error rate is smaller than the human-confirmation gate's catch rate** — i.e., the
  confidence threshold plus human confirmation of low-confidence fields (`BR-CON-003`) should be
  catching the errors that matter, not routinely missing them.
- Hallucination rate and citation-correctness failures are low enough that a reviewer can trust a
  citation without independently re-reading the whole source document every time — trust in
  citations is a product-adoption requirement, not just an accuracy nicety.
- False negative rate on risk flags (the dangerous direction) is held to a stricter bar than false
  positive rate, consistent with `ADR-010`'s "BLOCK/REVIEW always wins over silent APPROVE" safety
  philosophy — an extraction pipeline that leans toward under-confidence (more human confirmation)
  is preferable to one that leans toward over-confidence (more silent misses).

> Status: TBD / Current preferred option: set the initial numeric thresholds (per-field minimum
> confidence for auto-population vs. human confirmation, and the CI regression tolerance) directly
> from the golden dataset's first full run, rather than guessing a round number up front. / Why
> undecided: no golden dataset run exists yet, and picking a threshold before that would be an
> arbitrary number dressed up as a decision. / Resolution: run the golden dataset against the
> selected Tier-2 extraction model (`ai-strategy.md`'s model-selection TBD) and set the confidence
> threshold at the point that best separates correct from incorrect fields in that run, then
> re-validate after the first month of production spot-review data. / Decision artifact: a dated
> addendum to this document recording the chosen thresholds, cross-referenced from `BR-CON-003`.

## Relationship to other guardrails

Evaluation and guardrails are complementary, not the same thing: `evaluation.md` (this document)
answers "is the system accurate enough, measured offline and via sampling," while `guardrails.md`
answers "what stops a bad output from causing harm in a single, specific request, right now." A
configuration can pass every evaluation gate here and still need the guardrails in `guardrails.md` —
schema validation, confidence-threshold gating, prompt injection defense — because those protect
against per-request failures no aggregate metric fully captures.
