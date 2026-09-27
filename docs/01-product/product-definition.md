# Product Definition

## What JuriSense Gate is

JuriSense Gate is a B2B **Vendor, Contract & Compliance Operations Platform**. It is the first
commercial product built on the JuriSense platform, and it answers one operational question that
every company with a procurement pipeline asks before money and legal exposure change hands:

> **"Can we hire this supplier and sign this contract?"**

It answers that question the same way every time, for every supplier and every contract, with:

```
APPROVE / REVIEW / BLOCK
```

— always accompanied by **WHY, EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER, AUDIT
TRAIL, VERIFICATION**. A bare status with no explanation is treated as a product defect, not an
acceptable output shape; every one of the nine elements above must be attachable to every decision
the system produces, or the decision is not considered complete.

Concretely, JuriSense Gate is:

1. **A supplier intelligence layer.** It registers suppliers, checks them against official and
   public sources (company registry status, sanctions/restriction lists, corporate structure), and
   keeps an immutable, timestamped history of every check — see `docs/03-domain/supplier-
   compliance.md`.
2. **A contract intelligence layer.** It ingests contracts (PDF/DOCX/TXT) and turns them into
   structured, citable data — parties, value, duration, liability, DPA/data-processing terms,
   IP, jurisdiction, penalties, obligations — never prose summaries standing in for the source text.
   See `docs/03-domain/contract-compliance.md` and `docs/05-ai/structured-extraction.md`.
3. **An executable policy engine.** It lets a company encode its own internal policy as versioned,
   deterministic rules (`when <condition> then APPROVE|REVIEW|BLOCK`), so the rules that govern a
   decision are the company's own, not a black-box model's judgment. See `docs/03-domain/policy-
   engine.md` and `ADR-004`.
4. **A compliance and risk decision engine.** It combines supplier evidence, contract evidence, and
   policy rules into one explainable, reproducible decision per the aggregation algorithm in
   `ADR-010` (any `BLOCK` wins, else any `REVIEW` wins, else `APPROVE`).
5. **A human approval workflow.** Every `REVIEW` outcome is routed to a named role
   (Legal/Compliance/Director/etc.) through an explicit, auditable state machine — never a silent
   auto-resolution. See `ADR-006` and `docs/03-domain/approvals.md`.
6. **An evidence and audit system.** Every decision is packaged into a Decision Passport — the
   policy version used, every rule evaluated, every source consulted, every reviewer involved — and
   every state-changing action in the system emits an append-only audit event. See
   `docs/03-domain/evidence.md` and `docs/03-domain/audit.md`.
7. **A blockchain-anchored verification layer.** The hash of each Decision Passport's Evidence
   Package is anchored on a public, tamper-evident ledger through a provider-agnostic
   `AnchoringProvider` interface (`ADR-007`), so "was this evidence altered after the fact?" has an
   answer that does not depend on trusting JuriSense's own database.

## Core promise

