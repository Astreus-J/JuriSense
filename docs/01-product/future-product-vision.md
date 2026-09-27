# Future Product Vision

JuriSense Gate is the first commercial product built on the JuriSense platform — a compliance
decision engine for the specific moment a supplier and contract need an `APPROVE/REVIEW/BLOCK`
answer. It is not, however, the ceiling of what the underlying platform (Supplier Intelligence,
Contract Intelligence, Policy Engine, Compliance Engine, Approvals, Evidence/Audit, AI Services,
Integrations — `docs/03-domain/domain-model.md`'s 8 bounded contexts) can support. This document
describes the product family beyond Gate: what each future product adds, why it is a natural
extension of the same platform rather than a separate bet, and roughly where it sits relative to the
roadmap.

Roadmap grounding: `docs/00-project/overview.md` describes twelve phases from Foundation through
International expansion, with an explicit **Hackathon Cut** after Phase 8 (Evidence/Audit + a
working blockchain anchor) — that is JuriSense Gate's minimum viable, demonstrable form. Phases 9–11
are the post-hackathon path toward international/enterprise expansion of Gate itself. Everything in
this document is sequenced **beyond Phase 11** — it assumes JuriSense Gate is already a commercially
validated product with real customers and real usage data before any of these extensions is a
priority worth building, consistent with the guiding question stated in `docs/00-project/
overview.md`: *"If the hackathon ended tomorrow, would it still be worth building this as a
company?"* Each of the products below only clears that bar once Gate itself has proven the core loop
works for paying customers.

---

## JuriSense Monitor — continuous supplier monitoring

**What it adds beyond Gate**: Gate evaluates a supplier at the moments a `SupplierCheck` is
triggered — on registration and on manual/scheduled re-check (`docs/01-product/use-cases.md`, UC-2).
Monitor turns that point-in-time check into a continuous, always-on watch: automatic re-checks the
moment an external source's data changes (a new sanctions-list entry, a registry status change, an
adverse news signal), rather than waiting for the organization to think to ask again. It converts
supplier risk from "we checked when we onboarded them" to "we would know within hours if their
status changed."

**Why it's a natural extension**: the `Supplier`, `SupplierProfile`, and `SupplierCheck` domain
model (`docs/03-domain/domain-model.md`) already supports an unlimited number of checks per
supplier over time — Monitor is substantially a scheduling, change-detection, and alerting layer on
top of infrastructure Gate already has, not a new domain model. The `compliance.review_required`
re-evaluation trigger (`BR-DEC-004`) that Gate already uses when a `PolicyVersion`/`ContractVersion`
changes is the same mechanical pattern Monitor would use when a supplier's external status changes.

