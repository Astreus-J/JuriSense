# International Market

> How JuriSense Gate expands beyond Brazil: the business logic for Core Platform vs. Jurisdiction
> Packs, candidate next markets and what regulatory hooks matter in each, and why international
> expansion is sequenced after — not alongside — Brazil. This document covers the business/market
> side; the technical implementation of the Jurisdiction Pack architecture is covered in
> `docs/04-architecture/architecture-overview.md`. For the current-market analysis this builds on,
> see `brazil-market.md`.

## Core Platform vs. Jurisdiction Packs — the business logic

The product is architected (per `docs/00-project/overview.md` and
`docs/04-architecture/architecture-overview.md`) so that jurisdiction-specific logic — verification
sources, sanctions lists, policy-rule templates, regulatory clause types — lives in swappable
"Jurisdiction Pack" modules (Policy Engine rule packs and Supplier Intelligence source adapters),
while the Core Platform (workflow engine, policy evaluation, approvals, evidence/audit, blockchain
anchoring) is jurisdiction-agnostic. From a business standpoint, this is what makes international
expansion a **market-entry decision, not a re-engineering decision**: entering a new country means
building and validating one new Jurisdiction Pack (new data-source adapters, new policy-rule
templates matching local regulation) against an already-proven Core Platform, not rebuilding the
product. This directly shapes the commercial model too — see `business-model.md`'s "jurisdiction /
compliance / policy pack pricing" analysis, where each new pack is both a product investment and an
independent revenue line once a second pack exists.

This also means the *business* case for entering a given country reduces to two questions that are
answerable without new engineering: (1) does the target segment (companies with real
vendor/procurement volume and no dedicated TPRM tooling) exist there in a comparable buying pattern
to Brazil, and (2) is there a comparably strong regulatory hook (a data-protection law, a sanctions
regime, an anti-corruption framework) that gives the sale the same forcing-function quality LGPD
gives it in Brazil (`brazil-market.md`)?

## Candidate next markets and their regulatory hooks

### United States

- **Regulatory hooks**: no single federal data-protection law equivalent to LGPD/GDPR, but a dense
  patchwork of relevant regimes that matter to a vendor/contract-compliance product: state privacy
  laws (California's CCPA/CPRA and its growing set of state-level equivalents), **OFAC** sanctions
  screening (Treasury's Office of Foreign Assets Control — a hard requirement for any company doing
  business with regulated counterparties or in regulated industries), and **SEC**-driven vendor
  due-diligence expectations for public companies and their supply chains (e.g., third-party risk
  disclosure expectations tightening post-SolarWinds-era regulatory attention).
- **Why it's attractive**: the largest addressable market by company count and willingness-to-pay in
  the TPRM/GRC category — Vanta, Drata, and OneTrust all built their initial scale here, which proves
  category demand exists at volume.
- **Why it's not first**: it is also the most competitively saturated market for this category —
  entering the US market means competing directly with well-funded, US-native incumbents
  (`competitive-landscape.md`) on their home turf, with none of the "underserved segment" advantage
  Brazil provides. A Brazil-proven product with reference customers and a working Jurisdiction Pack
  pattern is a much stronger position to enter the US from than a cold start.

### European Union

- **Regulatory hooks**: **GDPR** is the closest direct analogue to LGPD (Brazilian law was explicitly
  modeled on it), meaning the Brazil Jurisdiction Pack's data-processing/DPA-clause extraction logic
  and policy-rule patterns transfer with adaptation, not a rewrite — this is the single strongest
  "next pack" candidate from a pure engineering-leverage standpoint. Also relevant: **EU sanctions
  lists** (Common Foreign and Security Policy consolidated list) for supplier screening, and sector-
  specific frameworks like **DORA** (Digital Operational Resilience Act) for financial-sector
  third-party risk, which is directly TPRM-shaped regulation.
- **Why it's attractive**: GDPR-driven demand for third-party data-processing diligence is mature and
  well understood by buyers (unlike Brazil, where LGPD awareness is real but compliance maturity is
  uneven per `brazil-market.md`) — an EU buyer needs less category education.
  OneTrust's own origin as a privacy-compliance product for GDPR is direct evidence this demand is
  real and large.
- **Why it's not first**: multi-country fragmentation (GDPR is EU-wide, but enforcement, language,
  and local business culture vary by member state) means "EU" is really several market entries in
  practice, not one — a heavier lift than Brazil's single-country focus, and again a market where
  OneTrust already has enterprise incumbency.

### United Kingdom

