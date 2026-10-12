# Approvals

This document specifies the full behavioral workflow of human approval in the **Approvals &
Decisions** bounded context: `ApprovalWorkflow` configuration, the `ApprovalRequest` state machine,
SLA/escalation behavior, multi-step approval chains, rejection handling, and how this workflow
relates to the Decision Engine's aggregation output. See `docs/03-domain/domain-model.md` for entity
definitions (`ApprovalWorkflow`, `ApprovalRequest`, `Decision`), `docs/03-domain/business-rules.md`
for invariants (`BR-APR-*`), `ADR-006` for the async/state-machine implementation decision, and
`ADR-010` for the aggregation algorithm that produces the `REVIEW` outcome this workflow reacts to.

## Purpose

Not every compliance outcome can or should be fully automatic. When the Policy Engine's aggregation
(`ADR-010`) reaches `REVIEW`, a human with the right authority must look at the evidence and decide.
Approvals & Decisions is the bounded context that turns that need into a concrete, trackable,
auditable task, routed to the correct role, with an explicit outcome recorded — never an email
thread or a verbal "looks fine to me" (`docs/00-project/overview.md`, "Workflow / Approvals").

## Relationship to the Decision Engine: what creates an ApprovalRequest

An `ApprovalRequest` is only ever instantiated as a **reaction** to a `ComplianceReview` reaching
`REVIEW`. It does not exist independently of the aggregation algorithm:

1. `Policy & Compliance` evaluates every applicable `Rule` in the current `PolicyVersion`, producing
   one `RuleEvaluation` per rule (`outcome ∈ {PASS, REVIEW, BLOCK, NOT_APPLICABLE}`).
