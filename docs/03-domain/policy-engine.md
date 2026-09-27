# Policy Engine

The Policy Engine is the core competitive component of JuriSense Gate: it lets an organization
express internal policy as executable, versioned rules, and evaluates them deterministically
against normalized supplier/contract evidence. See `ADR-004` (expression language) and `ADR-010`
(decision aggregation) for the decisions this document elaborates.

## Rule DSL

Rules are authored in YAML and compiled to CEL (primary) or JSONLogic (secondary, for future
no-code rule-builder output) — see `ADR-004`.

```yaml
rule:
  id: LGPD-001
  name: DPA Required for Personal Data Processing
when:
  processes_personal_data: true
  dpa_present: false
result:
  status: BLOCK
severity: critical
approver_role: null   # BLOCK has no approver — it is not overridable without an explicit override action
```

```yaml
rule:
  id: LEGAL-008
  name: Unlimited Liability Requires Legal Review
when:
  contract.liability.type: unlimited
result:
  status: REVIEW
severity: high
approver_role: legal
```

```yaml
rule:
  id: FIN-003
  name: High-Value Contract Requires Legal Approval
when:
  contract.value.brl: { gte: 250000 }
result:
  status: REVIEW
severity: medium
approver_role: legal
```

```yaml
rule:
  id: FIN-004
  name: Very High-Value Contract Requires Legal + Director Approval
when:
  contract.value.brl: { gte: 1000000 }
result:
  status: REVIEW
severity: high
approver_role: director
```

```yaml
rule:
  id: SANC-001
  name: Supplier on a Sanctions List
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null
```

## Policy lifecycle

`Policy` (container, mutable metadata: name/status) → `PolicyVersion` (immutable snapshot of a
`Rule` set, created on every publish) → `Rule` (immutable once its version is published). See
`docs/03-domain/domain-model.md` for the full entity definitions. Only one `PolicyVersion` per
`Policy` is "current" at a time; every `ComplianceReview` records exactly which `PolicyVersion` it
used, so historical decisions remain reproducible even after the policy changes (`ADR-010`).

## Rule lifecycle

A `Rule` is created/edited only inside a **draft** `PolicyVersion`. Publishing a `PolicyVersion`
freezes every `Rule` in it. Editing a published rule is not possible — it always produces a new
`PolicyVersion` (with a new set of `Rule`s, copy-modified from the previous version). This is what
makes "backward compatibility" tractable: nothing changes under decisions already made.

## Evaluation context & input normalization

Before any rule runs, `Policy & Compliance` builds a single **normalized evaluation context** from:
`Supplier` + current `SupplierProfile` + latest `SupplierCheck` (from `Suppliers`), and
`ContractVersion.extracted_data` + `Clause` list (from `Contracts & Documents`). This context is a
flat, typed object (e.g. `supplier.sanctions_hit`, `contract.liability.type`,
`contract.value.brl`, `contract.value.currency`, `contract.processes_personal_data`,
`contract.dpa_present`) — rules never touch raw AI output or raw documents directly. Normalization
is owned by `Policy & Compliance`'s application layer, not by `AI Services` (see the context
boundary rule: AI Services produces structured extraction, Policy & Compliance decides what of it
means for evaluation).

## Rule priority & conflicting rules

Rules do not have an execution "priority" that changes the outcome — the aggregation model
(`ADR-010`) is deliberately **order-independent**: every applicable rule in the current
`PolicyVersion` is evaluated, and the aggregation (`any BLOCK → BLOCK`, else `any REVIEW → REVIEW`,
else `APPROVE`) is a pure function of the *set* of outcomes, not the order they ran in. "Conflicting
rules" (e.g., one rule says REVIEW, another says BLOCK for the same condition) never need manual
tie-breaking — BLOCK always wins, by design, because it is the safer failure mode. If two REVIEW
rules trigger with different `approver_role`s, the required approver is the **highest-severity**
rule's role (ties broken by requiring all distinct roles named, i.e., escalate rather than
under-notify).

## Severity & escalation

Severity (`critical/high/medium/low`) drives two things: (1) which `approver_role` is required when
multiple REVIEW rules fire (highest severity wins, per above), and (2) prioritization in the human
reviewer's queue (`docs/01-product/use-cases.md`). Severity does **not** change the
APPROVE/REVIEW/BLOCK aggregation itself — a `low`-severity REVIEW rule still forces REVIEW, it just
sorts lower in a reviewer's worklist.

## Exceptions & manual overrides

An organization may grant a time-boxed **policy exception** for a specific supplier/contract
(e.g., "waive FIN-003 for this specific renewal") — modeled as a first-class, audited record (not a
silent rule edit), requiring the same `approver_role` the waived rule would have required, with
mandatory justification. Independently, a `Decision` itself can be manually **overridden** after
the fact (`ADR-010` §3) — both mechanisms are logged as distinct `AuditEvent`s and never remove the
original `RuleEvaluation` record.

## Simulation / dry-run

Before publishing a new `PolicyVersion`, an organization can run it in **simulation mode** against a
sample of existing `ContractVersion`s (already-evaluated or a hand-picked set) to see what would
change, without creating real `ComplianceReview`/`Decision` records. This is essential for trust —
a compliance team must be able to answer "if we tighten this rule, how many active contracts would
suddenly fail?" before publishing. Simulation runs are logged (for the policy author's benefit) but
do **not** emit domain events or affect real decisions.

## Auditability

Every `RuleEvaluation`, `ComplianceReview`, `Decision`, exception, and override is append-only and
timestamped (`docs/03-domain/audit.md`). Nothing in the Policy Engine ever silently changes a past
result — a policy change only affects future evaluations, and a re-evaluation is always a *new*
`ComplianceReview`/`Decision`, never an edit.

## Backward compatibility

Because rules are immutable once published (via `PolicyVersion`), backward compatibility is
structural: an old `Decision` always resolves against the exact `PolicyVersion` it recorded, even if
the `Policy` has since been republished many times over. `docs/09-planning/pivot-migration.md` and
future rule-schema changes (e.g., adding a new field to the `when` grammar) must remain
additive — existing rule YAML must keep compiling without edits when the DSL evolves; breaking
changes require a documented DSL version bump (`docs/07-engineering/api-standards.md` versioning
policy applies analogously here).

## Policy testing

Every `Policy` should ship with a set of **fixture cases** (a normalized evaluation context +
expected outcome) that run in CI whenever a new `PolicyVersion` is drafted, functioning like unit
tests for business rules — this is a Phase 4/5 backlog item (`docs/09-planning/backlog.md`), not
optional hardening.

## Compliance Decision aggregation (cross-reference)

The full BLOCK/REVIEW/APPROVE aggregation algorithm, override semantics, and re-evaluation/
expiration model are specified once, authoritatively, in `ADR-010` — this document does not repeat
it beyond the priority/conflict notes above, to avoid two documents drifting out of sync.
