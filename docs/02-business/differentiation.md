# Differentiation

> The moat hypothesis, deliberately split into three tiers of confidence: what is actually built or
> plausible today, what is differentiated *if executed well*, and a long-term moat *hypothesis* —
> stated explicitly as a hypothesis to validate, not a claimed moat, per the founder's own instruction
> not to overclaim. This document synthesizes `competitive-landscape.md`'s per-competitor analysis and
> should be read alongside it.

## Why this document is structured this way

Early-stage companies routinely overclaim differentiation before it is earned — describing a
combination of features as a "moat" when it is really just a current feature set that a well-funded
competitor could replicate. This document deliberately resists that by separating three different
claims that are often collapsed into one:

1. **Current capability** — what exists or is realistically buildable now, independent of whether it
   is differentiated.
2. **Potential differentiation** — what becomes genuinely differentiated *if executed well*, i.e., a
   real combination advantage that is hard to casually replicate, but not yet a structural moat.
3. **Long-term moat hypothesis** — what *could* compound into a durable, hard-to-replicate advantage
   over years, driven by data/network effects — explicitly framed as unproven and requiring
   validation, not asserted as already true.

## (a) Current capability

What is actually built or architecturally committed today, per `docs/00-project/overview.md` and the
ADRs:

- A domain model and pipeline (`docs/03-domain/domain-model.md`) that connects supplier verification,
  contract ingestion/extraction, policy evaluation, approval routing, decision packaging, and evidence/
  audit into one coherent flow — not yet proven at scale with real customers, but architecturally real,
  not aspirational.
- An executable Policy Engine design (`when <condition> then APPROVE|REVIEW|BLOCK`, versioned, with a
  defined aggregation algorithm — `ADR-004`, `ADR-010`, `BR-CMP-002`) that is deterministic and
  auditable by construction, not merely "AI decides" framing.
- Structured contract extraction with clause-level provenance (page/span citation back to source,
  `BR-CON-004`) as a designed requirement, not an afterthought.
