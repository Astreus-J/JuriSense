# Glossary

Alphabetical. Entity definitions here are intentionally one line — see
`docs/03-domain/domain-model.md` for the full definition of each entity (purpose, identity,
attributes, relationships, invariants, lifecycle, events, versioning, tenant ownership). Non-entity
terms are defined fully here, since they don't have a dedicated domain-model section of their own.

## ADR (Architecture Decision Record)

A short, numbered document (`docs/adr/ADR-NNN-*.md`) recording one significant technical or product
decision: its context, the decision itself, alternatives considered, and consequences. JuriSense uses
ADRs to keep decisions like the Policy Engine's expression language (`ADR-004`) or the decision
aggregation algorithm (`ADR-010`) explicit and traceable instead of implicit in code.

## AI Gateway

The internal abstraction layer (`ADR-005`) through which all LLM/AI provider calls are made. No
bounded context calls an AI provider directly; every extraction, classification, or summarization
request goes through the AI Gateway, which handles provider selection, fallback on error/timeout
(`AI-003`), and provenance tracking (model/prompt version) for every AI execution.

## Anchoring Provider

The provider-agnostic interface (`ADR-007`) through which an `EvidencePackage`'s hash is submitted to
a blockchain and later verified: `submit_hash`, `get_proof`, `verify`. No code outside this interface
depends on a specific chain SDK, so the concrete provider (a candidate list currently includes
Constellation Network and EVM-compatible testnets, per `ADR-007`) can change without touching anything
above it in the stack. Distinct from `BlockchainAnchor`, which is the domain entity recording one
concrete anchoring result.

## ApprovalRequest

*Entity, context: Approvals & Decisions.* One concrete instance of a required human approval step for
a `ComplianceReview` that resulted in `REVIEW`. See `docs/03-domain/domain-model.md`.

## ApprovalWorkflow

*Entity, context: Approvals & Decisions.* The configured routing template that determines which
approver role(s) a given risk tier requires. See `docs/03-domain/domain-model.md`.

## Approver Role

The specific `Role` (e.g., `legal`, `compliance`, `director`) that a `Rule` or `ApprovalWorkflow`
names as required to resolve a `REVIEW` outcome. An `ApprovalRequest` can only be approved or rejected
by a user whose active `Membership` role matches the required approver role (`BR-APR-001`).

## Audit Trail

The complete, append-only, chronologically ordered set of `AuditEvent` records for an organization (or
the system as a whole) — the mechanism that makes "what happened, and when" answerable without relying
on anyone's memory. See `docs/03-domain/audit.md` for the full event catalog.

## AuditEvent

*Entity, context: Evidence & Audit.* One append-only log record of a meaningful domain action; has no
update or delete operation anywhere in the system, including for Admin roles. See
`docs/03-domain/domain-model.md`.

## Bounded Context

A Domain-Driven Design concept: a boundary within which a specific domain model and its terms have one
consistent meaning, and across which integration happens only through defined contracts (commands,
events, application-layer calls) rather than shared internal state. JuriSense's domain is organized
into eight bounded contexts: **Identity & Organizations, Suppliers, Contracts & Documents, Policy &
Compliance, Approvals & Decisions, Evidence & Audit, AI Services, Integrations** (see
`docs/03-domain/domain-model.md` and boundary rules in `docs/04-architecture/components.md`).

## CEIS / CNEP / CEPIM

Brazilian federal sanctions and restriction registries consulted during a `SupplierCheck`: CEIS
(Cadastro de Empresas Inidôneas e Suspensas — companies barred or suspended from contracting with
public administration), CNEP (Cadastro Nacional de Empresas Punidas — companies sanctioned under the
Brazilian anti-corruption law), and CEPIM (Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas
— nonprofit entities barred from receiving public funds/agreements). A positive hit on any of these
forces a supplier toward `BLOCK` via rule `SANC-001` (`BR-SUP-004`).

## CEL (Common Expression Language)

The compact, sandboxed expression language, evaluated in-process (Python bindings via `cel-python`),
that the Policy Engine's `Rule.when` clauses compile to (`ADR-004`). Chosen over general-purpose policy
engines like OPA/Rego (too heavyweight/operationally costly for this use case) and over AWS Cedar
(purpose-built for resource authorization, not arbitrary business conditionals). JSONLogic is kept as
an alternative compilation target for a future no-code rule builder.

