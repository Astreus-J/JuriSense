# Expansion Strategy

> How the JuriSense product line expands commercially from JuriSense Gate outward to the future
> modules — Monitor, Contracts, Policies, Privacy, Risk, Audit, API. This document covers business
> sequencing and commercial logic: *why* each module makes sense as the next move and in what order.
> The product-side definition of each module lives in
> `docs/01-product/future-product-vision.md` (owned by another writer on this documentation effort);
> this document should be read as its commercial complement, not a duplicate.

## The sequencing principle

Every expansion module should satisfy the same test named in `docs/00-project/overview.md`'s closing
question: *"if the hackathon ended tomorrow, would it still be worth building this as a company?"*
Applied to sequencing specifically, that becomes: **each module should be justified by demand signals
already visible from JuriSense Gate's existing customers, not by a general roadmap ambition.** This
document orders modules by how directly they extend the trust and workflow relationship JuriSense
Gate already has with a customer — expansion should feel like the natural next question the customer
themselves would ask, not a separate product being cross-sold.

## Why expand from Gate at all, commercially

JuriSense Gate's core transaction is a point-in-time decision: verify this supplier, review this
contract, decide approve/review/block, keep the evidence. Once a customer has trusted that decision
loop with real vendor/contract volume (the usage that also calibrates `pricing-strategy.md`'s TBD
limits), several adjacent needs become visible that Gate does not address by design — what happens to
a supplier's risk profile *after* approval, what happens as more of the company's contract corpus
needs deeper structured management, whether the policy layer itself becomes valuable as a standalone
governance tool, and so on. Commercially, this is the textbook expansion-revenue pattern
(land-and-expand within an existing trusted account is materially cheaper than new-logo acquisition),
and it is *available* to JuriSense specifically because Gate's evidence/audit foundation
(`docs/03-domain/domain-model.md`) is built to be extended, not bolted onto later.

## Recommended sequencing and the commercial logic for each

### 1. JuriSense Monitor (continuous supplier monitoring) — first expansion

**Commercial logic for going first**: Gate's `SupplierCheck` is a point-in-time verification
(`docs/03-domain/domain-model.md`) — but the risk it addresses (a supplier's sanctions status,
registration status, or corporate structure changing) does not stay fixed after approval. The moment a
customer has approved a meaningful supplier base through Gate, "what if their status changes after we
approved them?" becomes an obvious, self-generated question from the customer, not a manufactured
upsell pitch — this is the most natural, lowest-resistance expansion because it extends the exact same
data model (`SupplierProfile`/`SupplierCheck`) the customer already trusts, just adding a time
dimension. It is also a strong fit for the usage-sensitive pricing logic in `business-model.md`: ongoing
monitoring is naturally metered (per supplier monitored per period), giving a clean second revenue line
without a new pricing paradigm.

**Why not first overall (i.e., why not build alongside Gate)**: monitoring only has value once there is
an approved supplier base *to* monitor — building it before Gate has real customers with real supplier
lists would be monitoring nothing.

### 2. JuriSense Contracts (deeper contract intelligence) — second expansion

**Commercial logic**: Gate's contract intelligence produces structured extraction sufficient to drive
a compliance decision (`ContractVersion.extracted_data`, `Clause` — `docs/03-domain/domain-model.md`),
but a customer with a large, growing contract corpus will naturally want more: contract search across
the full portfolio, obligation tracking beyond the compliance-decision moment (e.g., renewal-date
alerting independent of a new compliance review), and cross-contract analytics ("show me every
contract with an auto-renewal clause and less than 60 days notice"). This is a direct upsell within the
same buying relationship (the same Legal/Procurement users already in the product daily), and it is the
module most likely to bring JuriSense into competitive contact with Ironclad-style CLM
(`competitive-landscape.md`) — a deliberate, sequenced move only after Gate + Monitor have established
the trust and data foundation to make that comparison favorable, not before.

**Why second, not first**: it requires a larger contract corpus already ingested through Gate to be
valuable, and competing on contract-management breadth before establishing the compliance-decision
differentiation risks diluting the product's initial sharp positioning (`differentiation.md`'s warning
against chasing CLM breadth prematurely).

### 3. JuriSense Policies (standalone policy management) — third expansion

**Commercial logic**: as a customer's Policy Engine usage matures (multiple policies per
`pricing-strategy.md`'s Business/Growth tiers), the policy-authoring and governance experience itself
becomes a distinct value center — versioning, approval workflows for policy *changes* themselves,
cross-policy consistency checks, and policy-template libraries potentially informed by the
policy-pack network-effect hypothesis (`differentiation.md`). This is a natural narrow-and-deepen move:
customers who have invested real effort authoring policies want more sophisticated tools for
maintaining them, not just executing them.

**Why third, not earlier**: standalone policy management is a governance tool that only matters once a
customer has enough policy complexity (multiple policies, frequent revisions) to need it — Starter and
even Business-tier customers using one or two policies (`pricing-strategy.md`) would not yet feel this
need.

### 4. JuriSense Privacy (privacy compliance) — fourth expansion

