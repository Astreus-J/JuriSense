# Functional Requirements

Traceable IDs by area, per `docs/03-domain/domain-model.md` bounded contexts. Each requirement is a
capability the system **shall** provide; behavioral invariants live in
`docs/03-domain/business-rules.md` (`BR-*`) and are cross-referenced where relevant. This list
covers the Hackathon Cut scope (`docs/08-hackathon/fallback-mvp.md`) in full depth; post-hackathon
phases (Phases 9–11, `docs/09-planning/roadmap.md`) will extend this list as they are scoped.

## Identity & Organizations (ORG)

- **ORG-001**: The system shall allow a new `Organization` to be created with a name, tax id, and
  initial plan.
- **ORG-002**: The system shall allow an admin to invite `User`s to an `Organization` with a
  specific `Role` (reuses the existing invite mechanism in `Accounts`).
- **ORG-003**: The system shall enforce plan limits (suppliers, contracts, AI executions) per
  `BR-ORG-003`.
- **ORG-004**: The system shall allow an admin to customize per-user permission grants beyond the
  default `Role` grid (`ADR-003`, `ADR-012`).
- **ORG-005**: The system shall support a `User` holding memberships in multiple organizations
  (`BR-ORG-001`).

## Suppliers (SUP)

- **SUP-001**: The system shall allow an authorized user to register a `Supplier` with a
  jurisdiction-specific identifier (CNPJ for Brazil).
- **SUP-002**: The system shall trigger a `SupplierCheck` against configured external sources on
  supplier creation and on manual re-check request.
- **SUP-003**: The system shall normalize `SupplierCheck` results into a current `SupplierProfile`.
- **SUP-004**: The system shall surface a sanctions-list hit as a blocking condition per
  `BR-SUP-004`.
- **SUP-005**: The system shall maintain full `SupplierCheck` history per supplier (immutable,
  timestamped).

## Contracts & Documents (CON)

- **CON-001**: The system shall allow an authorized user to upload a contract document
  (PDF/DOCX/TXT).
- **CON-002**: The system shall create a new `ContractVersion` for every uploaded revision, never
  overwriting a previous version (`BR-CON-002`).
- **CON-003**: The system shall run AI structured extraction on every new `ContractVersion`,
  producing the schema defined in `docs/05-ai/structured-extraction.md`.
- **CON-004**: The system shall attach page/span provenance to every extracted `Clause`
  (`BR-CON-004`).
- **CON-005**: The system shall flag `ContractVersion`s below a minimum extraction confidence for
  mandatory human confirmation before compliance review proceeds (`BR-CON-003`).

## Policy & Compliance (POL / CMP)

- **POL-001**: The system shall allow an authorized user to author a `Policy` and its `Rule`s using
  the YAML DSL (`docs/03-domain/policy-engine.md`).
- **POL-002**: The system shall version every published set of rules as an immutable `PolicyVersion`
  (`BR-POL-001`, `BR-POL-002`).
- **POL-003**: The system shall support simulation/dry-run of a draft `PolicyVersion` against
  existing contracts before publishing.
- **POL-004**: The system shall support time-boxed policy exceptions with mandatory justification
  and approver sign-off.
- **CMP-001**: The system shall evaluate every applicable `Rule` in the current `PolicyVersion`
  against normalized supplier + contract evidence for each `ComplianceReview` (`BR-CMP-001`).
- **CMP-002**: The system shall aggregate `RuleEvaluation`s into a final status using the algorithm
  in `ADR-010` (`BR-CMP-002`).
- **CMP-003**: The system shall persist every `RuleEvaluation` as an immutable, evidence-linked
  record (`BR-CMP-003`).

## Approvals & Decisions (APR / DEC)

- **APR-001**: The system shall route a `REVIEW` outcome to the correct `approver_role` based on the
  configured `ApprovalWorkflow`.
- **APR-002**: The system shall only allow an `ApprovalRequest` to be resolved by a user whose role
  matches the required `approver_role` (`BR-APR-001`).
- **APR-003**: The system shall support multi-step approval chains (e.g., Legal then Director) for
  high-severity cases.
- **DEC-001**: The system shall generate a `Decision` (`APPROVE|REVIEW|BLOCK`) for every completed
  `ComplianceReview`, preserving the `PolicyVersion` used (`BR-DEC-001`).
- **DEC-002**: The system shall support authorized manual override of a `Decision` with mandatory
  justification, without deleting the original evaluation record (`BR-DEC-003`).
- **DEC-003**: The system shall trigger re-evaluation when a `Decision`'s validity expires or its
  underlying `ContractVersion`/`PolicyVersion` changes (`BR-DEC-004`).

## Evidence & Audit (EVD / AUD)

- **EVD-001**: The system shall assemble a complete `EvidencePackage` for every `Decision`,
  including document hashes, policy version, rule evaluations, and reviewer identities.
- **EVD-002**: The system shall compute a deterministic Merkle root over each `EvidencePackage`
  (`BR-EVD-001`).
- **EVD-003**: The system shall anchor the `EvidencePackage` hash via the configured
  `AnchoringProvider` (`ADR-007`) and expose a public verification page
  (`docs/06-blockchain/verification.md`).
- **EVD-004**: The system shall never include raw contract text or personal data in any on-chain
  payload (`BR-EVD-002`).
- **AUD-001**: The system shall emit an append-only `AuditEvent` for every state-changing action
  listed in the event catalog (`docs/03-domain/audit.md`).
- **AUD-002**: The system shall provide no update or delete operation for `AuditEvent` records,
  including to Admin roles (`BR-EVD-003`).

## AI Services (AI)

- **AI-001**: The system shall extract structured contract data via the AI Gateway abstraction
  (`ADR-005`), never via direct provider calls from other contexts.
- **AI-002**: The system shall attach a confidence score and source citation to every extracted
  field (`docs/05-ai/document-intelligence.md`).
- **AI-003**: The system shall fall back to a secondary AI provider on primary-provider error or
  timeout.
- **AI-004**: The system shall never allow `AI Services` output to directly set a `Decision`
  status — only `Policy & Compliance` may do so (context boundary rule,
  `docs/04-architecture/components.md`).

## Security (SEC)

- **SEC-001**: The system shall enforce tenant isolation on every tenant-owned table via
  `organization_id` (`ADR-003`).
- **SEC-002**: The system shall require a passing security audit (per `ADR-016`) before any sprint's
  work is considered done, including an explicit cross-tenant-access test.
- **SEC-003**: The system shall validate and scan every uploaded document for malware/type-spoofing
  before processing (`docs/07-engineering/security.md`).

## Integrations (INT)

- **INT-001**: The system shall allow an admin to configure an external `Integration` without
  granting it direct write access to business-domain tables (`ADR` boundary rule,
  `docs/04-architecture/components.md`).
- **INT-002**: The system shall expose outbound webhooks for key lifecycle events
  (`supplier.review.completed`, `contract.review.completed`, `approval.required`,
  `decision.completed`) for future integration consumers.