**Rough sequencing**: a logical first extension beyond Gate, since it deepens the existing Suppliers
bounded context rather than opening a new one — plausible as the first post-Gate product investment
once a customer base exists whose supplier portfolios are large/dynamic enough that periodic manual
re-checks (Gate's current model) leave a meaningful gap.

---

## JuriSense Contracts — deeper contract intelligence

**What it adds beyond Gate**: Gate's Contract Intelligence is deliberately scoped to what a
compliance gate needs — structured extraction sufficient to evaluate policy rules against
(`docs/01-product/product-definition.md` explicitly states Gate is not a CLM replacement). Contracts
would extend this into full contract lifecycle intelligence: clause-library benchmarking against a
market corpus ("is this liability cap typical for a contract this size in this industry"),
obligation tracking and deadline reminders across the contract's active life (not just at signature),
renewal/termination playbooks, and natural-language contract search across the entire portfolio.

**Why it's a natural extension**: the `ContractVersion`/`Clause` structured-extraction pipeline
(`docs/03-domain/domain-model.md`, `docs/05-ai/structured-extraction.md`) that Gate already runs on
every contract is exactly the data substrate this deeper intelligence would be built on — Contracts
does not need a new ingestion or extraction pipeline, it needs more analysis and more surfaces built
on the same extracted data Gate already produces and stores.

**Rough sequencing**: a natural second or parallel extension to Monitor, since it deepens the
Contracts & Documents bounded context. Most credible once enough contracts have flowed through Gate
to make benchmarking/corpus-style features (which need volume to be useful) actually valuable rather
than sparse.

---

## JuriSense Policies — standalone policy management

**What it adds beyond Gate**: in Gate, the Policy Engine is a component of the compliance pipeline —
policies exist to be evaluated against contracts. Policies would offer the rule-authoring, versioning,
simulation, and exception-management capabilities (`docs/03-domain/policy-engine.md`) as a
standalone governance product usable even for organizations or use cases that don't route through
Gate's full supplier/contract pipeline — e.g., internal policy governance for domains adjacent to
vendor compliance (expense policy, access-control policy, any domain expressible as versioned
`when/then` rules against a normalized evaluation context).

**Why it's a natural extension**: the Policy & Compliance bounded context's DSL, versioning model,
and simulation capability (`ADR-004`, `docs/03-domain/policy-engine.md`) are already
domain-agnostic by construction — nothing about the rule engine itself is Gate-specific; only the
particular rules Gate ships with (sanctions, LGPD, liability, financial thresholds) are
vendor-compliance-flavored. Decoupling the engine from the vendor-compliance evaluation context is
primarily a product-packaging exercise, not a rebuild.

**Rough sequencing**: a more speculative, platform-play extension than Monitor or Contracts — most
credible once JuriSense has established enough trust and brand recognition in the policy-as-code/
compliance-automation space that customers would consider adopting the engine independent of the
Gate use case that originally proved it out.

---

## JuriSense Privacy — privacy compliance

**What it adds beyond Gate**: Gate's privacy-relevant capability is narrow and specific — flagging
whether a given contract processes personal data and whether a DPA is present (`LGPD-001`), evaluated
per-contract as part of the compliance gate. Privacy would build this into a standalone privacy
compliance product: a full record of processing activities (ROPA)-equivalent register across all
vendors (not just ones currently under active contract review), data subject request handling
workflows, LGPD/GDPR-pack compliance checklists and assessments, and privacy-impact-assessment
tooling — the broader privacy-program surface a dedicated Privacy Officer/DPO needs beyond
vendor-contract gating.

**Why it's a natural extension**: the personal-data-processing fields already normalized into every
`ComplianceReview`'s evaluation context (`contract.processes_personal_data`, `contract.dpa_present`,
`docs/03-domain/policy-engine.md`) are the seed of exactly the vendor-processing register a full
privacy-compliance product needs to maintain — Privacy would extend data the platform already
collects into a purpose-built surface for the Privacy Officer persona (`docs/01-product/
personas.md`), rather than starting that data collection from zero.

**Rough sequencing**: plausible in parallel with Monitor/Contracts, driven less by technical
readiness and more by market signal — worth prioritizing earlier than its "natural" position in this
list if early Gate customers' Privacy Officers specifically ask for more than the DPA-presence flag
Gate ships with.

---

## JuriSense Risk — broader third-party risk

**What it adds beyond Gate**: Gate's risk classification (`docs/03-domain/domain-model.md`'s `Risk`
entity, UC-7) is scoped to what a `ComplianceReview` surfaces for a specific supplier/contract pair.
Risk would broaden this into full Third-Party Risk Management (TPRM): security questionnaire
automation, vendor risk scoring across dimensions beyond what a single contract review captures
(financial health/creditworthiness signals, operational resilience, concentration risk across the
vendor portfolio), and continuous risk-tiering independent of any single contract event — the
category `docs/00-project/overview.md`'s "Market" section identifies as the closest real-world
comparison (Vanta/Drata/OneTrust-adjacent, though Gate itself is explicitly narrower than that
category today, per `docs/01-product/product-definition.md`).

**Why it's a natural extension**: Gate's `Risk` entity and severity model already establish the
vocabulary (`category`, `description`, `severity`, `evidence_refs`) a broader TPRM risk-scoring
product would extend; the Suppliers bounded context's `SupplierProfile`/`SupplierCheck` history is
also the natural data foundation for a portfolio-wide risk-tiering view.