- **Regulatory hooks**: UK GDPR (post-Brexit divergent-but-similar to EU GDPR) and the UK's own
  sanctions regime (OFSI — Office of Financial Sanctions Implementation), plus a mature corporate
  compliance culture (UK Bribery Act creates anti-corruption supply-chain diligence expectations
  comparable to Brazil's Lei 12.846/2013 driving CNEP relevance).
- **Why it's attractive**: English-language market, regulatory logic close enough to the EU pack to
  largely reuse it, and a compliance-mature buyer base.
- **Why it's not first**: smaller absolute market than the US or EU, and the incremental
  Jurisdiction Pack work (UK-specific sanctions source, UK GDPR nuances) is real but not
  differentiated enough to prioritize over the higher-leverage EU pack.

### LATAM (beyond Brazil)

- **Regulatory hooks**: several LATAM countries have LGPD-adjacent data-protection laws (Mexico's
  data protection framework, Colombia's Ley 1581, Argentina's data protection law), and shared
  business-Portuguese/Spanish-language and cultural proximity to Brazil's procurement culture
  (`brazil-market.md`).
- **Why it's attractive**: the most natural "adjacent market" expansion — closer cultural and
  regulatory distance from Brazil than the US/EU/UK, and Brazilian companies with LATAM operations
  are a plausible expansion vector for existing customers (land in Brazil, expand within the same
  customer's regional footprint before a fully separate market-entry motion).
- **Why it's not first (after Brazil, before US/EU)**: individually smaller markets than the US or
  EU, requiring multiple smaller Jurisdiction Packs (Mexico, Colombia, Argentina each differ) for
  less aggregate opportunity than one EU pack — but a strong candidate for **the second pack after
  Brazil**, ahead of the US, precisely because of the lower relative lift and existing-customer
  expansion angle.

## Sequencing logic: why not international first

Four reasons, stacked:

1. **The differentiated wedge only exists in Brazil today.** The core differentiation claim (no
   competitor combines Brazil-first supplier compliance + contract intelligence + policy engine +
   blockchain evidence for this segment) is specifically a *Brazil* claim
   (`docs/00-project/overview.md`, `competitive-landscape.md`). The same claim is not true in the US
   or EU, where OneTrust, Vanta, and Drata already have mature, well-integrated offerings — entering
   those markets before Brazil validates the product would mean competing on unproven differentiation
   against entrenched players, instead of building a track record where no comparable player exists.
2. **One Jurisdiction Pack must be proven before a second is built.** The Core Platform vs.
   Jurisdiction Pack architecture is a hypothesis until at least one pack (Brazil) has been built,
   sold, and used in production — building a second pack in parallel, before the split between
   "core" and "jurisdiction-specific" logic has been battle-tested against real customer usage, risks
   baking the wrong abstraction boundary into the platform.
3. **Home-market advantages are real and non-transferable early.** The founder-market fit, language,
   and design-partner access described in `brazil-market.md` do not exist in the US/EU/UK yet — early-
   stage go-to-market (`go-to-market.md`) depends on exactly this kind of proximity, which argues for
   depth in one market before breadth across several.
4. **International expansion should be funded by Brazilian traction, not precede it.** Multi-country
   sales, support, and compliance-data-source integration is a meaningfully larger operating lift than
   a single-country motion; the credible path is a proven Brazil business (revenue, reference
   customers, a validated hybrid pricing model per `business-model.md`) that then funds and justifies
   the next Jurisdiction Pack, rather than spreading limited early resources across markets before any
   one of them is proven.

## Recommended sequencing (directional, not a committed roadmap date)

1. **Brazil** (current, in progress) — prove the Core Platform + Brazil Jurisdiction Pack, land the
   first 10–20 customers (`go-to-market.md`).
2. **LATAM adjacency** (e.g., Mexico/Colombia) — lowest-lift second pack, natural expansion path for
   existing Brazilian customers with regional operations, before a fully independent market-entry
   motion is required.
3. **EU** — highest engineering leverage (GDPR pack builds directly on the Brazil/LGPD pack's
   data-processing logic) and a compliance-mature buyer base, once the company has the resources for
   a genuinely separate go-to-market motion (different language(s), different sales relationships).
4. **US and/or UK** — largest absolute markets but also the most competitively saturated for this
   category; entered once JuriSense has reference customers and a proven multi-jurisdiction track
   record to compete credibly against incumbents on their home turf.

- Status: TBD / Current preferred option: the sequencing above (Brazil → LATAM → EU → US/UK) / Why
  undecided: actual sequencing will depend on where real inbound demand and design-partner interest
  emerge, which cannot be predicted before Brazil traction exists / Resolution: revisit this
  sequencing explicitly at the same milestone that triggers `expansion-strategy.md`'s module-expansion
  review (post-hackathon, once the first paying-customer cohort is established) / Decision artifact:
  not yet created — will be a dated addendum to this document once Brazil traction data exists.