## Clause

*Entity, context: Contracts & Documents.* One AI-identified, citable clause (liability, DPA,
termination, etc.) within a `ContractVersion`, always carrying a page/span citation back to its source
document. See `docs/03-domain/domain-model.md`.

## CLM (Contract Lifecycle Management)

The software category for tools that manage a contract from drafting through negotiation, signature,
and renewal (e.g., Ironclad). JuriSense Gate overlaps with CLM in contract intelligence but is scoped
narrower and deeper on the compliance-gate decision itself, rather than full lifecycle/authoring
tooling (see `docs/00-project/overview.md`, "Market").

## CNPJ (Cadastro Nacional da Pessoa Jurídica)

Brazil's national registry identifier for legal entities — the jurisdiction-specific `tax_id` used to
uniquely identify an `Organization` or `Supplier` within the Brazil Jurisdiction Pack (`BR-ORG-002`,
`BR-SUP-002`). Other Jurisdiction Packs use their own equivalent identifier.

## Compliance Engine

The component (within the Policy & Compliance bounded context) that combines supplier data, contract
data, AI analysis, and deterministic policy rules into one final, explainable `Decision`, using the
aggregation algorithm in `ADR-010`. See `docs/03-domain/policy-engine.md`.

## ComplianceReview

*Entity, context: Policy & Compliance.* One evaluation run of a `ContractVersion` (plus `Supplier`
evidence) against a `PolicyVersion`, producing `RuleEvaluation`s and, on completion, a `Decision`. See
`docs/03-domain/domain-model.md`.

## Contract

*Entity, context: Contracts & Documents.* The logical agreement with a `Supplier`, spanning one or more
immutable `ContractVersion`s over time. See `docs/03-domain/domain-model.md`.

## ContractVersion

*Entity, context: Contracts & Documents.* One immutable snapshot of a contract's text/terms and its
AI-extracted structured data; every negotiation round creates a new one rather than editing an
existing one (`BR-CON-002`). See `docs/03-domain/domain-model.md`.

## Core Platform

The jurisdiction-agnostic part of the architecture — the domain model, Policy Engine mechanics,
workflow/decision/evidence machinery — that stays constant across markets, as distinct from
**Jurisdiction Packs**, which hold jurisdiction-specific rules and source adapters. See
`docs/00-project/overview.md`, "Internationalization."

## Decision

*Entity, context: Approvals & Decisions.* The final, packaged `APPROVE`/`REVIEW`/`BLOCK` outcome for a
`ComplianceReview`; never edited in place — re-evaluation always creates a new `Decision` that
supersedes the old one. See `docs/03-domain/domain-model.md` and `ADR-010`.

## Decision Passport

The customer-facing packaging of a `Decision` and its full supporting `EvidencePackage` — the document
that answers "why was this approved?" with decision id, supplier, contract, document hashes, policy
version, rules triggered, external sources consulted, AI executions, reviewers, and timestamp, in a
form that remains meaningful months or years after the fact. See `docs/03-domain/evidence.md`.

## Document

*Entity, context: Contracts & Documents.* Any uploaded file (contract, supporting evidence,
certificate); immutable once uploaded, with a SHA-256 `content_hash` computed once and never
recomputed. See `docs/03-domain/domain-model.md`.

## DPA (Data Processing Agreement)

The contractual instrument required under LGPD (and analogous regimes) whenever a vendor processes
personal data on a company's behalf. Whether a contract's extracted terms show `dpa_present` alongside
`processes_personal_data: true` is exactly what rule `LGPD-001` checks — a missing DPA on a
personal-data-processing contract is a `BLOCK` condition, not a warning.

## DSL (Domain-Specific Language)

A purpose-built, restricted language for expressing rules in one domain rather than a general-purpose
programming language. The Policy Engine's rule authoring format (YAML `id`/`name`/`when`/`result`/
`severity`/`approver_role`, compiling to CEL) is JuriSense's policy DSL — see
`docs/03-domain/policy-engine.md`.

## Evidence