**Every compliance decision JuriSense Gate produces is explainable at the moment it is made and
verifiable years later, without depending on anyone's memory of what happened.** That promise has
two halves that must both hold: explainability now (a Procurement Manager or auditor can read WHY,
EVIDENCE, POLICY, SOURCE, RISK directly off the decision, in plain language, with citations back to
the source document or source list) and verifiability later (an external party — an auditor, a
regulator, an acquirer's due-diligence team — can independently confirm the recorded evidence has
not been altered since the decision was made, via the public verification page, without needing
privileged access to JuriSense's systems).

## What JuriSense Gate is NOT

Stating the boundary explicitly, because each of these is an adjacent category a reader might
reasonably (and incorrectly) assume the product also is:

- **It is not an ERP.** JuriSense Gate does not manage purchase orders, invoicing, inventory,
  general ledger, HR, or any of the operational/financial record-keeping an ERP owns. It consumes
  supplier and contract facts to make a compliance decision; it does not run the company's back
  office. Where an ERP integration exists, it is a data source into JuriSense Gate
  (`docs/03-domain/domain-model.md`'s `Integration` entity), never the other way around.
- **It is not a Contract Lifecycle Management (CLM) replacement.** JuriSense Gate does not do
  contract drafting, redlining/negotiation tooling, e-signature, clause-library management, or
  contract repository/search as a general-purpose function. It ingests a contract that already
  exists (in any state of the negotiation) to extract structured data and evaluate it for
  compliance risk. A company's CLM tool (or a folder of PDFs) remains the system of record for the
  negotiation itself; JuriSense Gate is the compliance gate the contract passes through, not the
  tool used to write it. (Deeper contract intelligence beyond this compliance-gate scope is a
  distinct, later product — see `docs/01-product/future-product-vision.md`, JuriSense Contracts.)
- **It is not a law firm tool or a legal research platform.** It does not provide legal research,
  case law search, litigation support, or legal drafting services, and it is not built for law
  firms to serve their clients. It is built for the operating company itself (Procurement, Legal,
  Compliance, Privacy, Security, Finance functions inside a technology company) to manage its own
  third-party risk.
- **It is not a token, NFT, DAO, or cryptocurrency project.** The blockchain component exists
  exclusively to anchor hashes of evidence packages for tamper-evidence; JuriSense Gate has no
  token, no on-chain governance, and no crypto-asset economics of any kind. No confidential
  document content or personal data is ever written on-chain — only hashes/commitments (`BR-EVD-
  002`, `docs/06-blockchain/privacy.md`). A customer's procurement/compliance buyer never needs to
  understand or hold cryptocurrency to use the product.
- **It is not a generic e-signature or workflow-automation tool.** Approval routing exists strictly
  to resolve a compliance `REVIEW` outcome (`ADR-006`); it is not a general-purpose BPM/workflow
  builder for unrelated business processes.
- **It is not a general-purpose GRC suite out of the box.** It targets vendor/supplier and contract
  compliance specifically. Categories like SOC 2 readiness automation, security questionnaire
  automation, or continuous control monitoring across a company's own infrastructure (the space
  Vanta/Drata occupy) are adjacent, not covered, by the Gate product (see `docs/02-business/
  competitive-landscape.md` for the category comparison).

## Boundary of responsibility: decision support, not legal advice

This is the single most important limitation to state without hedging, and it applies to every
persona and every use case in this platform:

> **JuriSense Gate provides decision support, compliance automation, and structured human review.
> It never provides legal advice, and its output is never a substitute for the judgment of the
> customer's own qualified legal counsel.**

What this means in practice:

- The AI layer (`AI Services` bounded context) extracts, classifies, and summarizes — it produces
  structured facts and cites where each fact came from. It never characterizes a clause as
  "acceptable" or "safe" in a legal sense; it reports what the clause says and flags it against the
  customer's own policy rules. `AI-004` (`docs/01-product/functional-requirements.md`) makes this a
  hard technical constraint: AI Services output can never directly set a `Decision` status.
- The Policy Engine evaluates the customer's **own** rules, authored and owned by the customer's
  own Legal/Compliance/Procurement staff. JuriSense does not write, endorse, or warrant that any
  shipped rule template constitutes sound legal policy for a given company, industry, or
  jurisdiction — rule templates are starting points, not legal opinions, and the customer's Legal
  function is responsible for reviewing and approving every rule before it goes live (see
  `docs/03-domain/policy-engine.md`).
- Every `REVIEW` outcome routes to a **human** with the matching role (`ADR-006`, `BR-APR-001`).
  The system never resolves a `REVIEW` by itself; a person with legal/compliance authority in the
  customer's organization always makes the final call on anything the deterministic rules did not
  auto-approve.
- `APPROVE` outcomes are auto-resolved only when **every** applicable rule the customer itself
  configured evaluates to `PASS` (`ADR-010`). This is the customer's own policy operating
  automatically at machine speed — it is not JuriSense independently vouching for the supplier or
  contract's legal soundness.
- The Decision Passport and audit trail exist to make the customer's own decision process
  reproducible and defensible — they document what happened and why, under the rules the customer
  set. They are not, and are never marketed as, a legal opinion, a compliance certification, or a
  warranty that a contract or supplier relationship is free of legal risk.
- Nothing in JuriSense Gate creates an attorney-client relationship, and no output should be
  presented to a regulator, court, or counterparty as legal advice from JuriSense. Customers remain
  responsible for maintaining their own legal counsel relationship for matters requiring actual
  legal judgment (contract negotiation strategy, litigation risk assessment, regulatory
  interpretation in novel situations, etc.).

Status: TBD / Current preferred option: this limitation is stated in the Terms of Service and
repeated as persistent, non-dismissible UI copy on every decision output screen / Why undecided:
exact legal disclaimer language requires review by outside counsel before the product is generally
available / Resolution: legal review of ToS and in-product disclaimer copy before GA / Decision
artifact: `docs/02-business/legal-and-compliance-posture.md` (to be created).

## Why this boundary matters commercially

A platform that overstated its own authority ("JuriSense approved this vendor" instead of "this
vendor passed every rule your Legal team configured") would be both a legal liability for JuriSense
and a weaker product for the customer — it would let the customer's own Legal/Compliance function
under-invest in owning their policy, which is precisely the muscle this product is meant to
strengthen, not replace. The product's differentiation (`docs/00-project/overview.md`,
"Differential") is being the **execution layer** for a company's own compliance judgment, not a
replacement for that judgment.
