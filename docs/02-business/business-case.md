# Business Case

> The economic argument for JuriSense Gate: what the manual process costs today, what changes with
> the product, who buys and why, the objections a seller will actually hear, and how the case
> extends after the first sale. Structural/qualitative reasoning is stated as real analysis; any bare
> number that would require live market research is marked `TBD` per the format below.

## The cost of the manual process today

Every target-segment company (50–1,000 employees, real procurement volume, no dedicated TPRM
tooling — see `docs/00-project/overview.md`) already runs this workflow. It is just unautomated,
uncoordinated across teams, and unrecorded. The cost shows up in four places:

### 1. Direct time cost

A single vendor/contract review today typically touches: a Procurement person who requests basic
company documents and negotiates terms; a Legal reviewer who reads the contract for liability, IP,
confidentiality, and termination terms; a Compliance/Privacy reviewer who checks LGPD/data-processing
exposure; and, for anything non-trivial, a Finance or Security sign-off. Each of those people spends
real hours — reading a contract closely, cross-checking clauses against internal policy from memory
or an outdated checklist, and going back and forth over email/Slack about what to flag. Multiply
that by the actual monthly volume of new vendors and contract renewals at a 50–1,000-employee tech
company (which routinely runs dozens of SaaS, cloud, consultancy, and outsourcing relationships,
each with periodic renewals) and the aggregate is a material, recurring labor cost that never shows
up as a line item because it is spread thinly across several people's "other duties."