*Entity, context: Evidence & Audit.* One atomic piece of evidence referenced by a `Decision` (a
document hash, a `SupplierCheck` result, a `RuleEvaluation`); immutable. See
`docs/03-domain/domain-model.md`.

## EvidencePackage

*Entity, context: Evidence & Audit.* The complete, hashable bundle of `Evidence` backing one
`Decision` — the payload whose Merkle root gets anchored on-chain via a `BlockchainAnchor`. See
`docs/03-domain/domain-model.md` and `ADR-007`.

## GRC (Governance, Risk, and Compliance)

The software category for platforms that automate compliance program management and audit readiness
(e.g., Vanta, Drata, OneTrust). JuriSense Gate sits adjacent to GRC — it produces compliance decisions
and evidence at the point of vendor/contract signature, which a GRC platform's ongoing program
management can consume, rather than being a general-purpose GRC platform itself (see
`docs/00-project/overview.md`, "Market").

## Hackathon Cut

The explicitly scoped subset of the full roadmap targeted for the BLI Legal Tech Hackathon 2 / Legal
Hack 2026 submission — through Phase 8 (Evidence/Audit plus a working blockchain anchor) of the twelve
planned phases. See `docs/00-project/overview.md`, "Roadmap," and `docs/08-hackathon/fallback-mvp.md`.

## Integration

*Entity, context: Integrations.* A configured external system connection (e.g., DocuSign, Slack, a
future ERP connector); never writes directly to business-domain tables — only through application
commands. See `docs/03-domain/domain-model.md`.

## Jurisdiction Pack

A swappable bundle of jurisdiction-specific logic — sanctions/registry source adapters, policy rule
packs, identifier formats (CNPJ vs. other jurisdictions' equivalents) — kept separate from the
jurisdiction-agnostic **Core Platform** so that expanding beyond Brazil means adding a pack, not
rewriting the domain model. See `docs/00-project/overview.md`, "Internationalization."

## JSONLogic

A lightweight, JSON-native rule expression format, kept as the Policy Engine's secondary/fallback
compilation target for `Rule.when` clauses — specifically for rules that will eventually be generated
by a no-code visual rule builder, where JSONLogic's tree structure is easier to generate safely than
raw CEL text (`ADR-004`).

## LGPD (Lei Geral de Proteção de Dados)

Brazil's general data protection law — the direct analogue to GDPR — governing the processing of
personal data. LGPD compliance is first-class throughout JuriSense's domain model (the
`processes_personal_data`/`dpa_present` fields checked by rule `LGPD-001`) and throughout its own data
handling (`BR-EVD-002`: no personal data is ever placed on-chain).

## Membership

*Entity, context: Identity & Organizations.* The link between a `User` and an `Organization` with a
specific `Role`; a `User` may hold memberships in more than one organization, but every permission
check is scoped to exactly one active membership. See `docs/03-domain/domain-model.md`.

## Merkle Root

A single cryptographic hash that deterministically summarizes a whole set of data (here, the `Evidence`
records in an `EvidencePackage`) such that any later tampering with any one piece of evidence would
produce a different root. Because it is recomputable from the same evidence set at any time
(`BR-EVD-001`), it is what actually gets anchored via a `BlockchainAnchor` — never the raw evidence
itself.

## Modular Monolith

The chosen backend architecture (`ADR-001`, `ADR-002`): a single deployable Python/FastAPI application
internally organized into strict bounded-context modules with enforced boundary rules, rather than a
microservices architecture. Chosen because the team's current stage doesn't justify microservices'
operational overhead, while the internal module boundaries preserve the option to extract a context
into its own service later if needed.

## Organization

*Entity, context: Identity & Organizations.* The tenant root; every other tenant-owned entity belongs
to exactly one Organization. See `docs/03-domain/domain-model.md`.

## Policy

*Entity, context: Policy & Compliance.* A named, organization-owned container for a versioned set of
`Rule`s, published as immutable `PolicyVersion`s. See `docs/03-domain/domain-model.md`.

## Policy Engine

The component (Policy & Compliance bounded context) that lets an organization express internal policy
as executable, versioned `Rule`s and evaluates them deterministically against normalized supplier/
contract evidence. See `docs/03-domain/policy-engine.md` and `ADR-004`.

## PolicyVersion