- A provider-agnostic blockchain anchoring abstraction (`ADR-007`) with a clear, narrow privacy
  boundary (hashes only, never raw data — `BR-EVD-002`) — the concrete anchoring provider is still a
  pending technical spike (see `ADR-007`'s own status), but the interface and privacy model are
  decided.
- Known, real, publicly accessible Brazilian compliance data sources (CNPJ via Receita Federal,
  CEIS/CNEP/CEPIM via Portal da Transparência — `brazil-market.md`) that make Brazil-first supplier
  verification a genuinely available, not speculative, data layer — though the exact integration
  mechanism is itself still a Phase-2 spike (`brazil-market.md`'s TBD).

**Honest caveat**: none of this has yet been validated against real paying customers at volume. What
is "current capability" here is a *coherent, buildable design*, not proof of product-market fit or
proof that the AI-extraction and policy-evaluation pipeline performs reliably at the accuracy levels a
compliance buyer would require in production. That validation is the immediate next milestone, not a
completed one.

## (b) Potential differentiation — if executed well

This is the level of claim that `docs/00-project/overview.md` itself makes: **"no identified
competitor combines Brazil-first supplier compliance + contract intelligence + an executable policy
engine + blockchain-backed evidence in one product"** for the 50–1,000-employee segment
(`competitive-landscape.md`'s synthesis). This is a real, defensible claim *about the current
competitive landscape as researched*, with three important qualifications:

1. **It is a combination advantage, not an ingredient advantage.** Every individual ingredient exists
   somewhere else and better-resourced (Vanta/Drata's evidence automation, OneTrust's TPRM breadth,
   Ironclad's contract-lifecycle depth, Harvey/Spellbook's legal-AI sophistication, Norm AI's
   policy-as-code philosophy and capital). The differentiation claim rests entirely on *nobody having
   assembled this specific combination for this specific segment* — which is a real gap today, but a
   gap that is closeable by any of those competitors deciding to build the missing pieces, especially
   a capital-rich one like Norm AI or OneTrust.
2. **It requires genuine execution across all four ingredients, not just one.** A product that does
   supplier verification well but has weak contract extraction, or a good policy engine but no real
   Brazilian data-source integration, does not get the differentiation benefit — the claim depends on
   the whole pipeline working end-to-end and being demonstrably better than assembling the equivalent
   manually (`business-case.md`'s productivity/risk argument), which is an execution risk, not a given.
3. **It is time-bound, not permanent.** "No identified competitor does this today" is a snapshot as of
   the research cited in `docs/00-project/overview.md` and `competitive-landscape.md` — it is not a
   claim that this gap persists indefinitely absent further action. The "long-term moat hypothesis"
   section below is precisely about what would need to be true for the advantage to persist rather
   than simply be a temporary head start.

**If executed well**, this combination gives JuriSense Gate a genuinely differentiated position for
the specific buyer named in `docs/00-project/overview.md`: a mid-market Brazilian tech company gets a
complete, purpose-built, appropriately priced (`pricing-strategy.md`) workflow instead of either
assembling point solutions (a Brazilian data-lookup service + a generic policy tool + a CLM + a
spreadsheet for audit trail) or overpaying for an enterprise suite (OneTrust) that was not built for
their scale.

## (c) Long-term moat hypothesis — explicitly unproven

This section names what *could* become a durable, compounding advantage over years — framed
throughout as a hypothesis requiring validation, deliberately not asserted as an existing moat:

- **Historical compliance-decision corpus.** Every `Decision`, `RuleEvaluation`, and `EvidencePackage`
  JuriSense accumulates (`docs/03-domain/domain-model.md`) is, in aggregate across customers,
  potentially a unique dataset of *how real companies actually decide* on vendor/contract compliance
  questions — which clause patterns get flagged, which policy configurations correlate with fewer
  downstream disputes, which risk categories most often need human override. **Hypothesis**: this
  corpus could improve the product's extraction accuracy, policy-template quality, and risk-scoring
  over time in a way a new entrant without that history cannot easily replicate. **What would validate
  it**: demonstrable, measurable improvement in extraction accuracy or policy-recommendation quality
  correlated with corpus size, observed over real usage — not yet measured, and not assumable from
  architecture alone.
- **Policy-pack network effects.** If a meaningful share of customers converge on similar policy
  patterns for similar vendor categories (e.g., a common baseline for "SaaS vendor with LGPD
  exposure"), JuriSense could develop increasingly refined *shared* policy-template libraries that get
  better as more customers use and implicitly validate them — a mechanism structurally similar to how
  Spellbook's clause-benchmark set (2,000+ benchmarks, per `competitive-landscape.md`) is itself a
  data-driven asset. **Hypothesis**: this could become a genuine switching cost (a customer's refined,
  battle-tested policy templates are not trivially portable to a competitor). **What would validate
  it**: evidence that customers actually converge on shared patterns rather than needing fully bespoke
  policies per company — not yet known.
- **Jurisdiction pack breadth.** As additional Jurisdiction Packs are built (`international-market.md`
  — LATAM, then EU, then US/UK), each new pack becomes progressively cheaper to build on the proven
  Core Platform (`international-market.md`'s Core Platform vs. Jurisdiction Pack logic), while a new
  entrant attempting to match breadth would need to build the same number of packs from zero.
  **Hypothesis**: breadth of jurisdiction coverage could become a real barrier once several packs
  exist. **What would validate it**: actually shipping and selling a second and third pack at
  reasonable incremental cost — unproven until at least one additional pack beyond Brazil exists.
- **Enterprise integration depth.** Once the product has deep integrations into a customer's
  procurement/ERP/CLM stack (a later-stage motion — `business-model.md`'s deferred API-usage model,
  `expansion-strategy.md`'s API module), switching cost rises structurally, similar to how deep
  Vanta/Drata system integrations make those products sticky. **Hypothesis**: integration depth could
  become a retention/expansion moat at the Growth/Enterprise tier. **What would validate it**: this is
  entirely a future-stage question — not applicable until the API/integration layer exists and is
  adopted.

## The explicit non-claim

None of the four items in (c) are claimed as an existing moat. Each requires: real usage at scale,
real measurement, and real time to compound — none of which has happened yet. The correct internal and
external posture, consistent with the founder's instruction, is: **"we have identified a real,
currently-unaddressed combination gap in the market (b), and we have a reasoned hypothesis for how
that initial position could compound into something durable (c) — but we have not yet earned the right
to call it a moat, and we will treat it as a hypothesis to test against real customer and usage data,
not a settled competitive claim."** This framing should be used consistently in pitch materials,
hackathon submissions, and any future fundraising conversation — overclaiming a moat that has not been
earned is a credibility risk with exactly the sophisticated, skeptical buyers and evaluators
(General Counsel, judges, investors) this product needs to convince.
