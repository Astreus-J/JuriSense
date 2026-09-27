# JuriSense — Product & Project Overview

> This document is the single entry point for anyone joining the project. It should be enough, on
> its own, to understand what JuriSense is, why it exists, how it works, and where it's going.

## What is JuriSense

**JuriSense** is an AI-powered Vendor, Contract & Compliance Operations Platform. It turns
contracts, supplier data, and company policies into auditable compliance decisions.

> Turn contracts, supplier data and company policies into auditable compliance decisions.

JuriSense is the company/platform brand. The first commercial product built on it is **JuriSense
Gate**.

## What is JuriSense Gate

JuriSense Gate is a B2B platform that automates the analysis and approval of suppliers and
contracts using AI, executable company policies, official data sources, approval workflows,
compliance and audit tooling, and a blockchain-based verifiability layer. It answers, in a
verifiable way, the question every company asks before signing:

> **"Can we hire this supplier and sign this contract?"**

with:

```
APPROVE / REVIEW / BLOCK
```

accompanied by **WHY, EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER, AUDIT TRAIL,
VERIFICATION** — never a bare status with no explanation.

## Problem

Companies contract suppliers, SaaS vendors, consultancies, outsourcing firms, developers, cloud
providers, and strategic partners continuously. Before any of these contracts is signed, a company
is supposed to check: registration/identity data, sanctions and restriction lists, compliance
posture, LGPD/data-processing exposure, security posture, SLA terms, liability caps, IP terms,
renewal/termination clauses, and internal approval requirements.

In practice, this process is split across **Procurement, Legal, Compliance, Finance, Security, and
Privacy** teams, coordinated over email and spreadsheets, with no single, reproducible record of
*why* a given supplier or contract was approved. Six months later, nobody can answer "why did we
approve this vendor's unlimited-liability clause?" with anything better than "someone probably
looked at it." That is a real audit, legal, and financial exposure — and it does not scale past a
handful of contracts per month.

JuriSense Gate replaces that fragmented, manual, unauditable process with a single automated and
traceable pipeline.

## Market

**Initial market: Brazil.** Target customer: technology companies with roughly **50–1,000
employees** that contract many SaaS vendors, consultancies, technology suppliers, cloud services,
outsourced staff, and marketing/professional service providers — i.e., companies with real
procurement volume but no dedicated TPRM (Third-Party Risk Management) tooling yet. See
`docs/02-business/brazil-market.md` for sizing and go-to-market detail.

**Category**: the closest real-world categories are Third-Party Risk Management (TPRM), GRC/
compliance automation (Vanta, Drata, OneTrust), and Contract Lifecycle Management / legal AI
(Ironclad, Harvey, Spellbook, Norm AI). No identified competitor combines Brazil-first supplier
compliance + contract intelligence + an executable policy engine + blockchain-backed evidence in one
product — see `docs/02-business/competitive-landscape.md` and `docs/02-business/differentiation.md`
for the full analysis and the explicit "current capability vs. long-term moat hypothesis"
distinction (this is a hypothesis to validate, not a claimed moat).

## Users

Procurement, Legal, Compliance, Privacy, Security, and Finance teams use the product day to day.
Likely buyers: Head of Procurement, General Counsel, Head of Compliance, CFO, COO, or a Procurement
Manager. See `docs/01-product/personas.md`.

## Product — how it works

```
Supplier
    ↓
Company verification (official sources)
    ↓
Documents / Contract ingestion
    ↓
AI structured extraction
    ↓
Company policies (Policy Engine)
    ↓
Compliance Engine
    ↓
Risk analysis
    ↓
APPROVE / REVIEW / BLOCK
    ↓
Human approval (when required)
    ↓
Decision Passport
    ↓
Audit Trail
    ↓
Blockchain verification (evidence anchoring)
```

### Supplier Intelligence
Registers and analyzes suppliers using official/public Brazilian sources where available
(company registry status, sanctions/restriction lists such as CEIS/CNEP/CEPIM, corporate structure)
plus internal history. See `docs/03-domain/supplier-compliance.md`.