*Entity, context: Policy & Compliance.* An immutable, evaluable snapshot of a `Policy`'s rule set,
created on every publish; every `ComplianceReview` records exactly which version it used, which is
what keeps historical decisions reproducible even after the policy changes. See
`docs/03-domain/domain-model.md`.

## RBAC (Role-Based Access Control)

The access-control model (`ADR-003`, `ADR-012`) in which permissions are granted through named `Role`s
assigned via `Membership`, with optional per-user overrides layered on top of the default role grid.
Used both for platform permission checks and for gating who may resolve an `ApprovalRequest` or
override a `Decision`.

## Risk

*Entity, context: Policy & Compliance.* A named risk finding surfaced during a `ComplianceReview`
(may or may not map 1:1 to a `RuleEvaluation`), giving reviewers a legible, evidenced view of concerns
beyond the bare rule outcomes. See `docs/03-domain/domain-model.md`.

## Role

*Entity, context: Identity & Organizations.* A named permission grid (e.g., `legal`, `compliance`,
`admin`) assigned to a `User` via `Membership`, and referenced by `Rule`s and `ApprovalWorkflow`s as
the required approver for a given outcome. See `docs/03-domain/domain-model.md`.

## Rule

*Entity, context: Policy & Compliance.* One executable condition within a `PolicyVersion` — a `when`
expression, a `result` (`APPROVE`/`REVIEW`/`BLOCK`), a `severity`, and (for non-auto-approve outcomes)
a required `approver_role`. Immutable once its `PolicyVersion` is published. See
`docs/03-domain/domain-model.md` and `docs/03-domain/policy-engine.md`.

## RuleEvaluation

*Entity, context: Policy & Compliance.* The append-only, immutable result of evaluating one `Rule`
within a `ComplianceReview` — outcome, severity, evidence references, rationale. See
`docs/03-domain/domain-model.md` and `ADR-010`.

## SaaS (Software as a Service)

The delivery model both for JuriSense Gate itself (a multi-tenant subscription platform, see
`docs/00-project/overview.md`, "Business model") and for the single largest category of vendor
JuriSense's own customers are onboarding and reviewing (`docs/00-project/problem.md`).

## Structured Extraction

The AI Services capability that turns an unstructured contract document into typed, structured data
(parties, value, duration, liability, DPA presence, etc.), each field carrying a confidence score and
a source citation, rather than free-text summarization. See `docs/05-ai/structured-extraction.md` and
`AI-002`.

## Supplier

*Entity, context: Suppliers.* A third party the organization is evaluating or has contracted; carries
a jurisdiction-specific `tax_id` (e.g., CNPJ) unique per organization. See
`docs/03-domain/domain-model.md`.

## SupplierCheck

*Entity, context: Suppliers.* One immutable, point-in-time verification run of a `Supplier` against
official/external sources (registries, sanctions lists); the full history of these runs *is* the
supplier's audit trail. See `docs/03-domain/domain-model.md`.

## SupplierProfile

*Entity, context: Suppliers.* The normalized, current-state snapshot of a supplier's registry/corporate
data, replaced (not mutated) on every successful `SupplierCheck`. See `docs/03-domain/domain-model.md`.

## Tenant Isolation

The structural guarantee that one organization's data is never visible to another's, enforced via an
`organization_id` column on every tenant-owned table and an explicit cross-tenant-access test required
before any sprint is considered done (`SEC-001`, `SEC-002`, `ADR-003`).

## TPRM (Third-Party Risk Management)

The software/practice category for assessing and monitoring the risk posed by third-party vendors and
suppliers — the closest overall category match for JuriSense Gate's target buyer problem, per
`docs/00-project/overview.md`, "Market": mid-market technology companies with real procurement volume
and no dedicated TPRM tooling today.

## Trust Layer

The blockchain-based verifiability component of the product: hashing an `EvidencePackage` and
submitting it via a provider-agnostic `Anchoring Provider` so that a third party can independently
verify evidence integrity, without that third party needing to trust JuriSense's own database. See
`docs/00-project/overview.md`, "Why blockchain makes sense here," and `ADR-007`.

## User

*Entity, context: Identity & Organizations.* An authenticated individual, globally unique by email, who
may hold `Membership`s in more than one `Organization`. See `docs/03-domain/domain-model.md`.