2. Aggregation (`ADR-010`, `BR-CMP-002`): any `BLOCK` → `BLOCK` (no approval step — see "BLOCK is
   not reviewable through this workflow" below); else any `REVIEW` → `REVIEW`, with the required
   approver being the **highest-severity** triggered `REVIEW` rule's `approver_role`
   (`docs/03-domain/policy-engine.md`, "Rule priority & conflicting rules"); else `APPROVE`
   (fully automatic, no human step at all).
3. Only on a `REVIEW` aggregate result does `Approvals & Decisions` instantiate one or more
   `ApprovalRequest`s from the organization's configured `ApprovalWorkflow`, and only then does
   `approval.requested` fire.
4. A `Decision` is not created until every required `ApprovalRequest` for that `ComplianceReview`
   reaches a terminal state (`approved` or `rejected`) — see "State machine" below.

**BLOCK is not reviewable through this workflow.** A `BLOCK` aggregate result (e.g. from `SANC-001`,
`docs/03-domain/supplier-compliance.md`) has `approver_role: null` by design
(`docs/03-domain/policy-engine.md`) — it is not routed to an `ApprovalRequest` because there is
nothing to "approve" at that severity. The only path past a `BLOCK` is a `Decision`-level manual
override with mandatory justification (`BR-DEC-003`, `ADR-010` §3), a distinct, higher-friction
mechanism from ordinary approval, and one that emits its own `decision.overridden` audit event
(`docs/03-domain/audit.md`).

## ApprovalWorkflow configuration

`ApprovalWorkflow` is the organization-configurable routing template (`ADR-006`): a
`trigger_condition` (what risk tier/rule severity this workflow applies to) and an ordered list of
`steps` (approver roles). Per `docs/00-project/overview.md` and `docs/03-domain/policy-engine.md`'s
severity model, the concrete default routing — adjustable per organization — is:

| Risk tier | Trigger (typical) | Routing |
|---|---|---|
| LOW | No `REVIEW`/`BLOCK` rule fired | Auto-approve — no `ApprovalWorkflow` instantiated at all |
| MEDIUM | Highest-severity triggered `REVIEW` rule is `medium` (e.g. `FIN-003`, high-value contract ≥ R$250,000) | Single step: **Legal** |
| HIGH | Highest-severity triggered `REVIEW` rule is `high`/`critical` (e.g. `FIN-004`, ≥ R$1,000,000; or `LEGAL-008`, unlimited liability) | Multi-step chain: **Compliance → Legal → Director** |

This table is a concrete default shipped with the product, not a hardcoded constant: `ADR-006`
models `ApprovalWorkflow` as organization-configurable data, so a customer can redefine
`trigger_condition`s and `steps` (e.g., a smaller organization might collapse HIGH to Legal +
Director only, skipping a dedicated Compliance role it doesn't staff). `domain-model.md`'s
invariant ("at least one step required") is the only hard constraint on a valid `ApprovalWorkflow`.

**"Director" is a persona-facing label, not a distinct RBAC role (product decision, 2026-10-12,
#181).** The technical `ApprovalWorkflow.steps` value this table's "Director" step seeds is the
real `app.identity.domain.constants.Role.APPROVER` value ("approver") -- `app.identity.domain.
rbac`'s own role grid already describes `approver` as "the generic Director/Approver persona."
There is no separate `director` role in the RBAC grid, and none is planned: a customer's actual
director is provisioned as an `approver`-role `User`, and "Director" is simply how this product
displays/names that step in the UI and in this table. Revisit only if a real customer's RBAC
needs genuinely diverge `approver` into distinct sub-personas -- not something this decision
anticipates.

`ApprovalWorkflow` itself is not versioned in v1 (`domain-model.md`: "not versioned in v1 (future
item if historical reproducibility of *workflow configuration* — not just decisions — becomes
required)"). Editing an active `ApprovalWorkflow` fires `approval_workflow.updated`
(`docs/03-domain/audit.md`) but does not retroactively change any in-flight or resolved
`ApprovalRequest` — an already-instantiated request keeps the `approver_role` it was created with.

## ApprovalRequest state machine

```
                 ┌────────────► approved ──────────┐
                 │                                  │
   pending ──────┤                                  ├──► (feeds Decision aggregation for this step)
                 │                                  │
                 ├────────────► rejected ───────────┘
                 │
                 └────────────► expired  (SLA exceeded, no resolution)
```

- **`pending`.** Created on `approval.requested`, scoped to one `approver_role` (from one step of
  the `ApprovalWorkflow`) and one `ComplianceReview`. Any user whose active `Membership.role`
  matches `approver_role` may resolve it.
- **`approved` / `rejected`.** Terminal. Per `BR-APR-001`, only a user with the matching role may
  resolve the request — enforced in the application layer, RBAC-gated per `ADR-003`/`ADR-012`.
  Resolving fires `approval.approved` or `approval.rejected` and requires the resolving actor's
  identity to be recorded (this becomes part of the `EvidencePackage`'s reviewer list,
  `docs/03-domain/evidence.md`).
- **`expired`.** Per `BR-APR-003`, an `ApprovalRequest` that exceeds its configured SLA
  automatically transitions to `expired` and emits an escalation event, rather than sitting
  `pending` indefinitely. `domain-model.md` lists `expired` as a first-class terminal status
  alongside `approved`/`rejected`.
- **Immutability.** Per `domain-model.md`, an `ApprovalRequest` is "immutable once resolved" — a
  resolved decision on a request is never edited; correcting a mistaken approval requires the
  `Decision`-level override mechanism, not editing the `ApprovalRequest`.

## SLA and escalation

Status: TBD / Current preferred option: a per-severity SLA clock (candidate default: 2 business
days for MEDIUM-tier / single-step requests, 1 business day per step for HIGH-tier chains, to keep
the overall chain from stretching indefinitely), with an escalation notification fired at a
configurable fraction of the SLA (e.g. 75%) before expiry, and automatic transition to `expired` at
100% / Why undecided: `BR-APR-003` explicitly marks the exact SLA duration TBD pending customer
discovery, since the right cadence depends on how the target customer segment
(`docs/02-business/brazil-market.md`, 50–1,000-employee tech companies) actually staffs Legal/
Compliance/Director review capacity, and on plan-tier expectations
(`docs/02-business/pricing-strategy.md`) / Resolution: finalize per-tier SLA defaults (and whether
they are admin-configurable per organization, which is the current lean) during early customer
discovery ahead of general availability; the hackathon build may ship a single flat default (e.g. 2
business days) rather than the full per-tier table above / Decision artifact: an ADR to be written
once customer discovery concludes.

Whatever the exact duration, the behavioral contract is fixed regardless of the number chosen: an
`expired` `ApprovalRequest` is **not** silently treated as approved or rejected — it is a distinct
terminal state that blocks the `ComplianceReview` from reaching a `Decision` until either the
request is manually re-opened/re-routed by an admin, or an authorized override is issued
(`BR-DEC-003`). An SLA breach is itself audit-relevant (`docs/03-domain/audit.md`) precisely because
"the approver never got to it in time" is a distinct failure mode from "the approver rejected it,"
and a Decision Passport must be able to show which one happened.

## Multi-step chains

A HIGH-tier `ApprovalWorkflow` names an **ordered** list of steps (e.g. Compliance → Legal →
Director, per `APR-003`). Steps execute sequentially, not in parallel: the next step's
`ApprovalRequest` is only instantiated once the current step resolves `approved`. This ordering
exists so that an earlier, more specialized reviewer (e.g. Compliance, checking regulatory/sanctions
context) can catch a problem before it consumes a scarcer, more senior reviewer's time (e.g.
Director) — but it also means a **rejection at any step halts the chain immediately**: later steps
are never instantiated once an earlier one rejects (see "On rejection" below).

Each step's `ApprovalRequest` is independently subject to the SLA/escalation behavior above; a
multi-step chain's total resolution time is therefore the sum of however many steps actually run
before either full approval or a rejection.

## On rejection

Per `BR-APR-002`: *"Rejecting any required `ApprovalRequest` in a workflow blocks the overall
`Decision` from reaching `APPROVE` without an explicit override."* Concretely:

1. The rejecting `ApprovalRequest` moves to `rejected` and fires `approval.rejected`, carrying the
   resolving actor's identity and (recommended, though not modeled as a separate required field
   beyond the request's own `justification` attribute) a rejection reason.
2. Any remaining un-instantiated steps in the chain are never created — the workflow halts, it does
   not continue past a rejection to collect "the rest of the opinions."
3. `Approvals & Decisions` produces a `Decision` with a status that reflects the rejection — in
   practice this is treated as equivalent in severity to a `BLOCK`-class outcome for the purpose of
   "cannot reach `APPROVE` automatically" — and it can only be moved past via the same manual
   override mechanism used for a policy-engine `BLOCK` (`BR-DEC-003`, mandatory justification,
   `decision.overridden` audit event). There is deliberately no separate "un-reject" action on the
   `ApprovalRequest` itself, because `ApprovalRequest` is immutable once resolved
   (`domain-model.md`) — the override happens at the `Decision` level, preserving the original
   rejection record intact.
4. The rejected `ComplianceReview`'s full `RuleEvaluation` set, the rejection itself, and (if it
   occurs) the subsequent override are all retained, unedited, as part of the eventual
   `EvidencePackage` (`docs/03-domain/evidence.md`) — a rejection is not a dead end that leaves no
   trace; it is a first-class part of the decision's audit history.

## Relationship to other domain documents

- `APR-001` through `APR-003`, `DEC-001` through `DEC-003`
  (`docs/01-product/functional-requirements.md`) are the capability requirements this workflow
  implements.
- `BR-APR-001` through `BR-APR-003` and `BR-DEC-001` through `BR-DEC-004` are the authoritative
  invariants; this document elaborates their behavior end to end.
- What produced the `REVIEW` outcome in the first place is specified in
  `docs/03-domain/policy-engine.md` and, for the supplier-side sanctions case specifically,
  `docs/03-domain/supplier-compliance.md`.
- Every event named above (`approval_workflow.updated`, `approval.requested`, `approval.approved`,
  `approval.rejected`, `decision.created`, `decision.overridden`) is catalogued in full — producer,
  payload, consumers, audit implications — in `docs/03-domain/audit.md`.
- How an `ApprovalRequest`'s resolution and any override become durable, hash-anchored evidence is
  specified in `docs/03-domain/evidence.md`.