### Contract Intelligence
Ingests contracts (PDF/DOCX/TXT) and produces **structured** output — not prose — covering parties,
value, duration, renewal/termination, liability, confidentiality, IP, data-processing/DPA terms,
jurisdiction, guarantees, penalties, obligations, deadlines, and clause-level citations back to the
source document. See `docs/03-domain/contract-compliance.md` and `docs/05-ai/structured-extraction.md`.

### Policy Engine
Lets a company turn internal policy into executable rules (`when <condition> then
APPROVE|REVIEW|BLOCK`, versioned, with a required approver role for non-auto-approve outcomes). See
`docs/03-domain/policy-engine.md` and `ADR-004`.

### Compliance Engine
Combines supplier data + contract data + AI analysis + deterministic policy rules into a final,
explainable decision, using the aggregation algorithm defined in `ADR-010`
(`docs/03-domain/policy-engine.md` has the full worked examples).

### AI
Used for interpretation, classification, extraction, and summarization — **never** to unilaterally
decide a compliance outcome. Every AI conclusion carries provenance (document/page/clause/
confidence). See `docs/05-ai/ai-strategy.md`.

### Workflow / Approvals
Risk-tiered approval routing (e.g., auto-approve on LOW risk; Legal review on MEDIUM; Compliance +
Legal + Director on HIGH), modeled as an explicit state machine (`ADR-006`). See
`docs/03-domain/approvals.md`.

### Decisions & Decision Passport
Every decision is packaged with: decision id, supplier, contract, document hashes, policies
evaluated (with version), rules triggered, external sources consulted, AI executions (model/prompt
version), reviewers, final decision, and timestamp — so "why was this approved?" is answerable
months or years later. See `docs/03-domain/evidence.md`.

### Audit
Every meaningful action emits an append-only audit event (catalog in `docs/03-domain/audit.md`).

### Blockchain / Trust Layer
Blockchain is used strictly as a **verification layer**, not as the product: only hashes of the
Evidence Package are anchored on-chain, never raw contract or personal data. See "Why blockchain
makes sense" and "Why blockchain is NOT the product" below, `docs/06-blockchain/*`, and `ADR-007`
for the provider-agnostic design.

### Privacy & Security
LGPD-first, tenant-isolated by design, no confidential data ever placed on-chain (only hashes/
commitments). See `docs/06-blockchain/privacy.md` and `docs/07-engineering/security.md`.

## Differential

The working hypothesis (to validate, not a settled claim — see
`docs/02-business/differentiation.md`) is a Brazil-first compliance data layer combined with
supplier + contract intelligence, an executable policy engine, AI, auditable decision workflows,
and a blockchain trust layer, in one product, for a market segment (50–1,000-employee tech
companies) that today stitches this together manually or not at all.

## Brazil strategy

Brazil is the first market by design, not an architectural ceiling: LGPD compliance, CNPJ-based
supplier identity, and Brazilian sanctions/registry sources are first-class from day one (see
`docs/02-business/brazil-market.md`), while the domain model and Policy Engine are built so that
jurisdiction-specific logic is swappable (see "Internationalization" below and
`docs/02-business/international-market.md`).

## Internationalization

The architecture separates a **Core Platform** from **Jurisdiction Packs** (Brazil Pack today;
US/EU/UK/LATAM packs are future work) — see `docs/04-architecture/architecture-overview.md` and
`docs/02-business/international-market.md`. Jurisdiction-specific rules (LGPD/CNPJ/CEIS/CNEP today;
GDPR/EU sanctions, OFAC/SEC, etc. in the future) live in Policy Engine rule packs and Supplier
Intelligence source adapters, not hardcoded into the core domain model.

## Business model

SaaS subscription with usage-sensitive limits (suppliers analyzed, contracts reviewed, AI
executions), moving toward per-review/usage-based and enterprise contracts as the product matures.
See `docs/02-business/business-model.md` and `docs/02-business/pricing-strategy.md` for the full
analysis, hypotheses, and explicit TBDs (exact price points require customer discovery and are not
invented here).

