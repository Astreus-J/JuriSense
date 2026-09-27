# Pricing Strategy

> Plan-tier hypothesis for JuriSense Gate. This document gives the *structure* — how tiers should
> differ and why — while treating exact price points and exact limit numbers as TBD, because they
> require customer discovery this team has not yet run. It builds directly on the hybrid model
> chosen in `business-model.md` (base SaaS subscription + usage-sensitive limits per `ADR-014`) and
> feeds the `Plan`/`Subscription` domain model in `docs/03-domain/domain-model.md`.

## Why a reasoned structure now, even with prices TBD

`ADR-014` requires `Plan`/`Subscription` limit enforcement (suppliers analyzed, contracts reviewed,
AI executions) to exist in the domain model before any real payment gateway is wired up. That means
the *shape* of the tiers — which dimensions gate which tier, and how they should scale relative to
each other — has to be decided now, even though the *numbers* inside that shape are appropriately
deferred to customer discovery. Getting the shape wrong (e.g., gating the wrong dimension, or making
tiers indistinguishable) would force a schema change later; getting the numbers wrong just means a
pricing-page edit.

## Tier hypothesis: Starter / Business / Growth / Enterprise

This four-tier structure mirrors the segment's natural size gradient (50–1,000 employees spans a
wide range of actual procurement volume) and gives a clear seat for both the smallest qualifying
company and the largest pre-enterprise buyer, with Enterprise as an explicit off-ramp to custom
contracts (`business-model.md`'s enterprise-contracts analysis).

### Starter

**Who it's for**: the smallest end of the target segment — a ~50–150 employee company running its
first systematic vendor-compliance process, likely a design-partner-era customer or a
self-serve/low-touch buyer testing the category for the first time.

**Design intent**: low commitment, fast time-to-value, deliberately capped low enough that a company
outgrowing it is a *positive* signal (real usage, real value realized) rather than a sign the tier
was mis-designed. This tier should feel complete for a light user, not artificially crippled — a
crippled free/entry tier undermines trust in a compliance product, where the buyer needs to believe
the tool works correctly, not that it's being deliberately hobbled to force an upgrade.

**Included dimensions** (qualitative — exact numbers TBD): a modest number of suppliers under active
management, a modest number of contract reviews per period, a limited number of AI executions per
period, a small number of user seats (enough for one Procurement + one Legal/Compliance user, the
minimum viable cross-functional pair), one policy (the org's core policy, not multiple parallel
policy sets), no API access, base storage, no SSO/advanced integrations.

### Business

**Who it's for**: the core of the target segment — a company with an established, recurring vendor
pipeline and more than one team actively using the product (Procurement + Legal + Compliance,
possibly Finance).

**Design intent**: this is the tier the business model should be optimized around, since it is where
most of the target segment (50–1,000 employees, "real procurement volume") should naturally land.
Limits should scale meaningfully above Starter on every dimension, and this tier should be the first
to unlock **multiple concurrent policies** (e.g., separate policy sets for different vendor
categories — software vendors vs. staffing/outsourcing vendors) since a company at this scale
typically has differentiated risk profiles across vendor types, not one uniform policy.

**Included dimensions** (qualitative): materially higher supplier/contract/AI-execution allowances
than Starter, more user seats, multiple policies, basic integrations (e.g., Slack/email notification
hooks — the kinds of `Integration` records already modeled in `docs/03-domain/domain-model.md`), no
API access yet, standard storage, priority support over Starter.

### Growth

**Who it's for**: the upper-mid segment — larger, more procurement-mature companies (approaching or
past the 500-employee mark) with higher usage, multiple business units, and a desire for more
automation and less manual review overhead (a higher proportion of auto-approved low-risk decisions).

**Design intent**: this tier should be where **workflow sophistication**, not just volume, becomes
the differentiator — more configurable `ApprovalWorkflow` routing (per
`docs/03-domain/domain-model.md`), higher AI-execution ceilings to support more automated (not just
higher-volume) review, and the first tier where **API access** becomes available (aligned with the
API-usage model being deferred in `business-model.md` until a segment exists that can actually use
it — Growth-tier companies are more likely to have the internal engineering capacity to integrate).

**Included dimensions** (qualitative): high supplier/contract/AI-execution allowances, more user
seats, unlimited or near-unlimited policies, integrations including early API access (rate-limited),
larger storage, faster support SLA.

### Enterprise

**Who it's for**: the largest and/or most regulated buyers — companies where SSO/security review,
custom policy-pack work, dedicated support, and negotiated contract terms are table stakes for a
purchase decision, per `business-model.md`'s enterprise-contracts analysis.

