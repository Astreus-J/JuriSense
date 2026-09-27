# Domain Model

Bounded contexts (see `docs/04-architecture/components.md` for boundary rules): **Identity &
Organizations, Suppliers, Contracts & Documents, Policy & Compliance, Approvals & Decisions,
Evidence & Audit, AI Services, Integrations**.

Each entity below is documented with: Purpose, Identity, Core attributes, Relationships,
Invariants, Lifecycle, Events, Versioning behavior, Tenant ownership.

---

## Organization
*Context: Identity & Organizations*
- **Purpose**: the tenant root; everything else belongs to exactly one Organization.
- **Identity**: `id` (UUID).
- **Core attributes**: `name`, `tax_id` (CNPJ for Brazil, jurisdiction-specific for other packs),
  `address`, `plan`, `status`.
- **Relationships**: has many `Membership`, `Supplier`, `Contract`, `Policy`, `Integration`.
- **Invariants**: `tax_id` unique per jurisdiction pack; cannot be deleted while active
  subscriptions/decisions reference it (soft-delete only).
- **Lifecycle**: `trial → active → past_due → cancelled/expired` (`ADR-014`).
- **Events**: `organization.created`, `organization.plan_changed`.
- **Versioning**: not versioned; plan changes are logged as events, not versions.
- **Tenant ownership**: is the tenant boundary itself.

## Membership
*Context: Identity & Organizations*
- **Purpose**: links a `User` to an `Organization` with a `Role`.
- **Identity**: `id` (UUID).
- **Core attributes**: `user_id`, `organization_id`, `role`, `status` (active/invited/revoked).
- **Relationships**: belongs to `Organization` and `User`.
- **Invariants**: a `User` may hold memberships in more than one `Organization` (e.g. a consultant),
  but every permission check is scoped to one `Membership` at a time.
- **Lifecycle**: `invited → active → revoked`.
- **Events**: `membership.invited`, `membership.accepted`, `membership.revoked`.
- **Versioning**: not versioned.
- **Tenant ownership**: `organization_id`.

## User
*Context: Identity & Organizations*
- **Purpose**: an authenticated individual (reused/renamed from the existing `Usuario` model).
- **Identity**: `id` (UUID).
- **Core attributes**: `email`, `password_hash` (Argon2id), `name`, `status`, `last_access`,
  2FA fields.
- **Relationships**: has many `Membership`.
- **Invariants**: email unique globally (not per-tenant — a person may belong to multiple orgs).
- **Lifecycle**: `pending → active → blocked/inactive` (`ADR-011`, `ADR-013`).
- **Events**: `user.registered`, `user.login_succeeded`, `user.login_failed`, `user.password_reset`.
- **Versioning**: not versioned.
- **Tenant ownership**: none directly (scoped via `Membership`).

## Role
*Context: Identity & Organizations*
- **Purpose**: named permission grid (`ADR-003`, `ADR-012`).
- **Identity**: `id` (slug, e.g. `legal`, `compliance`).
- **Core attributes**: `name`, `default_permissions` (module × action grid).
- **Relationships**: assigned via `Membership`; may be overridden per-user by an admin.
- **Invariants**: `Admin` role always exists and cannot be deleted.
- **Lifecycle**: static seed set for v1; custom roles are a future-roadmap item.
- **Events**: `role.permissions_updated`.
- **Versioning**: not versioned in v1 (custom/versioned roles are a documented future item).
- **Tenant ownership**: global defaults; per-user overrides are tenant-scoped via `Membership`.

## Supplier
*Context: Suppliers*
- **Purpose**: a third party the organization is evaluating or has contracted.
- **Identity**: `id` (UUID).
- **Core attributes**: `legal_name`, `tax_id`, `jurisdiction`, `status`
  (`prospect/under_review/approved/blocked/inactive`).
- **Relationships**: has one active `SupplierProfile`, many `SupplierCheck`, many `Contract`.
- **Invariants**: `tax_id` + `organization_id` unique together.
- **Lifecycle**: `prospect → under_review → approved|blocked → inactive`.
- **Events**: `supplier.created`, `supplier.updated`, `supplier.status_changed`.
- **Versioning**: not versioned itself; its `SupplierCheck` history is the audit trail.
- **Tenant ownership**: `organization_id`.

## SupplierProfile
*Context: Suppliers*
- **Purpose**: normalized, current-state snapshot of a supplier's registry/corporate data.
- **Identity**: `id` (UUID), one active per `Supplier`.
- **Core attributes**: registry status, corporate structure, responsible parties, CNAE
  (or jurisdiction equivalent), address.
