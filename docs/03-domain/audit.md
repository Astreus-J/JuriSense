# Audit — Event Catalog

This document is the authoritative catalog of every domain event emitted by JuriSense Gate, and the
specification of the `AuditEvent` append-only log that records them all. See
`docs/03-domain/domain-model.md` for the entities that emit these events, `docs/03-domain/
business-rules.md` (`BR-EVD-003`) for the append-only invariant, and `docs/01-product/
functional-requirements.md` (`AUD-001`, `AUD-002`) for the corresponding capability requirements.

## AuditEvent: storage and append-only guarantee

Every event in this catalog is persisted as one `AuditEvent` record (`Evidence & Audit` context):
`id` (UUID, monotonically ordered), `event_type`, `actor_id` (nullable for system-initiated events,
e.g. a scheduled re-check), `payload` (JSON, event-specific — see each entry below),
`organization_id` (nullable only for genuinely system-level events with no tenant, e.g. a platform
health event outside this catalog's scope), and `occurred_at`.

Per `BR-EVD-003`: *"Every `AuditEvent` is append-only; the audit log has no update or delete
operation exposed anywhere in the system, including to Admin roles."* This is not a UI-layer
restriction — `AUD-002` requires that no update/delete operation exists at all, at any layer,
for any actor. Practically, this means:

- Correcting a mistake never means editing or removing a past `AuditEvent`. It means recording a
  **new** event that describes the correction (e.g. `decision.overridden` never erases the
  `decision.created` event it responds to; it references it).
- Every other domain entity's "immutable once created/completed/published" invariant
  (`SupplierCheck`, `RuleEvaluation`, `Decision`, `PolicyVersion`, `Clause`, `Evidence`, and more —
  see `domain-model.md`) is *reinforced* by the audit log: even if a bug or a future feature ever
  allowed a domain table row to change, the `AuditEvent` trail for that entity's id remains the
  ground truth of what actually happened and when, independent of current row state.
- This is what makes the **Decision Passport reconstruction use case** possible at all — see the
  dedicated section below.

## How audit events support Decision Passport reconstruction

Per `docs/00-project/overview.md`, a Decision Passport must answer "why was this approved?" months
or years later (`docs/03-domain/evidence.md` is the full specification of the Passport/
`EvidencePackage` itself). Reconstruction works by replaying the relevant slice of the `AuditEvent`
log for a given `decision_id`, joined against the immutable entities each event references:

```
decision.created (this decision)
   ├── references compliance_review_id
   │      ├── compliance.review_started / compliance.review_completed
   │      └── compliance.rule_evaluated  (one per Rule × PolicyVersion at review time)
   │             └── references rule_id within policy_version_id  → policy.version_published
   ├── references contract_version_id
   │      └── contract.version_created → contract.analysis_completed
   │             └── references document_id → document.uploaded / document.processed
   ├── references supplier_id
   │      └── supplier.check.completed (the check current as of the review)
   │             └── supplier.profile_updated
   ├── references any approval.requested / approval.approved / approval.rejected
   │      for this compliance_review_id
   └── (if applicable) decision.overridden
          └── evidence.package_created → evidence.anchored
```

Because every node in this chain is either an immutable entity or an append-only event referencing
one, the whole chain can be walked **without needing any live external system** — no call to the
CNPJ registry, no re-running AI extraction, no re-querying a sanctions list. The `SupplierCheck`'s
`raw_results` and the `ContractVersion`'s `extracted_data` are themselves the frozen record of what
those external systems said at the time; the audit trail is what proves the sequence and timing
of how those frozen facts were used. This is precisely the property `BR-EVD-001` requires of the
`EvidencePackage`'s Merkle root: deterministic recomputability at any time, from data already at
rest (`docs/03-domain/evidence.md` for the full mechanics).

## Event catalog

Events are grouped by producing bounded context, in the order they appear in the mission brief.
For each: **Producer**, **Meaning**, **Payload** (key fields), **Consumers**, **Audit
implications**.

### Identity & Organizations

**`organization.created`**
- Producer: `Organization` aggregate, on tenant creation (`ORG-001`).
- Meaning: a new tenant now exists in the system.
- Payload: `organization_id`, `name`, `tax_id`, `plan`, `created_by`.
- Consumers: billing/plan-limit enforcement (`BR-ORG-003`), onboarding email flow, analytics.
- Audit implications: the root anchor for every tenant-scoped event that follows; establishes the
  `organization_id` boundary that `SEC-001` requires on every subsequent tenant-owned record.

**`membership.invited`**
- Producer: `Membership` aggregate, on `ORG-002` invite action.
- Meaning: an admin invited a user (existing or new) into the organization with a given role.
- Payload: `membership_id`, `organization_id`, `invited_email`, `role`, `invited_by`.
- Consumers: invite email delivery, plan-limit check (`BR-ORG-003`).
- Audit implications: proves who granted access and what role was intended, independent of whether
  the invite is ever accepted — relevant if an invited-but-unaccepted role is later disputed.

**`membership.accepted`**
- Producer: `Membership` aggregate, on invite acceptance.
- Meaning: the invited user activated their membership (`invited → active`).
- Payload: `membership_id`, `organization_id`, `user_id`, `role`, `accepted_at`.
- Consumers: permission cache warm-up, seat-count enforcement (`BR-ORG-003`).
- Audit implications: establishes the exact moment a user's permissions in this organization became
  live — relevant when reconstructing "who could have approved X on date Y" for a given
  `ApprovalRequest`.

**`membership.revoked`**
- Producer: `Membership` aggregate, on admin revocation.
- Meaning: a user's access to the organization was terminated.
- Payload: `membership_id`, `organization_id`, `user_id`, `revoked_by`, `revoked_at`.
- Consumers: session invalidation, permission cache invalidation.
- Audit implications: proves exactly when access ended — critical for showing that an action
  attributed to a user occurred while their membership was still active, or flagging one that
  should not have been possible after revocation.

**`user.registered`**
- Producer: `User` aggregate, on account creation.
- Meaning: a new authenticated individual now exists in the system (may later hold memberships in
  multiple organizations, `BR-ORG-001`).
- Payload: `user_id`, `email`, `registered_at`.
- Consumers: welcome/verification email flow.
- Audit implications: establishes the identity root that every `actor_id` elsewhere in the catalog
  ultimately resolves to.

**`user.login_succeeded`**
- Producer: `User` aggregate / auth service, on successful authentication.
- Meaning: a user successfully authenticated (credentials + 2FA where enabled).
- Payload: `user_id`, `ip_address`, `user_agent`, `occurred_at`.
- Consumers: session issuance, anomaly/security monitoring (`SEC-002`).
- Audit implications: forms the access-pattern baseline needed to detect and later prove/disprove
  unauthorized access claims against a specific decision or approval.

**`user.login_failed`**
- Producer: `User` aggregate / auth service, on failed authentication attempt.
- Meaning: an authentication attempt failed (wrong credentials, failed 2FA, locked account).
- Payload: `user_id_attempted` (nullable if the email doesn't resolve to a user), `ip_address`,
  `reason`, `occurred_at`.
- Consumers: brute-force/lockout logic, security monitoring (`SEC-002`).
- Audit implications: security-relevant on its own (attack-pattern detection); also matters for
  disputes about whether an actor's account was compromised around the time of a questioned action.

**`user.password_reset`**
- Producer: `User` aggregate, on completed password reset.
- Meaning: a user's password was changed via the reset flow.
- Payload: `user_id`, `initiated_via` (self-service/admin-forced), `occurred_at`.
- Consumers: session invalidation for all other active sessions, security notification email.
- Audit implications: credential-change events are a standard forensic anchor point when
  investigating whether an account was compromised before or after a disputed action.

### Suppliers

**`supplier.created`**
- Producer: `Supplier` aggregate, on registration (`SUP-001`).
- Meaning: a new third party has been registered for evaluation.
- Payload: `supplier_id`, `organization_id`, `legal_name`, `tax_id`, `jurisdiction`, `created_by`.
- Consumers: triggers the initial `SupplierCheck` (`SUP-002`), plan-limit enforcement.
- Audit implications: the anchor point for the supplier's entire subsequent check/decision history
  — every later `SupplierCheck` and `Decision` referencing this supplier traces back here.

**`supplier.updated`**
- Producer: `Supplier` aggregate, on manual edit of core attributes (`legal_name`, `jurisdiction`,
  etc. — not the profile, see `supplier.profile_updated` below).
- Meaning: a user manually corrected/updated supplier record data.
- Payload: `supplier_id`, `changed_fields`, `updated_by`.
- Consumers: none beyond the audit trail itself.
- Audit implications: distinguishes human-entered corrections from system-derived profile updates —
  necessary to answer "was this field ever manually overridden, and by whom?"

**`supplier.status_changed`**
- Producer: `Supplier` aggregate, on lifecycle transition
  (`prospect → under_review → approved|blocked → inactive`).
- Meaning: the supplier's overall status changed.
- Payload: `supplier_id`, `from_status`, `to_status`, `reason` (e.g. "sanctions hit", "manual
  reactivation"), `changed_by` (nullable if system-driven, e.g. an automatic block on `SANC-001`).
- Consumers: downstream contract-creation eligibility checks, notification to relevant teams.
- Audit implications: proves exactly when a supplier became `approved` (relevant to `BR-SUP-003`'s
  "no open sanctions flag newer than the last completed check" invariant) or `blocked`, and why.

**`supplier.profile_updated`**
- Producer: `SupplierProfile` aggregate, on materialization from a completed `SupplierCheck`.
- Meaning: the supplier's normalized current-state snapshot was replaced with a fresh one.
- Payload: `supplier_id`, `supplier_profile_id`, `supplier_check_id` (the check that produced it),
  `changed_fields` (diff summary vs. prior profile), `occurred_at`.
- Consumers: `Policy & Compliance` evaluation-context builder (picks up new `supplier.*` fields);
  triggers `compliance.review_required` if the change is material to an existing `Decision`
  (`BR-DEC-004`).
- Audit implications: because `SupplierProfile` is replaced, not versioned, in the domain model,
  this event (paired with the `supplier_check_id`) is the only durable record of what the profile
  looked like before vs. after — essential for reconstructing "what did we believe about this
  supplier on the day of approval?"

**`supplier.check.started`**
- Producer: `SupplierCheck` aggregate, on check initiation (`SUP-002`).
- Meaning: a verification run against external sources has begun.
- Payload: `supplier_check_id`, `supplier_id`, `sources_consulted` (planned), `trigger`
  (creation/manual/periodic/contract-linked — `docs/03-domain/supplier-compliance.md`),
  `started_at`.
- Consumers: async worker (Celery, `ADR-006`) picking up the check job.
- Audit implications: establishes the exact window a check ran in, and — combined with
  `supplier.check.completed` — the check's duration, useful for diagnosing source outages later.

**`supplier.check.completed`**
- Producer: `SupplierCheck` aggregate, on check completion (success or failure — `status` in the
  payload distinguishes them).
- Meaning: the verification run finished and its results (or failure) are now immutable.
- Payload: `supplier_check_id`, `supplier_id`, `status` (`completed`/`failed`), `sources_consulted`
  (actual), `sanctions_hit` (bool, if `completed`), `completed_at`.
- Consumers: `SupplierProfile` materialization (`supplier.profile_updated`), `SANC-001` evaluation
  path for any pending `ComplianceReview`.
- Audit implications: this is the single most safety-critical event in the whole catalog per
  `BR-SUP-004` — it is the point at which a sanctions hit becomes visible to the system, and
  `BR-EVD-003`'s append-only guarantee ensures it can never be quietly removed or altered after the
  fact.

### Contracts & Documents

**`document.uploaded`**
- Producer: `Document` aggregate, on file upload (`CON-001`).
- Meaning: a new file has entered the system.
- Payload: `document_id`, `organization_id`, `content_hash` (SHA-256), `mime_type`, `uploaded_by`,
  `uploaded_at`.
- Consumers: malware/type-spoofing scan (`SEC-003`), object storage write (`ADR-008`).
- Audit implications: `content_hash` recorded here, at upload time, is what the `EvidencePackage`
  later cites as proof of exactly which bytes were reviewed (`docs/03-domain/evidence.md`) — it is
  never recomputed, so this event is the sole authoritative record of the original hash.

**`document.processed`**
- Producer: `Document` aggregate, on completed malware/type-spoofing scan.
- Meaning: the file has cleared security scanning and is safe to use for extraction.
- Payload: `document_id`, `scan_result`, `processed_at`.
- Consumers: `ContractVersion` extraction pipeline (only proceeds after this event).
- Audit implications: proves the document was scanned before any content was trusted or extracted —
  relevant to `SEC-003` compliance evidence.

**`contract.created`**
- Producer: `Contract` aggregate, on first version of a new logical agreement.
- Meaning: a new contractual relationship with a supplier now exists.
- Payload: `contract_id`, `organization_id`, `supplier_id`, `title`, `contract_type`, `created_by`.
- Consumers: `Contract` lifecycle tracking, dashboards.
- Audit implications: the anchor for the contract's entire version and review history.

**`contract.version_created`**
- Producer: `ContractVersion` aggregate, on every negotiation round (`CON-002`, `BR-CON-002`).
- Meaning: a new immutable snapshot of the contract's terms now exists.
- Payload: `contract_version_id`, `contract_id`, `document_id`, `version_number`, `created_by`.
- Consumers: AI extraction pipeline (`AI-001`).
- Audit implications: because versions are never edited in place, this event sequence is itself the
  full negotiation history — reconstructable purely from the audit log plus the immutable
  `ContractVersion` records it references.

**`contract.analysis_completed`**
- Producer: `ContractVersion` aggregate, on reaching `analyzed` (`BR-CON-003` gate satisfied).
- Meaning: structured extraction (and any required human confirmation) is complete and this version
  is ready for compliance evaluation.
- Payload: `contract_version_id`, `extraction_confidence` (summary), `human_confirmed_fields`
  (list, possibly empty), `completed_at`.
- Consumers: `Policy & Compliance` (may now build an evaluation context and start a
  `ComplianceReview`).
- Audit implications: records whether any field required human confirmation — a `Decision` that
  relied on human-confirmed (vs. purely AI-extracted) data is a materially different evidentiary
  claim, and this event is where that distinction is captured.

### Policy & Compliance

**`policy.created`**
- Producer: `Policy` aggregate, on authoring a new named rule collection (`POL-001`).
- Meaning: an organization started defining a new policy.
- Payload: `policy_id`, `organization_id`, `name`, `created_by`.
- Consumers: policy authoring UI, draft-state rule editor.
- Audit implications: establishes who introduced a given policy area, relevant when a customer asks
  "who decided we needed a rule about X?"

**`policy.version_published`**
- Producer: `PolicyVersion` aggregate, on publish (`POL-002`, `BR-POL-001`, `BR-POL-002`).
- Meaning: a new immutable, evaluable rule set became the current version for its `Policy`.
- Payload: `policy_version_id`, `policy_id`, `version_number`, `rule_ids`, `published_by`,
  `published_at`.
- Consumers: `Policy & Compliance` evaluation engine (uses this as "current" for new reviews);
  simulation/dry-run feature (`POL-003`) for comparison against the prior version.
- Audit implications: this is what makes `BR-DEC-001` ("every final `Decision` preserves the exact
  `PolicyVersion` used") checkable — the published rule set's exact content and timing is fixed by
  this event, permanently.

**`compliance.review_started`**
- Producer: `ComplianceReview` aggregate, on initiation (`CMP-001`).
- Meaning: an evaluation run of a `ContractVersion` + supplier evidence against a `PolicyVersion`
  has begun.
- Payload: `compliance_review_id`, `contract_version_id`, `policy_version_id`, `supplier_id`,
  `started_at`.
- Consumers: rule evaluation worker.
- Audit implications: fixes the exact `policy_version_id` and evidence inputs at the moment
  evaluation began, before any individual rule outcome is known — this timestamp anchors the whole
  review in the reconstruction chain described above.

**`compliance.rule_evaluated`**
- Producer: `RuleEvaluation` aggregate, one per applicable `Rule` evaluated within a
  `ComplianceReview` (`CMP-001`, `CMP-003`).
- Meaning: one specific rule was evaluated against the normalized context and produced an outcome.
- Payload: `rule_evaluation_id`, `compliance_review_id`, `rule_id`, `outcome`
  (`PASS|REVIEW|BLOCK|NOT_APPLICABLE`), `severity`, `evidence_refs`, `rationale`.
- Consumers: aggregation step (`ADR-010`) reads the full set of these to compute the review's final
  status.
- Audit implications: `BR-CMP-003` makes this the single most granular, load-bearing audit record in
  the compliance domain — append-only by construction, and the direct evidentiary basis for "why
  did rule X fire," cited by `evidence_refs` back to the exact `Clause`/`SupplierCheck` that
  triggered it.

**`compliance.review_completed`**
- Producer: `ComplianceReview` aggregate, once every applicable rule has been evaluated and
  aggregation has run.
- Meaning: the review is finished and immutable; a final status (`APPROVE|REVIEW|BLOCK`) is known.
- Payload: `compliance_review_id`, `final_status`, `required_approver_role` (if `REVIEW`),
  `completed_at`.
- Consumers: `Approvals & Decisions` (instantiates `ApprovalRequest`s if `REVIEW`, or a `Decision`
  directly if `APPROVE`/`BLOCK`).
- Audit implications: the direct trigger for everything in `docs/03-domain/approvals.md`; also the
  event that a `Decision`'s eventual `EvidencePackage` cites as "which review produced this
  decision."

**`compliance.review_required`**
- Producer: `Decision`/`ComplianceReview` aggregate, on `valid_until` expiration or a materially
  affecting `PolicyVersion`/`ContractVersion`/`SupplierProfile` change (`BR-DEC-004`).
- Meaning: an existing `Decision` can no longer be trusted as current and must be re-evaluated.
- Payload: `decision_id` (the one being flagged), `reason`
  (`expired`/`policy_changed`/`contract_changed`/`supplier_changed`), `flagged_at`.
- Consumers: scheduling/notification for a fresh `ComplianceReview`.
- Audit implications: proves the system never let a stale decision look current without flagging it
  — directly evidences `BR-DEC-004` compliance to an auditor.

### Approvals & Decisions

**`approval_workflow.updated`**
- Producer: `ApprovalWorkflow` aggregate, on admin edit of routing configuration.
- Meaning: an organization's approval routing template changed.
- Payload: `approval_workflow_id`, `organization_id`, `changed_fields`, `updated_by`.
- Consumers: future `ComplianceReview`s reaching `REVIEW` (uses the current configuration at
  instantiation time).
- Audit implications: because `ApprovalWorkflow` is not versioned, this event is the only durable
  record of what the routing rules were at a given point in time — relevant if a customer disputes
  why a given review was routed to a particular role.

**`approval.requested`**
- Producer: `ApprovalRequest` aggregate, on instantiation from a `REVIEW` `ComplianceReview`
  (`APR-001`).
- Meaning: a specific human approval step is now pending.
- Payload: `approval_request_id`, `compliance_review_id`, `approver_role`, `step_number`,
  `requested_at`.
- Consumers: notification to users holding `approver_role`; SLA clock start (`BR-APR-003`).
- Audit implications: the anchor for the request's resolution (or expiration) history described in
  `docs/03-domain/approvals.md`.

**`approval.approved`**
- Producer: `ApprovalRequest` aggregate, on approval by a correctly-roled actor (`APR-002`,
  `BR-APR-001`).
- Meaning: this approval step is resolved favorably.
- Payload: `approval_request_id`, `approved_by`, `justification` (optional), `approved_at`.
- Consumers: next step instantiation (multi-step chains) or `Decision` creation (final step).
- Audit implications: records exactly who exercised the approval authority for this step —
  the human-accountability record the whole workflow exists to produce.

**`approval.rejected`**
- Producer: `ApprovalRequest` aggregate, on rejection (`BR-APR-002`).
- Meaning: this approval step is resolved unfavorably, halting the chain.
- Payload: `approval_request_id`, `rejected_by`, `justification`, `rejected_at`.
- Consumers: `Decision` creation (blocked from `APPROVE`, per `BR-APR-002`); no further steps in
  the chain are instantiated.
- Audit implications: distinct from `expired` — proves a human actively reviewed and declined,
  which matters legally/commercially differently than "nobody got to it in time."

**`decision.created`**
- Producer: `Decision` aggregate, once a `ComplianceReview` (and any required approval chain)
  reaches a terminal outcome (`DEC-001`).
- Meaning: the final, packaged compliance outcome for a `ComplianceReview` now exists.
- Payload: `decision_id`, `compliance_review_id`, `status` (`APPROVE|REVIEW|BLOCK`), `valid_until`,
  `supersedes_decision_id` (nullable), `created_at`.
- Consumers: `Evidence & Audit` (triggers `EvidencePackage` assembly, `EVD-001`); notification to
  requesting user; webhook (`INT-002`, `decision.completed`).
- Audit implications: the terminal record every downstream evidence and verification artifact is
  built from — `BR-DEC-001` (preserves exact `PolicyVersion`) and `BR-DEC-002` (never edited in
  place) both center on this event.

**`decision.overridden`**
- Producer: `Decision` aggregate, on manual override by an authorized approver (`DEC-002`,
  `BR-DEC-003`, `ADR-010` §3).
- Meaning: a human deliberately changed the computed outcome, with mandatory justification.
- Payload: `decision_id`, `original_outcome`, `new_outcome`, `justification` (mandatory,
  non-empty), `overridden_by`, `overridden_at`.
- Consumers: `Evidence & Audit` (the override becomes part of the `EvidencePackage`); compliance
  reporting/dashboards flagging override rates.
- Audit implications: `BR-DEC-003` makes this event the load-bearing safeguard against silent
  manual tampering — an override can never happen without this event firing, and the original
  `RuleEvaluation`/`Decision` records remain untouched alongside it, so both "what the system
  concluded" and "what a human decided instead, and why" are permanently visible together.

### Evidence & Audit

**`evidence.package_created`**
- Producer: `EvidencePackage` aggregate, on assembly following `decision.created` (`EVD-001`).
- Meaning: the complete, hashable evidence bundle for a `Decision` has been built.
- Payload: `evidence_package_id`, `decision_id`, `evidence_count`, `merkle_root`, `created_at`.
- Consumers: `BlockchainAnchor` submission pipeline (`EVD-003`).
- Audit implications: `merkle_root` recorded here is what `BR-EVD-001` requires to be
  deterministically recomputable later — full mechanics in `docs/03-domain/evidence.md`.

**`evidence.anchored`**
- Producer: `BlockchainAnchor` aggregate, on confirmed on-chain submission via the configured
  `AnchoringProvider` (`ADR-007`, `EVD-003`).
- Meaning: the `EvidencePackage`'s Merkle root is now anchored on a public, tamper-evident ledger.
- Payload: `blockchain_anchor_id`, `evidence_package_id`, `provider`, `anchor_ref`, `submitted_at`,
  `confirmed_at`.
- Consumers: public verification page (`docs/06-blockchain/verification.md`); customer-facing
  Decision Passport UI.
- Audit implications: the final, externally-checkable link in the chain — an auditor or counterparty
  can, independent of JuriSense Gate's own database, confirm the anchored hash matches a
  recomputed `merkle_root` from the (internally retained) `Evidence` set.

### Integrations

**`integration.connected`**
- Producer: `Integration` aggregate, on admin configuration of an external system connection
  (`INT-001`).
- Meaning: an external system (e.g. DocuSign, Slack) is now connected on behalf of the organization.
- Payload: `integration_id`, `organization_id`, `provider`, `connected_by`, `connected_at`.
- Consumers: the integration's own sync/webhook workers.
- Audit implications: establishes when third-party access to organization data/events began —
  relevant to LGPD data-sharing accountability.

**`integration.disconnected`**
- Producer: `Integration` aggregate, on admin disconnection or credential revocation.
- Meaning: the external system connection has been terminated.
- Payload: `integration_id`, `organization_id`, `disconnected_by`, `reason`, `disconnected_at`.
- Consumers: sync/webhook worker teardown.
- Audit implications: establishes the end of a third party's access window — pairs with
  `integration.connected` to bound exactly when external data sharing was active.

## Relationship to other domain documents

- `AUD-001`/`AUD-002` (`docs/01-product/functional-requirements.md`) and `BR-EVD-003`
  (`docs/03-domain/business-rules.md`) are the authoritative capability/invariant statements this
  catalog implements.
- `docs/03-domain/supplier-compliance.md`, `docs/03-domain/contract-compliance.md`, and
  `docs/03-domain/approvals.md` are the behavioral specs that produce the events catalogued here in
  context.
- `docs/03-domain/evidence.md` specifies how a subset of these events and the entities they
  reference are assembled into the `EvidencePackage`/Decision Passport.
