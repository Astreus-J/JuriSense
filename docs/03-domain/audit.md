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

This catalog is checked against the code by `backend/tests/evidence/test_audit_catalog_coverage.py`:
every entry must be emitted by `app/` and named by a test under `tests/` (a quoted reference, not
proof of the assertion itself), or be marked "not yet emitted" and listed in that test's
`PLANNED_NOT_YET_EMITTED`. Payloads are not compared by that test, and neither is the placement of
the emission: that it shares its business transaction is covered only by the atomicity tests
(for example `test_password_reset_is_atomic_with_its_audit_event`).

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
- Payload: `user_id`. Carried the plaintext email until the security review (finding M3,
  2026-10-05); removed because it is reachable from `user_id` by anyone permitted to look it up,
  so the audit trail does not need its own copy.
- Consumers: welcome/verification email flow.
- Audit implications: establishes the identity root that every `actor_id` elsewhere in the catalog
  ultimately resolves to.

**`user.updated`**
- Producer: `User` aggregate, on an admin changing a user's `role` and/or `status` via
  `PATCH /users/{id}` (`app/identity/application/user_service.update_user`). Added after security
  review found role/status changes were the one Identity mutation left unaudited, unlike every
  sibling use case (registration, invitation, deactivation).
- Meaning: an admin changed another user's role and/or account status within the organization —
  the single most security-sensitive action this endpoint exposes (e.g. granting/revoking admin,
  demoting a user, reactivating a deactivated one).
- Payload: `user_id`, `updated_by`, and, only for the field(s) that actually changed,
  `role: {from, to}` and/or `status: {from, to}`.
- Consumers: security monitoring for unexpected privilege changes; the `ModulePermission` grid
  reseed (`reseed_permissions_for_role_change`) that runs in the same transaction.
- Audit implications: the Decision Passport / Evidence & Audit value proposition depends on being
  able to answer "who had elevated access, and since when?" for any past decision — this event is
  the only record of that changing over time.

**`user.login_succeeded`**
- Producer: `User` aggregate / auth service (`app.identity.application.auth_service.login`), on
  successful authentication. Emitted; 2FA is not built yet.
- Meaning: a user successfully authenticated with credentials.
- Payload: `user_id`, `occurred_at`. The client IP and user agent are not repeated here: they are
  written to the `AccessLog` row in the same transaction, which is their record. This payload
  carries ids and timestamps only, no personal data.
- Consumers: session issuance, anomaly/security monitoring (`SEC-002`).
- Audit implications: forms the access-pattern baseline needed to detect and later prove/disprove
  unauthorized access claims against a specific decision or approval.

**`user.login_failed`**
- Producer: `User` aggregate / auth service (`app.identity.application.auth_service.login`), on a
  refused login where the credentials were checked: a wrong password, an address that is not a
  user, or an inactive account presented with the correct password. Emitted; failed 2FA is not
  built yet. Locked-out attempts are refused before the credential check and are not recorded
  here, which matches `AccessLog` today.
- Meaning: an authentication attempt was refused.
- Payload: `user_id_attempted` (null if the address is not a user), `reason`
  (`invalid_credentials` | `user_inactive`), `occurred_at`. The attempted address is not stored,
  in plaintext or hashed: an unsalted hash of an address is still confirmable, so it is not a
  pseudonym. A failed attempt against an address that is not a user can therefore be counted but
  not correlated to the same address later.
- `actor_id` is null (the caller is unauthenticated). `organization_id` is the matched user's
  organization, or null when the address is not a user.
- The HTTP response is unchanged by this event: the caller still receives `401 Invalid credentials`
  for every refusal in this list.
- Consumers: brute-force/lockout logic, security monitoring (`SEC-002`).
- Audit implications: security-relevant on its own (attack-pattern detection); also matters for
  disputes about whether an actor's account was compromised around the time of a questioned action.
  Known gap: the endpoint has no rate limit yet (security review M1), so an unauthenticated caller
  can write one row per request. Until that is fixed, treat row volume here as attacker-controlled.

**`user.password_reset`**
- Producer: `User` aggregate (`app.identity.application.password_service.reset_password`), on
  completed password reset. Emitted in the same transaction as the password change.
- Meaning: a user's password was changed via the reset flow.
- Payload: `user_id`, `initiated_via` (`self_service`; the admin-forced path is not built yet),
  `occurred_at`.
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
- Status: not yet emitted (feature not built: no manual edit route for core attributes exists).
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

