# Business Rules

Traceable identifiers connect Domain → Requirement (`docs/01-product/functional-requirements.md`)
→ future Plane Issue → Code → Test. Rules here describe *behavioral invariants*, distinct from the
functional requirements (*capabilities*) in `functional-requirements.md`.

## Organization & Identity

- **BR-ORG-001**: A `User` may hold `Membership` in more than one `Organization`; every permission
  check is scoped to exactly one active `Membership`.
- **BR-ORG-002**: An `Organization`'s `tax_id` must be unique within its jurisdiction pack.
- **BR-ORG-003**: Plan limits (suppliers analyzed, contracts reviewed, AI executions per period) are
  enforced at the point of creation, not retroactively — exceeding a limit blocks new creation but
  never deletes existing data (mirrors the existing `LimiteUsuariosAtingidoError` → 402 pattern in
  the reused `Accounts` code).

## Suppliers

- **BR-SUP-001**: A `Supplier` belongs to exactly one `Organization`.
- **BR-SUP-002**: `tax_id` + `organization_id` must be unique — the same supplier cannot be
  registered twice within one organization.
- **BR-SUP-003**: A `Supplier` cannot move to `approved` status without at least one `completed`
  `SupplierCheck` newer than any open sanctions flag.
- **BR-SUP-004**: A positive sanctions-list hit on any `SupplierCheck` forces the `Supplier`
  toward the `BLOCK` path via rule `SANC-001` (`docs/03-domain/policy-engine.md`) — it cannot be
  silently ignored by the workflow; it requires an explicit exception record if overridden.

## Contracts & Documents

- **BR-CON-001**: A `Contract` belongs to exactly one `Supplier`.
- **BR-CON-002**: Every negotiation round creates a new `ContractVersion`; existing versions are
  never edited in place.
- **BR-CON-003**: A `ContractVersion` cannot be marked `analyzed` until AI extraction has produced a
  structured result meeting the minimum confidence threshold (`TBD` — see
  `docs/05-ai/evaluation.md`) or a human has manually confirmed low-confidence fields.
- **BR-CON-004**: Every `Clause` must carry a page/span citation back to its source `Document` —
  a clause without provenance cannot be used as evidence in a `RuleEvaluation`.

## Policy & Compliance

- **BR-POL-001**: Policies (and their rules) are versioned; a rule is never edited after its
  `PolicyVersion` is published.
- **BR-POL-002**: Only one `PolicyVersion` per `Policy` is active/current at a time.
- **BR-CMP-001**: A `ComplianceReview` always evaluates the applicable `PolicyVersion` against
  normalized evidence — never against raw, unnormalized AI output (`docs/03-domain/policy-engine.md`
  evaluation-context section).
- **BR-CMP-002**: Aggregation is order-independent: `any BLOCK → BLOCK`, else `any REVIEW → REVIEW`,
  else `APPROVE` (`ADR-010`).
- **BR-CMP-003**: A `RuleEvaluation` is append-only; it is never edited or deleted, including by a
  later override.

## Approvals

- **BR-APR-001**: An `ApprovalRequest` can only be resolved (`approved`/`rejected`) by a user whose
  `Membership` role matches the request's `approver_role`.
- **BR-APR-002**: Rejecting any required `ApprovalRequest` in a workflow blocks the overall
  `Decision` from reaching `APPROVE` without an explicit override.
- **BR-APR-003**: An `ApprovalRequest` that exceeds its configured SLA moves to `expired` and emits
  an escalation event (exact SLA duration is a `TBD`, pending customer discovery — see
  `docs/02-business/pricing-strategy.md` for related plan-limit context).

## Decisions

- **BR-DEC-001**: Every final `Decision` preserves the exact `PolicyVersion` used to generate it.
- **BR-DEC-002**: A `Decision` is never edited in place; re-evaluation always creates a new
  `Decision` with `supersedes_decision_id` set. Each `Decision` carries `lifecycle`: `ACTIVE` for
  the single effective Decision of its ContractVersion, `SUPERSEDED` once a newer one replaces it.
  Only `lifecycle` changes on the old row, and at most one `ACTIVE` row exists per ContractVersion
  (enforced by the database). An automatic re-evaluation never silently supersedes an overridden
  `ACTIVE` Decision; a human replaces it with a manual review.
- **BR-DEC-003**: An override requires a mandatory, non-empty justification string and is itself
  audited (`decision.overridden` event) — it can never be silent. Only an `ACTIVE` Decision can be
  overridden; a `SUPERSEDED` one is refused (409).
- **BR-DEC-004**: A `Decision`'s `valid_until` expiring, or a new `PolicyVersion`/`ContractVersion`
  affecting rules it used, triggers `compliance.review_required` — the system never lets a stale
  decision look current without flagging it.

## Evidence & Audit

- **BR-EVD-001**: An `EvidencePackage`'s `merkle_root` must be deterministically recomputable from
  its `Evidence` set at any time (verifiability requirement, `docs/06-blockchain/verification.md`).
- **BR-EVD-002**: No raw contract text, personal data, or confidential document content is ever
  included in a `BlockchainAnchor` payload — only hashes/commitments
  (`docs/06-blockchain/privacy.md`).
- **BR-EVD-003**: Every `AuditEvent` is append-only; the audit log has no update or delete
  operation exposed anywhere in the system, including to Admin roles.
