# ADR-010 — Compliance Decision Aggregation Model

## Status
Accepted

## Context
The Compliance Engine must turn a set of independently-evaluated policy rules into one final
decision (`APPROVE` / `REVIEW` / `BLOCK`) in a way that is deterministic, explainable, auditable,
and safe (never silently down-grades a risk). This is the single most important behavioral
specification in the product — see `docs/03-domain/policy-engine.md` for the full worked examples.

## Decision
1. Every evaluated `Rule` produces a `RuleEvaluation` with `outcome ∈ {PASS, REVIEW, BLOCK,
   NOT_APPLICABLE}`, a `severity` (`critical|high|medium|low`), supporting evidence/rationale, and
   (for REVIEW/BLOCK) an `approver_role`.
2. Aggregation into the `ComplianceReview`'s final status:
   - **Any `BLOCK` → final status `BLOCK`.**
   - Else, **any `REVIEW` → final status `REVIEW`**, with the required approver being the highest
     severity among the triggered REVIEW rules' `approver_role`.
   - Else (all rules `PASS` or `NOT_APPLICABLE`) → final status **`APPROVE`** (fully automatic).
3. **Manual override**: an authorized approver (RBAC-gated, per `ADR-003`) may override the computed
   status, but must supply a mandatory written justification. The override **never mutates or
   deletes** the original `RuleEvaluation` records (append-only) — it is recorded as a
   `decision.overridden` audit event carrying `original_outcome`, `justification`, and
   `overridden_by`.
4. **Expiration & re-evaluation**: every `Decision` carries a `valid_until` (derived from policy
   configuration, default TBD pending commercial input — see `03-domain/policy-engine.md`). A new
   `ContractVersion` or a newly published `PolicyVersion` that affects previously-evaluated rules
   emits `compliance.review_required`. Historical decisions are **never edited in place**; a new
   `Decision` references the superseded one via `supersedes_decision_id`.

## Alternatives Considered
- **Weighted/scored risk model** (e.g., numeric risk score crossing thresholds): rejected as the
  primary mechanism — it obscures *why* a decision was reached, which conflicts directly with the
  product's core promise ("WHY, EVIDENCE, POLICY, SOURCE" per the mission's product principle).
  A severity-tagged rule may still contribute to a secondary informational risk score, but the
  APPROVE/REVIEW/BLOCK gate itself stays rule-outcome-based, not score-based.
- **First-matching-rule-wins**: rejected — would let a low-priority PASS rule mask a later BLOCK
  rule depending on evaluation order; the any-BLOCK/any-REVIEW aggregation is order-independent by
  design.

## Consequences
- The algorithm is simple enough to explain to a customer's Legal/Compliance team in one sentence,
  which matters for sales and for trust in an AI-adjacent product.
- Every `Decision` is fully reproducible from its recorded `RuleEvaluation` set and `PolicyVersion`
  — this is the backbone of the Decision Passport and of the blockchain evidence anchoring (`ADR-007`).