**`supplier.check.failed`**
- Producer: `SupplierCheck` (`app.suppliers.application.check_service`), when a mandatory source (the
  CNPJ registry or the sanctions index) was unavailable. The check is marked failed, and no
  `SupplierProfile` is replaced.
- Meaning: the check produced no usable outcome, and must not be read as a clean one.
- Payload: `supplier_id`, `check_id`, `reason`.
- Consumers: none beyond the audit trail. The supplier's status does not change.
- Audit implications: `actor_id` is null (system-initiated). This is the record that an incomplete
  verification never looked like a clean one (`supplier-compliance.md`, step 3).

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

**`document.processing_failed`**
- Producer: `ContractVersion` extraction (`app.contracts.application.extraction_orchestration`), when
  a document cannot be parsed or yields no extractable text, before any AI call. The `Document`
  moves to `processing_failed` and the version to `extraction_failed` in the same transaction.
- Meaning: the file could not be turned into text, so its contents were never extracted.
- Payload: `document_id`, `contract_version_id`, `reason`.
- Consumers: none beyond the audit trail; the failed version is visible through the Contracts API.
- Audit implications: `actor_id` is null (system-initiated). An unreadable document is a different
  outcome from a low-confidence extraction (`contract.analysis_needs_confirmation`), and a Decision
  built on either would need to say so.

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

**`contract.analysis_needs_confirmation`**
- Producer: `ContractVersion` extraction (`app.contracts.application.extraction_orchestration`), the
  same emission site as `contract.analysis_completed`, selected by the outcome: extraction finished
  below the `BR-CON-003` confidence threshold, or with no fields.
- Meaning: extraction ran, but the version cannot be evaluated until a human confirms it.
- Payload: `contract_id`, `contract_version_id`, `extraction_confidence`, `clause_count`.
- Consumers: the Contracts API (`needs_confirmation` status); the confirmation endpoint then emits
  `contract.version_confirmed` and `contract.analysis_completed`.
- Audit implications: records that this version was not analyzed automatically. Without it the trail
  shows only the upload, with no sign that a human decision was pending.

**`contract.version_confirmed`**
- Producer: `ContractVersion` aggregate (`app.contracts.application.confirmation_service`), on
  `POST .../versions/{version_id}/confirm`. Emitted in the same transaction as
  `contract.analysis_completed` (with `via_human_confirmation: true`).
- Meaning: a human reviewed the extracted fields of a `needs_confirmation` version, optionally
  correcting some, and marked it analyzed.
- Payload: `contract_id`, `contract_version_id`, `corrected_fields` (sorted field paths the human
  changed; empty when confirmed as-is).
- Consumers: `Policy & Compliance` evaluation, via `contract.analysis_completed`.
- Audit implications: `actor_id` is the confirming human. This is the record that a Decision built
  on this version relied on human-confirmed data (`BR-CON-003`). The corrected values themselves
  live in the version's `extracted_data`, not in this payload.

### Policy & Compliance

**`policy.created`**
- Producer: `Policy` aggregate, on authoring a new named rule collection (`POL-001`).
- Meaning: an organization started defining a new policy.
- Payload: `policy_id`, `organization_id`, `name`, `created_by`.
- Consumers: policy authoring UI, draft-state rule editor.
- Audit implications: establishes who introduced a given policy area, relevant when a customer asks
  "who decided we needed a rule about X?"

**`policy.rule_created`**
- Producer: `Rule` (`app.policies.application.rule_service`), on adding a rule to a draft
  `PolicyVersion` via `POST .../versions/{version_id}/rules`.
- Meaning: a rule was authored into a draft version. Rules are mutable until publish.
- Payload: `policy_id`, `policy_version_id`, `rule_id`, `rule_key`, `result_status`, `severity`.
- Consumers: none beyond the audit trail; the rule is evaluated only once its version is published
  (`policy.version_published`).
- Audit implications: `actor_id` records who authored each rule before publish, so a published rule
  set can be traced back to its authors.

**`policy.rule_updated`**
- Producer: `Rule` (`app.policies.application.rule_service`), on `PUT .../rules/{rule_id}` against a
  draft version. A published version's rules are frozen, and the update is rejected.