- **Relationships**: belongs to `Supplier`; produced by `SupplierCheck` runs.
- **Invariants**: always reflects the most recent successful `SupplierCheck`.
- **Lifecycle**: replaced (not mutated) on every successful re-check.
- **Events**: `supplier.profile_updated`.
- **Versioning**: implicit via the `SupplierCheck` history; the profile itself is a materialized
  current view.
- **Tenant ownership**: via `Supplier.organization_id`.

## SupplierCheck
*Context: Suppliers*
- **Purpose**: one point-in-time verification run against official/external sources.
- **Identity**: `id` (UUID).
- **Core attributes**: `supplier_id`, `sources_consulted`, `raw_results`, `started_at`,
  `completed_at`, `status`.
- **Relationships**: belongs to `Supplier`; feeds `SupplierProfile` and `ComplianceReview` evidence.
- **Invariants**: immutable once `completed`.
- **Lifecycle**: `started → completed|failed`.
- **Events**: `supplier.check.started`, `supplier.check.completed`.
- **Versioning**: each run is its own immutable record — this *is* the versioning mechanism.
- **Tenant ownership**: via `Supplier.organization_id`.

## Document
*Context: Contracts & Documents*
- **Purpose**: any uploaded file (contract, supporting evidence, certificate).
- **Identity**: `id` (UUID).
- **Core attributes**: `storage_key` (object storage, `ADR-008`), `content_hash` (SHA-256),
  `mime_type`, `uploaded_by`.