## Why this product makes sense

The underlying workflow (verify supplier → review contract → check against policy → approve/
block → keep evidence) already happens in every company that buys from outside vendors — today
manually, slowly, and unauditably. Automating it is a productivity and risk-reduction play with a
measurable cost baseline (see `docs/02-business/business-case.md`).

## Why companies would pay

Faster procurement cycles, fewer missed compliance red flags (unlimited liability, missing DPA,
auto-renewal traps), and — critically for regulated or enterprise-adjacent buyers — a defensible,
reproducible audit trail when a regulator, auditor, or acquirer asks "why was this vendor
approved?" See `docs/02-business/business-case.md` for the detailed value/ROI argument and named
objections.

## Why AI makes sense here

Reading and structuring contracts and supplier documents at the volume a growing company generates
is exactly the kind of interpretation/extraction task LLMs are good at — and exactly the kind of
task that is too slow and inconsistent for a human to do for every single vendor. AI here is an
**extraction and drafting-support** engine, not a decision-maker (see `docs/05-ai/ai-strategy.md`).

## Why blockchain makes sense here

The product's core promise is *auditability that survives time and organizational memory loss*.
A hash of the Evidence Package anchored on a public, tamper-evident ledger gives a verifiable,
third-party-checkable answer to "was this evidence altered after the fact?" — something a purely
internal database log cannot prove to an external auditor or counterparty. See
`docs/06-blockchain/blockchain-purpose.md`.

## Why blockchain is NOT the product

JuriSense Gate is not a token, NFT, DAO, or cryptocurrency play, and no confidential document or
personal data is ever written on-chain — only hashes/commitments of evidence packages (see
`docs/06-blockchain/privacy.md`). The product's value is the compliance automation and decision
workflow; blockchain is one verifiability component within it, swappable behind the
`AnchoringProvider` interface (`ADR-007`), not the reason a customer buys.

## Commercial strategy

Land technology companies in Brazil with real procurement volume and no TPRM tooling today (see
`docs/02-business/go-to-market.md`), using the hackathon submission as the first public proof point,
then expand toward larger/regulated buyers and international jurisdiction packs.

## Technology strategy

Python/FastAPI modular monolith (`ADR-001`, `ADR-002`), reused and renamed `Accounts` context as
`Identity & Organizations`, CEL/JSONLogic-based Policy Engine (`ADR-004`), multi-provider AI gateway
(`ADR-005`), Celery for async tasks with a DB-backed state machine for approvals (`ADR-006`), an
anchoring-provider-agnostic Trust Layer (`ADR-007`), S3-compatible storage (`ADR-008`), and
PostgreSQL+pgvector for retrieval (`ADR-009`). Full detail in `docs/04-architecture/` and
`docs/07-engineering/technology-stack.md`.

## Roadmap (summary)

Twelve phases from Foundation through International expansion, with an explicit **Hackathon Cut**
after Phase 8 (Evidence/Audit + a working blockchain anchor). Full detail, with objectives,
deliverables, dependencies, exit criteria, and risks per phase, in `docs/09-planning/roadmap.md`.

## Hackathon

JuriSense Gate is being built for **BLI Legal Tech Hackathon 2 / Legal Hack 2026** (judging
2026-11-05 to 2026-12-05, awards 2026-12-12; sponsors ICP/Caffeine AI, Constellation Network, Story
Protocol) as the first public milestone of a real commercial product — not a disposable demo. Full
strategy in `docs/08-hackathon/`.

## Long-term vision

Beyond JuriSense Gate: continuous supplier monitoring (JuriSense Monitor), deeper contract
intelligence (JuriSense Contracts), standalone policy management (JuriSense Policies), privacy
compliance (JuriSense Privacy), broader third-party risk (JuriSense Risk), audit/evidence tooling
(JuriSense Audit), and an open developer platform (JuriSense API) — see
`docs/01-product/future-product-vision.md`. The guiding question for every feature, hackathon or
not: **"If the hackathon ended tomorrow, would it still be worth building this as a company?"**