- Meaning: a draft rule was replaced with a revised definition.
- Payload: `policy_id`, `policy_version_id`, `rule_id`, `rule_key` (the key after the edit).
- Consumers: none beyond the audit trail.
- Audit implications: draft rules are updated in place, not versioned, and the payload does not carry
  the before or after definition. This event is the only record that a rule changed before publish.

**`policy.version_draft_created`**
- Producer: `PolicyVersion` (`app.policies.application.policy_service.create_draft_version`), on
  `POST /api/policies/{policy_id}/versions` (`BR-POL-001` copy-modify path).
- Meaning: a new draft version of an existing policy was opened, copying the rules of the version it
  was based on.
- Payload: `policy_id`, `policy_version_id`, `version_number`, `copied_from_version_id` (the version
  whose rules were copied; null when there was none).
- Consumers: none beyond the audit trail.
- Audit implications: opens the change window that `policy.version_published` closes, so the two
  events bracket every edit to a policy's rule set.

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

**`policy.exception_granted`**
- Producer: `PolicyException` aggregate (`app.policies.application.exception_service.
  grant_exception`), on `POST /api/policies/{policy_id}/versions/{version_id}/rules/{rule_id}/
  exceptions` (STORY-4.4.2).
- Meaning: an approver holding the waived rule's own `approver_role` granted a time-boxed waiver
  of one REVIEW-tier `Rule` for one Supplier or ContractVersion, with a mandatory justification.
- Payload: `policy_exception_id`, `rule_id`, `rule_key`, `supplier_id` (null if the target is a
  contract version), `contract_version_id` (null if the target is a supplier), `approver_role`,
  `valid_until`.
- Consumers: `evaluation_service.evaluate_rule` (an active exception short-circuits CEL evaluation
  for its rule, producing an `EXEMPTED` `RuleEvaluation` instead); the review-results screen (cites
  the exception as the reason a would-be `REVIEW` rule did not fire).
- Audit implications: this is the one event that makes an `EXEMPTED` outcome explainable after the
  fact — it is never a rule mutation (`Rule.when`/`compiled_*_cel` are untouched), only a
  documented override input, append-only like every other record in this domain (no update/delete
  path exists on `PolicyExceptionRepository`).

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
  (`expired`/`policy_changed`/`contract_changed`/`supplier_changed`/`override_review_required`),
  `flagged_at`.
- `override_review_required` (FEATURE-6.5): the flagged Decision carries a human override. It is
  NOT re-evaluated and gets no successor; a human must confirm it or run a manual review.
- Consumers: scheduling/notification for a fresh `ComplianceReview`.
- Audit implications: proves the system never let a stale decision look current without flagging it
  — directly evidences `BR-DEC-004` compliance to an auditor.

**`compliance.reevaluation_failed`** (FEATURE-6.5)
- Producer: `reevaluation_service`, once per Decision, when its re-evaluation has been attempted the
  configured maximum number of times and the latest attempt's approval chain expired without a
  Decision.
- Meaning: automatic re-evaluation of this Decision has stopped. It stays ACTIVE and flagged, and
  needs a human (a manual review or an override decision).
- Payload: `decision_id`, `attempts`, `last_review_id`, `failed_at`. Emitted at most once per Decision.
  `attempts` counts the re-evaluation reviews whose approval chain expired (the retry path), or the
  attempts that raised an exception (the execution-error path, FEATURE-6.5 review F4); `last_review_id`
  is `null` when no review was produced.
- Consumers: operator alert. A notification channel is future work; the event is the alert today.
- Audit implications: the only record that automatic re-evaluation gave up on a Decision, so it can
  never silently stay stale.

### Approvals & Decisions

**`approval_workflow.updated`**
- Status: not yet emitted (feature not built: no route edits routing configuration).
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