- **Relationships**: may belong to a `Contract` (as a `ContractVersion`'s source file) or stand
  alone (supporting evidence).
- **Invariants**: `content_hash` computed on upload and never recomputed/mutated.
- **Lifecycle**: `uploaded → processed → (archived)`.
- **Events**: `document.uploaded`, `document.processed`.
- **Versioning**: a `Document` is itself an immutable version; re-upload creates a new `Document`.
- **Tenant ownership**: `organization_id`.

## Contract
*Context: Contracts & Documents*
- **Purpose**: the logical agreement with a `Supplier`, spanning one or more versions over time.
- **Identity**: `id` (UUID).
- **Core attributes**: `supplier_id`, `title`, `contract_type`, `status`.
- **Relationships**: has many `ContractVersion`; has many `ComplianceReview`.
- **Invariants**: always belongs to exactly one `Supplier`.
- **Lifecycle**: `draft → under_review → active → renewed|terminated|expired`.
- **Events**: `contract.created`.
- **Versioning**: versioned via `ContractVersion` (see below), not in-place.
- **Tenant ownership**: `organization_id`.

## ContractVersion
*Context: Contracts & Documents*
- **Purpose**: one immutable snapshot of a contract's text/terms + its AI-extracted structured data.
- **Identity**: `id` (UUID).
- **Core attributes**: `contract_id`, `document_id`, `version_number`, `extracted_data` (JSON,
  schema per `docs/05-ai/structured-extraction.md`), `extraction_confidence`.
- **Relationships**: belongs to `Contract`; references one `Document`; has many `Clause`.
- **Invariants**: immutable once created; a new negotiation round always creates a new
  `ContractVersion`, never edits an existing one.
- **Lifecycle**: `extracted → analyzed → (superseded by next version)`.
- **Events**: `contract.version_created`, `contract.analysis_completed`.
- **Versioning**: is itself the versioning unit for `Contract`.
- **Tenant ownership**: via `Contract.organization_id`.

## Clause
*Context: Contracts & Documents*
- **Purpose**: one AI-identified, citable clause (liability, DPA, termination, etc.) within a
  `ContractVersion`.
- **Identity**: `id` (UUID).
- **Core attributes**: `contract_version_id`, `clause_type`, `page`, `text_span`, `confidence`.
- **Relationships**: belongs to `ContractVersion`; referenced by `RuleEvaluation` as evidence.
- **Invariants**: always carries a page/span back-reference to the source `Document` (provenance —
  see `docs/05-ai/document-intelligence.md`).
- **Lifecycle**: immutable once extracted.
- **Events**: none independent (covered by `contract.analysis_completed`).
- **Versioning**: tied 1:1 to its `ContractVersion`.
- **Tenant ownership**: via `ContractVersion`.

## Policy
*Context: Policy & Compliance*
- **Purpose**: a named, organization-owned collection of `Rule`s.
- **Identity**: `id` (UUID).
- **Core attributes**: `organization_id`, `name`, `status` (`draft/published/archived`).
- **Relationships**: has many `PolicyVersion`.
- **Invariants**: only one `PolicyVersion` is "current" (published and active) at a time.
- **Lifecycle**: `draft → published → (new version published) → archived`.
- **Events**: `policy.created`.
- **Versioning**: via `PolicyVersion`.
- **Tenant ownership**: `organization_id`.

## PolicyVersion
*Context: Policy & Compliance*
- **Purpose**: an immutable, evaluable snapshot of a `Policy`'s rule set.
- **Identity**: `id` (UUID).
- **Core attributes**: `policy_id`, `version_number`, `published_at`, `published_by`.
- **Relationships**: has many `Rule`; referenced by every `ComplianceReview` it was evaluated
  against.
- **Invariants**: immutable once published — editing rules always creates a new `PolicyVersion`
  (this is what makes historical decisions reproducible, per `ADR-010`).
- **Lifecycle**: `published → (superseded)`.
- **Events**: `policy.version_published`.
- **Versioning**: is itself the versioning unit.
- **Tenant ownership**: via `Policy.organization_id`.

## Rule
*Context: Policy & Compliance*
- **Purpose**: one executable condition (`docs/03-domain/policy-engine.md` for the full DSL).
- **Identity**: `id` (business key, e.g. `LGPD-001`) + `policy_version_id`.
- **Core attributes**: `when` (compiled CEL/JSONLogic expression, `ADR-004`), `result`
  (`APPROVE|REVIEW|BLOCK`), `severity`, `approver_role`.
- **Relationships**: belongs to `PolicyVersion`; produces `RuleEvaluation`.
- **Invariants**: immutable once its `PolicyVersion` is published.
- **Lifecycle**: tied to its `PolicyVersion`.
- **Events**: none independent.
- **Versioning**: tied to `PolicyVersion`.
- **Tenant ownership**: via `Policy.organization_id`.

## ComplianceReview
*Context: Policy & Compliance*
- **Purpose**: one evaluation run of a `ContractVersion` (+ `Supplier` evidence) against a
  `PolicyVersion`.
- **Identity**: `id` (UUID).
- **Core attributes**: `contract_version_id`, `policy_version_id`, `status`, `started_at`,
  `completed_at`.
- **Relationships**: has many `RuleEvaluation`; produces zero or one `Decision`.
- **Invariants**: immutable once `completed`.
- **Lifecycle**: `started → completed`.
- **Events**: `compliance.review_started`, `compliance.review_completed`,
  `compliance.review_required` (re-trigger).
- **Versioning**: each review is its own immutable record.
- **Tenant ownership**: via `Contract.organization_id`.

## RuleEvaluation
*Context: Policy & Compliance*
- **Purpose**: the result of evaluating one `Rule` within a `ComplianceReview` (`ADR-010`).
- **Identity**: `id` (UUID).
- **Core attributes**: `rule_id`, `outcome` (`PASS|REVIEW|BLOCK|NOT_APPLICABLE`), `severity`,
  `evidence_refs` (→ `Clause`/`SupplierCheck`), `rationale`.
- **Relationships**: belongs to `ComplianceReview`; references evidence in `Suppliers`/
  `Contracts & Documents`.
- **Invariants**: append-only; never edited, including by overrides (`ADR-010` §3).
- **Lifecycle**: created once, immutable.
- **Events**: `compliance.rule_evaluated`.
- **Versioning**: immutable by construction.
- **Tenant ownership**: via `ComplianceReview`.

## Risk
*Context: Policy & Compliance*
- **Purpose**: a named risk finding surfaced during review (may or may not map 1:1 to a
  `RuleEvaluation`; also used for informational/non-blocking findings).
- **Identity**: `id` (UUID).
- **Core attributes**: `category`, `description`, `severity`, `evidence_refs`.
- **Relationships**: belongs to `ComplianceReview`.
- **Invariants**: immutable once created.
- **Lifecycle**: created once.
- **Events**: none independent (covered by `compliance.rule_evaluated`/review completion).
- **Versioning**: immutable.
- **Tenant ownership**: via `ComplianceReview`.

## ApprovalWorkflow
*Context: Approvals & Decisions*
- **Purpose**: the configured routing template for a given risk tier/organization (`ADR-006`).
- **Identity**: `id` (UUID).
- **Core attributes**: `organization_id`, `trigger_condition`, `steps` (ordered approver roles).
- **Relationships**: instantiates `ApprovalRequest`.
- **Invariants**: at least one step required.
- **Lifecycle**: `active/inactive`, editable by admins.
- **Events**: `approval_workflow.updated`.
- **Versioning**: not versioned in v1 (future item if historical reproducibility of *workflow
  configuration* — not just decisions — becomes required).
- **Tenant ownership**: `organization_id`.

## ApprovalRequest
*Context: Approvals & Decisions*
- **Purpose**: one concrete instance of a human approval step for a `ComplianceReview` with a
  `REVIEW` outcome.
- **Identity**: `id` (UUID).
- **Core attributes**: `compliance_review_id`, `approver_role`, `status`
  (`pending/approved/rejected/expired`), `justification`.
- **Relationships**: belongs to `ComplianceReview`; instantiated from `ApprovalWorkflow`.
- **Invariants**: state transitions enforced in the application layer (`ADR-006`); rejection or
  approval requires an actor with the matching `Role`.
- **Lifecycle**: `pending → approved|rejected|expired`.
- **Events**: `approval.requested`, `approval.approved`, `approval.rejected`.
- **Versioning**: immutable once resolved.
- **Tenant ownership**: via `ComplianceReview`.

## Decision
*Context: Approvals & Decisions*
- **Purpose**: the final, packaged compliance outcome for a `ComplianceReview`.
- **Identity**: `id` (UUID).
- **Core attributes**: `compliance_review_id`, `status` (`APPROVE|REVIEW|BLOCK`), `valid_until`,
  `supersedes_decision_id` (nullable), `overridden` (bool), `override_justification` (nullable).
- **Relationships**: one-to-one with `ComplianceReview`; source for `EvidencePackage`.
- **Invariants**: never edited in place once created — a re-evaluation creates a new `Decision`
  with `supersedes_decision_id` set (`ADR-010` §4).
- **Lifecycle**: `created → (expired|superseded)`.
- **Events**: `decision.created`, `decision.overridden`.
- **Versioning**: immutable; superseding chain is the version history.
- **Tenant ownership**: via `ComplianceReview`.

## Evidence
*Context: Evidence & Audit*
- **Purpose**: one atomic piece of evidence referenced by a `Decision` (a document hash, a
  `SupplierCheck` result, a `RuleEvaluation`).
- **Identity**: `id` (UUID).
- **Core attributes**: `type`, `ref_id`, `content_hash`.
- **Relationships**: belongs to an `EvidencePackage`.
- **Invariants**: immutable.
- **Lifecycle**: created once.
- **Events**: none independent.
- **Versioning**: immutable.
- **Tenant ownership**: via `EvidencePackage`.

## EvidencePackage
*Context: Evidence & Audit*
- **Purpose**: the complete, hashable bundle backing one `Decision` — the payload that gets
  anchored on-chain (`ADR-007`).
- **Identity**: `id` (UUID).
- **Core attributes**: `decision_id`, `merkle_root`, `created_at`.
- **Relationships**: has many `Evidence`; produces zero or one `BlockchainAnchor`.
- **Invariants**: immutable; `merkle_root` is deterministically recomputable from its `Evidence` set.
- **Lifecycle**: `created → anchored`.
- **Events**: `evidence.package_created`, `evidence.anchored`.
- **Versioning**: immutable; a new `Decision` produces a new `EvidencePackage`.
- **Tenant ownership**: via `Decision`.

## AuditEvent
*Context: Evidence & Audit*
- **Purpose**: append-only log of every meaningful domain action (catalog in
  `docs/03-domain/audit.md`).
- **Identity**: `id` (UUID, monotonically ordered).
- **Core attributes**: `event_type`, `actor_id`, `payload`, `occurred_at`.
- **Relationships**: references any other entity by id in `payload`.
- **Invariants**: append-only, never updated or deleted.
- **Lifecycle**: created once.
- **Events**: is itself the event log (not an entity that emits further events).
- **Versioning**: immutable by construction.
- **Tenant ownership**: `organization_id` (nullable for system-level events).

## BlockchainAnchor
*Context: Evidence & Audit*
- **Purpose**: the on-chain reference proving an `EvidencePackage`'s hash was anchored at a point
  in time (`ADR-007`).
- **Identity**: `id` (UUID).
- **Core attributes**: `evidence_package_id`, `provider`, `anchor_ref`, `submitted_at`,
  `proof`.
- **Relationships**: belongs to `EvidencePackage`.
- **Invariants**: immutable once confirmed; `provider` is one of the `AnchoringProvider`
  implementations (`06-blockchain/anchoring-providers.md`).
- **Lifecycle**: `submitted → confirmed|failed`.
- **Events**: `evidence.anchored`.
- **Versioning**: immutable.
- **Tenant ownership**: via `EvidencePackage`.

## Integration
*Context: Integrations*
- **Purpose**: a configured external system connection (e.g., DocuSign, Slack, a future ERP
  connector).
- **Identity**: `id` (UUID).
- **Core attributes**: `organization_id`, `provider`, `config` (secrets stored separately),
  `status`.
- **Relationships**: emits/consumes domain events on behalf of the organization.
- **Invariants**: never writes directly to business-domain tables — always through application
  commands (see `04-architecture/components.md` boundary rules).
- **Lifecycle**: `configured → active/disabled`.
- **Events**: `integration.connected`, `integration.disconnected`.
- **Versioning**: not versioned.
- **Tenant ownership**: `organization_id`.