- Status: TBD / Current preferred option: model illustrative benchmarks (e.g., "N hours per review ×
  blended hourly cost × reviews per month") once first customer interviews establish real numbers /
  Why undecided: exact hours-per-review and reviews-per-month vary too much by company size and
  contract complexity to state a credible number without primary research / Resolution: capture
  actual time-per-review data during the first 5–10 design-partner conversations (`go-to-market.md`)
  and build a simple ROI calculator from it / Decision artifact: a customer-discovery interview
  script + ROI calculator spreadsheet, not yet created.

### 2. Delay cost

Because the process is coordinated over email and spreadsheets with no shared state, a review
routinely stalls waiting on whichever person is currently the bottleneck (Legal is backlogged;
Compliance is on vacation; nobody remembers who has the latest version of the contract). Every day a
vendor approval is stuck is a day the business cannot start a project, cannot onboard a needed
supplier, or loses negotiating leverage because a deadline is closing in and the counterparty knows
it. This is a real, if hard-to-price-precisely, opportunity cost — procurement delay is a commonly
cited pain in every adjacent category (CLM vendors like Ironclad sell explicitly against contract
cycle-time), so the *structural* claim ("manual coordination adds meaningful cycle time") is safe to
state; the *magnitude* is not.

### 3. Risk cost of a missed red flag

This is the sharpest part of the case. A contract that slips through with an unlimited liability
clause, a missing or non-compliant Data Processing Agreement, an auto-renewal trap with an
unfavorable notice period, or a supplier that later turns out to be sanctioned or under investigation
is not a productivity problem — it is a financial and legal exposure that can dwarf years of
subscription cost in a single incident. The core issue named in `docs/00-project/overview.md` is
exact: "six months later, nobody can answer 'why did we approve this vendor's unlimited-liability
clause?' with anything better than 'someone probably looked at it.'" That is not just a bad outcome,
it is an *unauditable* bad outcome — the company cannot even demonstrate due diligence was
attempted, which is worse in front of a regulator, auditor, or acquirer than a documented mistake.

### 4. Auditability / institutional-memory cost

Even when the manual process works, its output (an email thread, a Slack decision, an approval
buried in someone's inbox) has no durable, reproducible record. When the person who approved a
vendor two years ago leaves the company, the "why" leaves with them. This is a cost that only
becomes visible at the worst possible moment: due diligence for a fundraise or acquisition, a
regulatory inquiry, or a dispute with the vendor itself.

## What changes with JuriSense Gate

- **Productivity gain**: supplier verification against official sources and contract clause
  extraction happen automatically in the pipeline (`docs/00-project/overview.md`'s
  Supplier→Verification→Ingestion→Extraction→Policy→Compliance→Risk→Decision flow) instead of via
  manual reading and manual cross-referencing against a checklist someone half-remembers. Human
  attention is reallocated to the reviews that actually need judgment (the `REVIEW`-tier decisions
  routed by risk, per `docs/03-domain/domain-model.md`'s `ApprovalWorkflow`), not spent re-deriving
  facts a machine can extract with citations.
- **Risk reduction**: the Policy Engine makes red-flag detection *systematic and non-optional* —
  every contract is checked against every published rule in the current `PolicyVersion`, every time,
  with no dependency on which human happened to remember to check for that specific clause that day
  (`docs/03-domain/policy-engine.md`, `BR-CMP-002`'s aggregation rule: any `BLOCK` anywhere wins).
  This converts risk detection from "depends on who reviewed it" to "depends on what the company's
  own published policy says," which is both more consistent and more defensible.
- **Time reduction**: cycle time drops because AI-assisted extraction and automatic policy evaluation
  happen in the time it takes to process a document, not in the time it takes six people to each find
  a slot in their week — and low-risk cases can auto-approve entirely, per the risk-tiered routing
  design (`docs/03-domain/domain-model.md` `ApprovalWorkflow`).
- **Auditability value**: this is the structurally strongest and most defensible part of the value
  proposition, because it does not depend on AI accuracy claims at all. Every `Decision` carries its
  exact `PolicyVersion`, every `RuleEvaluation` is append-only and immutable (`BR-CMP-003`), every
  `EvidencePackage` is independently hash-verifiable and optionally blockchain-anchored
  (`docs/00-project/overview.md`, `ADR-007`). "Why was this vendor approved?" becomes answerable
  from the system itself, months or years later, without depending on anyone's memory. This is a
  categorically different guarantee than "we have good internal notes."

## ROI framing (qualitative structure — exact figures are TBD)

The ROI argument has three legs, and only the third is genuinely hard to quantify without primary
research:

1. **Time saved × blended cost of the people currently doing manual review** — directionally large
   and easy for a buyer to estimate themselves once shown the workflow, but the exact multiplier is
   TBD (see above).
2. **Cycle-time compression × value of faster vendor onboarding / project starts** — real but
   company-specific; a company launching new vendor relationships tied to revenue-generating
   projects values this far more than one with a slow, low-stakes procurement cadence.
3. **Expected value of risk avoided** — the single largest potential number in the ROI case (one
   avoided unlimited-liability incident or one avoided regulatory finding can exceed years of
   subscription fees), but also the hardest to state as a clean number because it is a
   probability-weighted avoided-loss argument, not an observed cost.

- Status: TBD / Current preferred option: build a simple, transparent ROI calculator (hours saved +
  qualitative risk-avoidance framing, not a fabricated "expected incident cost" number) usable in
  sales conversations / Why undecided: risk-avoidance value requires either customer-specific loss
  history or actuarial-style data JuriSense does not have and should not fabricate / Resolution:
  co-develop the calculator's time-saved inputs with early design partners (`go-to-market.md`); leave
  risk-avoidance qualitative in early sales materials / Decision artifact: ROI calculator (not yet
  built).

## Who buys, who uses, why they'd buy

- **Economic buyers**: Head of Procurement, General Counsel, Head of Compliance, CFO, COO, or a
  Procurement Manager with budget authority (`docs/00-project/overview.md`). Different buyers care
  about different legs of the case: General Counsel and Head of Compliance are most moved by risk
  reduction and auditability; CFO/COO are most moved by cycle-time and headcount-efficiency framing;
  a Procurement Manager is most moved by day-to-day workflow relief.
- **Day-to-day users**: Procurement, Legal, Compliance, Privacy, Security, and Finance teams —
  meaning the sale has to satisfy both the person who owns the budget and the people who will
  actually run reviews inside the tool daily, which argues for a demo-heavy, workflow-transparent
  sales motion rather than a pure slide-deck pitch (see `go-to-market.md`).
- **Why they'd buy now, specifically**: this segment has "real procurement volume but no dedicated
  TPRM tooling" (`docs/00-project/overview.md`) — meaning the pain is already large enough to be
  felt, but the company has not yet made a category purchase decision (unlike, say, an enterprise
  that already has OneTrust). That makes them reachable with a category-defining pitch rather than a
  displacement pitch against an entrenched incumbent.

## Sales objections and rebuttals

**"We already have a spreadsheet process."**
Rebuttal: the spreadsheet is exactly the problem, not a competing solution — it records *that*
someone looked at something, not *why*, not against *which version* of company policy, and not with
any independent way to prove it wasn't edited after the fact. Ask directly: "if a regulator or
acquirer asked you to prove why vendor X was approved eighteen months ago, could your spreadsheet
answer that today?" This reframes the sale from "replace a tool" to "close a real audit gap they
already know they have."

**"Can we trust AI for this? What if it gets a clause wrong or approves something it shouldn't?"**
Rebuttal: this objection conflates two different things the product deliberately keeps separate.
AI is used strictly for interpretation, extraction, classification, and summarization — it never
unilaterally decides a compliance outcome (`docs/00-project/overview.md`, `docs/05-ai/ai-strategy.md`).
The actual `APPROVE/REVIEW/BLOCK` decision comes from deterministic, versioned, company-authored
policy rules (the Policy Engine) evaluated against normalized evidence (`BR-CMP-001`), not from an
LLM's judgment call. Every AI-derived fact carries a citation back to the source document/page/clause
with a confidence score (`docs/03-domain/domain-model.md`'s `Clause.confidence`), so a human reviewer
can verify rather than blindly trust. This is a materially different (and more defensible) claim than
"trust our AI's judgment" — it is "trust your own policy, applied consistently, with AI doing the
reading."

**"Why do we need blockchain? Sounds like a gimmick."**
Rebuttal: fair skepticism, and the product's own documentation takes the same position —
`docs/00-project/overview.md` explicitly states blockchain is a verification layer, not the product,
and is not a token/NFT/DAO play. The concrete claim is narrow and useful: only a hash (Merkle root)
of the Evidence Package is anchored on a public, tamper-evident ledger — never raw contract or
personal data (`ADR-007`, `BR-EVD-002`) — which gives a third party (an auditor, a counterparty, a
regulator) an independently checkable answer to "was this evidence altered after the fact?" that a
purely internal database log structurally cannot provide, because an internal log's own operator
could, in principle, edit it. Position it as one verifiability component inside the audit story, not
as the headline feature — if a prospect does not care about that specific guarantee, the sale does
not depend on convincing them to care.

**"We're too small / don't have enough vendors to justify this."**
Rebuttal: the target segment (50–1,000 employees) is defined precisely because it is *not* too small
— these companies already run dozens of concurrent vendor relationships with renewal cycles, which
is exactly the volume where a spreadsheet process starts silently failing. This objection is best
handled by asking the prospect to count their actual active SaaS/consultancy/cloud vendor list live
in the call; the number is almost always larger than the prospect's own mental estimate.

**"We'll just build a policy checklist ourselves / hire someone."**
Rebuttal: a checklist without enforcement, versioning, and evidence capture reproduces the exact
audit gap described above — a human-run checklist still depends on someone remembering to use it
correctly every time, and still leaves no independently verifiable trail. Hiring a person adds
headcount cost without adding the systematic, always-on-every-contract guarantee the Policy Engine
provides by construction (`BR-CMP-002`).

## Competitive angle (business-case framing)

The business case is strongest precisely where the named competitors are weakest for this segment:
Vanta/Drata are built for SOC2/ISO27001 evidence collection (a security-audit use case, not a live
supplier/contract approval workflow); OneTrust and Ironclad are enterprise-priced and enterprise-
implemented, a poor fit for a 50–1,000 employee company's budget and internal capacity; Harvey and
Spellbook are BigLaw/legal-drafting tools, not TPRM/procurement-workflow products; Norm AI is
agentic-compliance but not supplier/contract-specific nor Brazil-first. See
`competitive-landscape.md` for the full per-competitor breakdown — the business-case implication is
that none of them currently sell *this* buyer *this* workflow at *this* price point, which is why the
objection set above is about internal status quo ("we use a spreadsheet"), not about a named
competitor's product.

## Expansion logic (from the business case, not the product roadmap)

The same case that lands the first sale extends naturally in three directions, each covered in more
detail elsewhere: more usage from the same buyer as they trust the system with more of their vendor
base (the usage-sensitive plan limits in `business-model.md` capture this directly); more modules
from the same buyer as adjacent pain becomes visible (continuous monitoring, deeper contract
intelligence — `expansion-strategy.md`); and more buyers in adjacent segments once the audit-trail
story has real reference customers to point to (larger/regulated companies, then international
markets — `international-market.md`). The throughline in all three: every expansion is justified by
the same core mechanism (turning an unaudited manual judgment call into a reproducible, evidenced
decision), not by unrelated feature bolt-ons.