**Rough sequencing**: the most ambitious, market-repositioning extension in this list — it moves
JuriSense meaningfully closer to competing directly in the TPRM/GRC category rather than the
narrower compliance-gate niche Gate occupies today. Credible only once JuriSense has real
competitive standing and a customer base large enough to justify the broader (and more
crowded/competitive) TPRM market, not before.

---

## JuriSense Audit — audit/evidence tooling

**What it adds beyond Gate**: Gate's Evidence & Audit capability produces a Decision Passport and
audit trail per decision, in service of Gate's own compliance pipeline. Audit would generalize this
into a standalone audit/evidence toolkit: audit-program management (scheduling and tracking internal/
external audits, not just storing evidence for ad hoc requests), evidence-request workflows for
responding to a customer's or regulator's due-diligence questionnaire, and a broader "evidence
locker" that can hold and hash-anchor evidence types beyond compliance decisions specifically (e.g.,
SOC 2 control evidence, security-attestation documents).

**Why it's a natural extension**: the `EvidencePackage`/`Evidence`/`BlockchainAnchor` model and the
provider-agnostic `AnchoringProvider` interface (`ADR-007`) are already general-purpose — "hash a
bundle of evidence, anchor it, expose a public verification page" is not inherently
compliance-decision-specific, and the technical foundation (Merkle-root computation, anchoring,
public verification, `docs/06-blockchain/verification.md`) generalizes directly to any evidence type
an organization wants tamper-evident proof for.

**Rough sequencing**: a strong technical fit for extension at any point after the Hackathon Cut,
since the underlying anchoring infrastructure is largely built for Gate already — the limiting factor
is product/market validation that a standalone evidence-tooling product (as opposed to a Gate
feature) is something customers would buy independently, which is a commercial question more than a
technical one.

---

## JuriSense API — developer platform

**What it adds beyond Gate**: Gate today exposes a defined set of outbound webhooks (`INT-002`) for
key lifecycle events, primarily for the organization's own integration needs. API would open the
platform as a genuine developer platform: a public, documented, versioned API surface for suppliers,
contracts, policy evaluation, and evidence retrieval; the ability for a third-party developer or
partner (e.g., a CLM vendor, an ERP provider, a systems integrator serving JuriSense's target
customer segment) to build on top of JuriSense Gate's compliance engine rather than JuriSense
building every integration itself; and, potentially, a marketplace-style ecosystem of
jurisdiction-pack or policy-template contributions from partners.

**Why it's a natural extension**: the `Integration` bounded context's boundary rule — external
systems never write directly to business-domain tables, always through application commands
(`docs/04-architecture/components.md`) — is exactly the discipline a safe public API needs; API
mostly generalizes and hardens an integration surface the platform's architecture already assumes
exists, rather than introducing a new architectural pattern.

**Rough sequencing**: the last product in this list to prioritize, by design — a public developer
platform is most valuable once JuriSense has enough of an ecosystem of partners/integrators wanting
to build on it that opening the platform pays off; opening a public API before that demand exists
mostly adds surface area (support burden, security exposure, versioning discipline) without
commensurate benefit. Most credible once JuriSense Contracts, Privacy, and/or Risk have created
enough adjacent-product surface area that third parties have a reason to integrate with more than
just Gate's core compliance-decision flow.

---

## Sequencing summary

None of the products above has a committed date — they are stated relative to each other and to the
Gate roadmap's Phase 11 horizon, not as a fixed schedule. The rough ordering of *plausibility*,
independent of market-driven reprioritization, is: **Monitor and Privacy** (smallest extension of
existing data/infrastructure, clearest incremental customer value) → **Contracts and Audit** (strong
technical fit, contingent on contract/evidence volume and commercial validation respectively) →
**Policies** (platform-packaging play, contingent on brand/trust maturity) → **Risk** (market-
repositioning play, contingent on competitive standing) → **API** (ecosystem play, contingent on
partner demand existing in the first place). Actual sequencing will be driven by what Gate's early
customers ask for most, not by this document's a priori technical-fit ordering — this list exists to
show the platform's extension surface is real and grounded in the architecture already being built
for Gate, not to lock in a multi-year product plan today.