**`approval.expired`**
- Producer: `ApprovalRequest` aggregate, on SLA expiry (`BR-APR-003`), via the Celery task that
  sweeps stale `pending` requests (`app.approvals.infrastructure.tasks`; ADR-006: time-based
  transitions are a Celery task's job, never held in the request/response cycle).
- Meaning: this approval step exceeded its configured SLA without a human resolving it — a
  distinct failure mode from `approval.rejected` ("nobody got to it in time" vs. "a human actively
  declined").
- Payload: `approval_request_id`, `compliance_review_id`, `approver_role`, `step_number`,
  `requested_at`, `expired_at`.
- Consumers: none yet (no admin-intervention/re-routing path exists — tracked as future work); the
  review simply has no `Decision` until one is built.
- Audit implications: `actor_id` is always `null` on this event (system-initiated, no human actor)
  — the Decision Passport must be able to show an SLA breach as its own distinct category, not
  conflated with an active rejection.

**`decision.created`**
- Producer: `Decision` aggregate, once a `ComplianceReview` (and any required approval chain)
  reaches a terminal outcome (`DEC-001`).
- Meaning: the final, packaged compliance outcome for a `ComplianceReview` now exists.
- Payload: `decision_id`, `compliance_review_id`, `status` (`APPROVE|REVIEW|BLOCK`), `valid_until`,
  `supersedes_decision_id` (nullable), `superseded_decision_ids` (FEATURE-6.5: every Decision this
  one moved to `SUPERSEDED` when it was created, possibly empty), `created_at`.
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

**`evidence.override_addendum_recorded`**
- Producer: `EvidenceOverrideAddendum` aggregate (`app.evidence.application.evidence_package_
  service.record_override_addendum`), called by `decision_service.override_decision` in the
  same transaction as `decision.overridden`, right after it (product decision 2026-10-10,
  closing #187).
- Meaning: a Decision's EvidencePackage has gained one more chained, anchorable addendum
  recording an override -- closing the gap where `override_decision` changed `Decision.status`
  in place but never touched the package built for it, leaving anchored evidence silently stale
  relative to the real, current outcome. A Decision can be overridden more than once while it
  stays `ACTIVE`, so a package can accumulate more than one addendum.
- Payload: `evidence_override_addendum_id`, `evidence_package_id`, `decision_id`,
  `sequence_number`, `content_hash`.
- Consumers: none yet -- addenda are stored and readable through the evidence-package API
  (`GET /api/evidence-packages/{id}`, `GET /api/decisions/{id}/evidence-package`) but are not
  yet submitted to `BlockchainAnchor`/`AnchoringProvider` on their own; that wiring is deferred.
- Audit implications: `content_hash` chains to the previous addendum's hash (`previous_hash`,
  `docs/03-domain/evidence.md`), so a sequence of overrides on the same package is itself
  tamper-evident and strictly ordered, the same guarantee the package's own Merkle root gives
  its leaves.

**`evidence.anchored`**
- Producer: `BlockchainAnchor` aggregate (`app.evidence.application.anchoring_service.
  check_anchor_status`/`submit_anchor`), the first time a submission's status settles to
  `confirmed` via the configured `AnchoringProvider` (`ADR-007`, `EVD-003`). Never emitted for
  a `failed` settlement (visible on the row's own `status`, not a separate audited event yet)
  or on a poll that finds the anchor still `submitted`.
- Meaning: the `EvidencePackage`'s Merkle root is now anchored on a public, tamper-evident
  ledger -- or, while `provider` is `transparency_log`, on the labeled fallback
  (`docs/09-planning/risks.md` risk 4; not a blockchain anchor).
- Payload: `blockchain_anchor_id`, `evidence_package_id`, `provider`, `anchor_ref`,
  `submitted_at`, `confirmed_at`.
- Consumers: public verification page (`docs/06-blockchain/verification.md`); customer-facing
  Decision Passport UI.
- Audit implications: the final, externally-checkable link in the chain — an auditor or counterparty
  can, independent of JuriSense Gate's own database, confirm the anchored hash matches a
  recomputed `merkle_root` from the (internally retained) `Evidence` set.

### Integrations

**`integration.connected`**
- Producer: `Integration` aggregate (`app.integrations.application.integration_service`), on
  `POST /api/integrations`, an admin configuring an external system connection (`INT-001`).
  Emitted in the same transaction as the record.
- Meaning: an external system (e.g. DocuSign, Slack) is now connected on behalf of the organization.
- Payload: `integration_id`, `organization_id`, `provider`, `connected_by`, `connected_at`. The
  `config` is deliberately not in the payload: it may hold connector credentials.
- Consumers: the integration's own sync/webhook workers.
- Audit implications: establishes when third-party access to organization data/events began —
  relevant to LGPD data-sharing accountability.

**`integration.disconnected`**
- Status: not yet emitted (feature not built: no disconnect or credential-revocation route exists).
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
