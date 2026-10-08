# Business Model

> How JuriSense Gate makes money, model by model, with an explicit recommendation for v1 and an
> explicit list of what is deferred. This document is the revenue-model analysis; for tier
> structure and limit dimensions see `pricing-strategy.md`, for the buying logic see
> `business-case.md`, and for the payment-gateway sequencing decision see `ADR-014`.

## Commercial policy update — 2026-10-07

The owner selected **the same released features in every subscription, differentiated only by
usage allowances**. [Pricing strategy](pricing-strategy.md) now defines the proposed BRL catalog,
quota semantics, cost assumptions, and rollout requirements. This supersedes feature exclusivity
suggested in the candidate-model discussion below: API, integrations, SSO, standard policy packs,
and workflow capabilities are available in every tier when released. Their implementation dates
remain governed by the roadmap. Enterprise negotiates finite capacity; bespoke professional
services remain separately scoped. Public prices are proposals until cost and metering validation.

## Why this matters now, even without a payment gateway

`ADR-014` defers real payment-gateway integration (Stripe or a Brazilian equivalent) past the
hackathon and early-validation phase. That is a technical/sequencing decision, not a business-model
decision: the product still needs a `Plan`/`Subscription` domain model (`Organization.plan`,
lifecycle `trial → active → past_due → cancelled/expired`, per `docs/03-domain/domain-model.md`)
that enforces limits from day one, even while actual billing is manual (invoice, bank transfer, or
a founder-run Stripe Payment Link) for the first cohort of customers. Getting the revenue *model*
right early avoids two expensive mistakes: (1) building a limit-enforcement system around the wrong
usage dimension, and (2) training the first customers on a pricing logic that has to be renegotiated
away from later, which is reputationally costly with the exact accounts (Legal/Compliance/Procurement
leaders) whose trust the product depends on.

## The candidate models

### 1. Flat SaaS subscription (seat- or org-based, fixed tiers)

**Mechanics**: fixed monthly/annual fee per tier (Starter/Business/Growth/Enterprise — see
`pricing-strategy.md`), independent of how many suppliers or contracts actually flow through the
system in a given month.

**Advantage for this product**: predictable revenue and predictable cost for the buyer — a critical
property when the buyer is Procurement/Finance and the internal pitch is "replace an unpredictable
manual process with a predictable line item." It is also the fastest model to sell without a mature
usage-metering pipeline, and the easiest for a first-time buyer of a compliance tool to evaluate
against a budget line.

**Disadvantage for this product**: JuriSense Gate's underlying cost structure is *not* flat — every
supplier check, contract extraction, and AI-assisted review consumes external API costs (AI model
calls, official-source lookups) and compute that scale with usage. A pure flat fee either overprices
light users (a 60-person company evaluating 5 suppliers/month) or underprices heavy users (a
400-person company running 200 supplier checks/month), and in the latter case the company absorbs
AI-cost risk with no revenue lever to match it.

**Verdict**: use as the *base* of the model, not the whole model (see Recommendation).

### 2. Usage-based pricing (pay per unit of consumption, no tiers)

**Mechanics**: price per supplier check, per contract review, per AI execution, metered and billed
per period (think: a usage-metered API product).

**Advantage for this product**: aligns revenue with cost almost perfectly — heavy users pay more,
light users pay less, and the model scales cleanly from a 50-employee company to a 1,000-employee
one without a step-function tier renegotiation. It is also intuitively fair to a Procurement/Finance
buyer used to volume-based vendor costs.