**Commercial logic**: Gate already touches LGPD/data-processing exposure as one dimension of contract
review (`docs/00-project/overview.md`), but a dedicated Privacy module (broader data-mapping,
consent-adjacent tracking, DPA-lifecycle management beyond the vendor-approval moment) is the module
that most directly extends toward OneTrust's territory (`competitive-landscape.md`). Building it as an
expansion — after Gate has established trust and after the Brazil Jurisdiction Pack's LGPD logic has
been proven in production — is commercially safer than launching it as a standalone competitor to
OneTrust from day one, since it can be positioned to existing customers as "the privacy depth you
already trusted us with in Gate, extended," not a cold pitch against an entrenched incumbent.

**Why fourth, not earlier**: this is the module most likely to require the heaviest new
regulatory/compliance domain investment (real privacy-office-grade functionality, not just a
vendor-approval-scoped check) — sequencing it after the lower-lift Monitor/Contracts/Policies
expansions lets the company build that investment on a larger, already-monetizing customer base.

### 5. JuriSense Risk (broader third-party risk) — fifth expansion

**Commercial logic**: this is the module that most directly generalizes Gate's supplier-risk logic
beyond vendor/contract approval into broader enterprise risk management (operational risk, concentration
risk across the supplier portfolio, risk-trend reporting for board/executive audiences). It is a
natural upmarket move, well-suited to the Growth/Enterprise tier buyer (`pricing-strategy.md`) who
wants portfolio-level risk visibility, not just per-decision compliance gates.

**Why fifth, not earlier**: broader risk management is a more strategic, executive-facing sell
(COO/CFO-level portfolio risk reporting) that is credible only once JuriSense has enough real
decision/evidence data across a customer's supplier base (fed by Gate + Monitor + Contracts) to produce
meaningful portfolio-level risk insight — building it earlier would mean reporting on a data set too
thin to be useful.

### 6. JuriSense Audit (standalone audit/evidence tooling) — sixth expansion

**Commercial logic**: Gate's Evidence & Audit layer (`EvidencePackage`, `AuditEvent`,
`BlockchainAnchor` — `docs/03-domain/domain-model.md`) is built into the core product from the start,
not deferred — but a *standalone* Audit module (dedicated auditor-facing views, exportable
audit-readiness reports, cross-module audit aggregation once Monitor/Contracts/Policies/Privacy/Risk
all exist) becomes commercially distinct once a customer has enough breadth of JuriSense usage that a
unified, cross-module audit view has value beyond what any single module's built-in evidence trail
already provides.

**Why sixth, not earlier**: standalone audit tooling's value is proportional to how much of the
JuriSense product surface a customer actually uses — it is the aggregation layer *across* the other
modules, so it logically follows most of them rather than preceding them.

### 7. JuriSense API (open developer platform) — final expansion

**Commercial logic**: this is deliberately last, matching `business-model.md`'s explicit deferral of
API-usage pricing and `pricing-strategy.md`'s decision to gate API access behind the Growth tier. An
open developer platform only makes commercial sense once (a) enough customers have the internal
engineering capacity to build against it (a Growth/Enterprise-tier characteristic, not a Starter/
Business one), and (b) enough of the product surface (Gate + the modules above) exists to make an API
genuinely valuable to integrate, rather than exposing an immature or narrow product via API too early.
This is also the module most directly enabling the marketplace/partner-ecosystem business model named
as explicitly deferred in `business-model.md` — API-first distribution is the prerequisite for that
later-stage model, not a parallel effort.

**Why last**: of every module named here, this is the one most dependent on *all* the others already
existing and being proven — an API is only as valuable as the product behind it, and building it first
would mean exposing a thin, unproven product to external developers before the core workflow has
earned that trust.

## Cross-cutting commercial principles for every expansion module

- **Land-and-expand, not land-and-cross-sell.** Every module above should be pitched to *existing*
  JuriSense Gate customers first, using their own usage data and demonstrated trust in the core
  product, before (or instead of) being sold as a standalone product to new logos — consistent with
  `go-to-market.md`'s founder-led, trust-dependent sales logic.
- **Each module should have its own metering/pricing logic consistent with `business-model.md`'s
  hybrid framework**, not a bolted-on flat add-on fee — e.g., Monitor naturally meters by suppliers
  monitored per period, mirroring Gate's own usage-sensitive limit design.
- **International sequencing and module sequencing are independent axes.** A given Jurisdiction Pack
  (`international-market.md`) can, in principle, be built for Gate alone before any of the modules
  above exist — the two expansion dimensions (new modules vs. new jurisdictions) should be evaluated
  against separate demand signals, not conflated into one roadmap decision.
- **No module should be built ahead of demonstrated demand from the module immediately before it in
  this sequence.** The ordering above is a hypothesis about likely demand emergence, not a committed
  calendar roadmap — the actual trigger to begin building each module should be repeated, unprompted
  customer requests for that specific capability, observed during the Gate (and subsequent module)
  sales and success conversations described in `go-to-market.md`.