**Design intent**: explicitly **not** a bigger version of Growth with higher numbers — it is a
different sales motion (negotiated, not self-serve) whose limits are custom by definition. Its role
in the pricing page is to signal a ceiling exists and to capture inbound interest from
larger/regulated buyers without forcing them into an ill-fitting self-serve tier.

**Included dimensions** (qualitative, all negotiated): custom or unlimited supplier/contract/AI-
execution allowances, SSO and advanced security/audit requirements, custom/multiple jurisdiction or
compliance packs (tying into `business-model.md`'s deferred jurisdiction-pack pricing and
`international-market.md`'s expansion sequencing), full API access, dedicated support and onboarding,
and — the natural home for `business-model.md`'s deferred implementation-fee model — a structured,
paid onboarding engagement rather than an ad hoc one.

## Limit dimensions across tiers — how they should differ

| Dimension | Direction of scaling across tiers | Reasoning |
|---|---|---|
| Suppliers under management | Increases meaningfully tier-to-tier | Directly tracks company size/procurement volume; the most legible "you're growing" signal to the buyer. |
| Contract reviews per period | Increases meaningfully tier-to-tier | Tracks with suppliers but not 1:1 — larger companies renegotiate/renew more per supplier too. |
| AI executions per period | Increases faster than suppliers/contracts at higher tiers | Growth-tier's "more automation, not just more volume" design intent (above) means AI usage per review should also rise, not just review count. |
| Users/seats | Increases tier-to-tier, but modestly | Cross-functional usage (Procurement+Legal+Compliance+Finance) needs enough seats to be useful even at Starter; seat-gating too aggressively undermines the cross-functional-adoption thesis in `business-case.md`. |
| Policies | 1 → several → many/unlimited | Reflects the real business need (differentiated risk profiles by vendor category) emerging as a company scales, not an arbitrary gate. |
| AI/automation sophistication (auto-approve thresholds, workflow configurability) | Increases qualitatively, not just numerically, at Growth+ | This is the one dimension that should differentiate on *capability*, not just *quantity* — matches the Growth-tier design intent above. |
| Integrations | None → basic → basic+API → full/custom | API access should not exist below Growth, per the `business-model.md` reasoning that Starter/Business buyers lack the internal engineering capacity to use it. |
| Storage | Increases tier-to-tier | Tracks directly with document/evidence volume — a low-cost dimension to scale generously since storage cost itself is low relative to AI-execution cost. |
| Jurisdiction/compliance packs | Brazil pack only, all tiers → custom/multiple at Enterprise | Matches `business-model.md`'s decision to bundle the single Brazil pack into every tier for v1, reserving multi-pack access for Enterprise once a second pack exists (`international-market.md`). |

## What is explicitly TBD

- Status: TBD / Current preferred option: none stated — deliberately avoiding an invented number for
  monthly/annual price per tier / Why undecided: correct price points require willingness-to-pay data
  from real prospect conversations (`business-case.md`'s ROI-calculator dependency), which has not
  been gathered / Resolution: run pricing-sensitivity conversations with the first 10–20 design-
  partner-stage prospects identified in `go-to-market.md`, using the tier *structure* above as the
  conversation scaffold rather than presenting fixed numbers upfront / Decision artifact: a pricing
  worksheet from those conversations (not yet created).
- Status: TBD / Current preferred option: none stated — deliberately avoiding invented numeric caps
  (e.g., "50 suppliers on Starter") / Why undecided: the right numeric caps depend on real usage
  patterns from actual customer vendor lists, which vary more than can be safely estimated a priori /
  Resolution: instrument usage from the first design-partner cohort during a free/discounted pilot
  period and set initial caps from observed real usage distributions, then adjust / Decision
  artifact: usage-distribution data from pilot customers (not yet available).
- Status: TBD / Current preferred option: annual billing with a discount over monthly, matching
  standard SaaS convention / Why undecided: whether the target buyer (Procurement/Finance at a
  50–1,000 employee Brazilian tech company) prefers annual commitment or monthly flexibility at this
  early, unproven stage of the category has not been tested / Resolution: offer both in early sales
  conversations and observe actual buyer preference / Decision artifact: none yet.

## How this connects back to the domain model

Every dimension named above maps directly onto fields and invariants already defined in
`docs/03-domain/domain-model.md` and `docs/03-domain/business-rules.md`: `Organization.plan`,
the `trial → active → past_due → cancelled/expired` lifecycle (`ADR-014`), and the "block new
creation, never delete existing data" limit-enforcement invariant (`BR-ORG-003`). Pricing-strategy
decisions should always be checked against that invariant set before being finalized — a tier
structure that required deleting a customer's historical data on downgrade, for instance, would
violate a business rule that exists specifically to protect the audit-trail value proposition
(`business-case.md`).