**Disadvantage for this product**: pure usage pricing is a poor fit for a *new, trust-dependent*
category. A buyer evaluating whether an AI-assisted compliance decision can be trusted at all does
not want unpredictable monthly bills while they are still building internal confidence in the tool;
unpredictability becomes an objection in itself ("what if the AI reviews explode our bill because it
flags every contract for re-review?"). Pure usage pricing also weakens the "we've fully adopted this
as our process of record" commitment signal that a subscription creates — compliance tooling
benefits from being treated as infrastructure, not a metered utility.

**Verdict**: too risky as the sole model for v1; the right building block for v2+ once customers
have usage history to negotiate from (see Recommendation, "usage-sensitive limits" vs. "usage-based
billing").

### 3. Per-supplier-review pricing (transaction-based, supplier-check unit)

**Mechanics**: charge per completed `SupplierCheck` (see `docs/03-domain/domain-model.md`) —
effectively a la carte vendor-vetting.

**Advantage for this product**: extremely legible value story for a first-time or low-volume buyer
("$X to vet one vendor" is easy to compare against a lawyer's hourly rate for the same task) and a
low-commitment way to get a company to try the product without a subscription commitment — useful as
a top-of-funnel / trial-conversion mechanism, not necessarily as the core model.

**Disadvantage for this product**: undersells the platform. The product's differentiated value is
the *combination* of supplier intelligence + contract intelligence + policy engine + audit trail
across the whole procurement lifecycle, not a single point-in-time check. Pricing purely per
supplier review invites the buyer to mentally model JuriSense Gate as "a vendor-lookup tool," which
is a weaker, more commoditizable position than "the system of record for vendor and contract
compliance decisions" (see `differentiation.md`). It also does not monetize the Policy Engine,
Approvals, or Evidence/Audit layers, which are a large share of the engineering investment and the
actual moat hypothesis.

**Verdict**: acceptable as an *add-on metering unit* inside a subscription (i.e., a plan includes N
supplier reviews/month, overage billed per review), not as the standalone model.

### 4. Per-contract-review pricing (transaction-based, contract-analysis unit)

**Mechanics**: charge per `ContractVersion` analyzed (per `docs/03-domain/domain-model.md`).

**Advantage / disadvantage**: structurally identical reasoning to per-supplier-review above — legible
per-unit value, same undersell risk, same good fit as an in-plan metered unit with overage.

**Verdict**: same as #3 — a metering dimension inside the subscription, not the sole model.

### 5. API usage / developer platform pricing

**Mechanics**: expose supplier checks, contract extraction, and policy evaluation via API, billed
per call or per API-consuming integration, aimed at companies that want to embed compliance checks
into their own procurement/ERP tooling rather than use the JuriSense UI.

**Advantage for this product**: this is a real long-term expansion path — it is explicitly the
final planned module (`JuriSense API`, see `docs/01-product/future-product-vision.md` and
`expansion-strategy.md`) and matches how Vanta/Drata and OneTrust monetize their most
integration-mature customers. It also opens a channel-partner motion (procurement platforms, ERPs,
legal ops tooling reselling JuriSense as an embedded compliance layer).

**Disadvantage for this product today**: v1's target buyer (a 50–1,000 employee tech company without
dedicated TPRM tooling) is buying a *workflow and a decision*, not an API — they do not yet have the
internal engineering capacity or organizational maturity to build against a compliance API. Building
API pricing before there is UI-product-market fit would spend scarce engineering effort on a channel
the initial segment cannot use.

**Verdict**: explicitly deferred (see `expansion-strategy.md`); revisit once Enterprise-tier
customers request it.

### 6. Enterprise contracts (custom-negotiated, annual, multi-year)

**Mechanics**: negotiated annual contracts for large/regulated buyers, typically bundling higher
usage caps, custom policy packs, SSO/audit requirements, dedicated support, and possibly custom
integrations.

**Advantage for this product**: enterprise and regulated buyers (banks, larger tech companies,
companies under external audit pressure) have the highest willingness to pay for exactly what
JuriSense Gate's differentiation is — a defensible, reproducible audit trail (see `business-case.md`)
— and enterprise deals materially increase average contract value and revenue predictability once
the product has reference customers.

**Disadvantage for this product today**: enterprise sales cycles are long (procurement/security
review, legal review, SSO/compliance requirements the product does not yet fully have), and closing
one before the product has 10–20 mid-market reference customers risks over-customizing the product
for one logo instead of building a repeatable mid-market motion (see `go-to-market.md`).

**Verdict**: the explicit top of the tier ladder (`pricing-strategy.md`'s Enterprise tier) and the
named path for later revenue concentration, but not the initial go-to-market focus.

### 7. Implementation / onboarding fees

**Mechanics**: one-time fee for policy-pack setup, data migration (existing supplier lists,
contract backlog ingestion), and admin training.

**Advantage for this product**: compliance tooling has a real, legitimate setup cost — a company's
first Policy Engine configuration requires translating actual internal policy into `when/then` rules
(`docs/03-domain/policy-engine.md`), which benefits from guided setup, and charging for it signals
seriousness rather than positioning the product as "another dashboard nobody configures." It is also
a reasonable way to monetize founder-led onboarding time during the early GTM phase without
inflating the recurring subscription price the market has not yet validated.

**Disadvantage for this product**: extra friction in a hackathon-to-early-revenue period where the
priority is proving usage and value, not maximizing one-time revenue; and it needs a bar of product
maturity (documented setup flow) that does not fully exist yet.

**Verdict**: use selectively for early customers who need real policy-migration work (see
`go-to-market.md`), waived or minimized for the first design-partner cohort in exchange for case
studies and product feedback.

### 8. Jurisdiction / compliance / policy pack pricing

**Mechanics**: price add-on "packs" — e.g., an LGPD-specific policy pack, a future GDPR pack once
the EU Jurisdiction Pack ships (`international-market.md`), or vertical-specific policy templates
(fintech vendor policy, healthcare DPA policy) — as paid add-ons on top of the base subscription.

**Advantage for this product**: this maps directly onto the architecture's Core Platform vs.
Jurisdiction Packs split (`docs/04-architecture/architecture-overview.md`, `international-market.md`)
and is a clean, scalable monetization unit for exactly the kind of expansion this product is built
for — each new jurisdiction or vertical pack is both a product investment and an independent revenue
line, without re-architecting the core.

**Disadvantage for this product today**: v1 ships with exactly one pack (Brazil/LGPD) bundled into
every tier — there is nothing to differentiate on yet. Packaging this as a separate paid SKU before
a second pack exists would just be an artificial price increase on the only thing being sold.

**Verdict**: structurally correct future model, explicitly deferred until a second jurisdiction or
vertical pack exists (`international-market.md`, `expansion-strategy.md`).

### 9. Marketplace / white-label / partner ecosystem

**Mechanics**: (a) a marketplace where third parties publish policy packs, integrations, or
verification-source connectors and JuriSense takes a revenue share; (b) white-labeling the platform
for consultancies/law firms/Big4-style advisory firms to offer under their own brand to their
client base; (c) a partner/referral program with ERPs, procurement platforms, or law firms.

**Advantage for this product**: high long-term leverage — a marketplace or white-label motion turns
JuriSense from a single-vendor product into a platform, and is the natural monetization shape once
the "data/network effects from policy packs" moat hypothesis (`differentiation.md`) is validated at
all. Partner referral from law firms or Big4 advisory practices is also a plausible low-CAC channel
given the trust-heavy nature of the category.

**Disadvantage for this product today**: none of this is buildable or sellable before there is a
proven core product with real usage — a marketplace with no supply (no third-party packs) or a
white-label offer with no reference customer is not credible to a partner or a first white-label
prospect.

**Verdict**: explicitly deferred; a v3+/company-stage idea, noted here so it is not forgotten, not
because it is actionable now.

## Recommendation for v1

**Hybrid: a base SaaS subscription (tiered, per `pricing-strategy.md`) with usage-sensitive limits
per the `Plan`/`Subscription` model already decided in `ADR-014`.** Concretely:

- Each tier (Starter/Business/Growth/Enterprise) has a **fixed monthly/annual base price** and
  **included usage allowances** for the three metering dimensions that actually track cost and
  value: suppliers analyzed, contracts reviewed, and AI executions per period (exactly the three
  dimensions already named in `ADR-014` and `docs/03-domain/business-rules.md` BR-ORG-003).
- Exceeding an allowance **blocks new creation, never deletes existing data** (BR-ORG-003 — this
  invariant already exists in the domain model and is deliberately buyer-friendly: a company is
  never at risk of losing its audit trail for going over a limit).
- Overage is **modeled as a per-unit rate reference in the plan configuration now**, even though no
  payment gateway charges it automatically yet (`ADR-014`) — so the upgrade path to real metered
  billing later is additive, not a redesign, exactly as `ADR-014`'s Consequences section intends.
- Implementation fees are used selectively and manually for early customers needing real policy
  migration help, not automated or systematized yet.
- Jurisdiction/compliance packs, API usage pricing, enterprise custom contracts, and
  marketplace/white-label revenue are **explicitly deferred** — named here as the logical next moves
  (see `expansion-strategy.md`), not built or priced now.

**Why this is the right sequencing**: it gives the first cohort of customers pricing that is legible
and predictable enough to buy without a procurement fight (flat tiers), while the underlying limit
dimensions already track real cost drivers — so when the product has enough usage history to move
toward true usage-based or enterprise pricing (subject to the feature-parity policy in `pricing-strategy.md`), that
transition is a pricing-page change and a metering-to-billing wire-up, not a rebuild of the
`Plan`/`Subscription` domain model.

## What is explicitly deferred (summary)

| Model | Status in v1 |
|---|---|
| Flat SaaS subscription | **Core of v1** (base of the hybrid) |
| Usage-sensitive limits (non-billed enforcement) | **Core of v1** (per `ADR-014`) |
| True usage-based billing (metered charges) | Deferred — v2, once a payment gateway exists |
| Per-supplier-review / per-contract-review as standalone SKUs | Deferred — kept as in-plan metering units only |
| API usage pricing | Deferred — post-UI product-market fit (`expansion-strategy.md`) |
| Enterprise custom contracts | Deferred as *focus*, but tier exists as ceiling (`pricing-strategy.md`) |
| Implementation/onboarding fees | Used ad hoc/manually for early customers, not systematized |
| Jurisdiction/compliance/policy packs as paid add-ons | Deferred until a second pack exists (`international-market.md`) |
| Marketplace / white-label / partner ecosystem | Deferred — company-stage idea, not v1/v2 |
