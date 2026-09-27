# Go-To-Market

> The initial GTM motion for JuriSense Gate: how to land the first 10–20 Brazilian tech-company
> customers, the role of the hackathon, the content/community angle, why this is a founder-led sale,
> and what changes once initial traction exists. Builds on `brazil-market.md` (segment/culture),
> `business-case.md` (the pitch and objections), and `pricing-strategy.md` (the offer).

## The core motion: founder-led sales to a named, narrow segment

The first 10–20 customers should not come from broad-based marketing — they should come from
**direct, founder-led outreach to a tightly defined segment**: Brazilian technology companies,
50–1,000 employees, with visible signs of real procurement volume (multiple SaaS/consultancy/cloud
vendors, active hiring, recent funding rounds implying vendor scale-up) and no existing TPRM tooling
in place. This is the correct motion for three structural reasons specific to this product, not a
default startup playbook choice:

1. **It's a trust-dependent, workflow-embedded category, not a self-serve tool.** JuriSense Gate asks
   Legal/Compliance/Procurement to route real approval decisions through it — nobody adopts that from
   a landing page and a free trial alone. Early customers need to see the founder explain, live, how
   AI extraction stays subordinate to deterministic policy rules (the "can we trust AI for this"
   objection in `business-case.md`), which requires a real conversation, not a self-serve funnel.
2. **The product needs design partners more than it needs early revenue.** The pricing numbers,
   usage-limit calibration, and even parts of the policy-rule template library
   (`docs/03-domain/policy-engine.md`) are explicitly TBD pending real customer input
   (`pricing-strategy.md`, `business-case.md`). Founder-led sales conversations are also product-
   discovery conversations — a self-serve motion would forfeit that.
3. **The category has to be explained, not just sold.** "TPRM/GRC/CLM, but Brazil-first and combined"
   is not a category the target buyer already searches for by name (unlike, say, "CRM" or "payroll
   software") — the first conversations are necessarily consultative and educational, which only a
   live conversation (not paid ads or inbound SEO alone) can do efficiently at this stage.

## Sourcing the first prospects

Concrete, low-cost channels consistent with a founder-led motion in this specific segment:

- **Warm network first**: any existing relationships with Legal, Compliance, Procurement, or
  founder/COO contacts at companies matching the segment profile — the fastest path to a first design
  partner, because trust is already partially established.
- **LinkedIn outreach targeted by role and company profile**: Head of Procurement / General Counsel /
  Head of Compliance / COO / Procurement Manager at Brazilian tech companies in the 50–1,000-employee
  band, referencing the specific, recognizable pain (spreadsheet-and-email vendor review, no
  systematic audit trail) rather than a generic product pitch — matching the objection-framing already
  developed in `business-case.md`.
- **Legal-ops and compliance communities**: Brazilian legal-ops, compliance, and GRC professional
  communities (LinkedIn groups, Slack/Discord communities, local legal-tech meetups) are a
  concentrated pool of exactly the users (not just buyers) who feel this pain daily and are likely to
  give direct product feedback, not just a sales lead.
- **Existing vendor/consultant relationships**: law firms, compliance consultancies, and Big4-style
  advisory practices serving this segment are a plausible referral source even before any formal
  partner program exists (`business-model.md` names partner/referral motions as a later-stage model —
  informal referrals from these relationships can start now without building that infrastructure).

## The role of the hackathon as a public proof point

The **BLI Legal Tech Hackathon 2 / Legal Hack 2026** (judging 2026-11-05 to 2026-12-05, awards
2026-12-12; sponsors ICP/Caffeine AI, Constellation Network, Story Protocol) is not a side project
alongside GTM — it is the first GTM asset:

- **Credibility signal for a new category.** A public hackathon result (working demo, judged by legal-
  tech-focused evaluators) gives an outside validation point for a product in a category the buyer
  does not yet have a mental model for — "built for and recognized at a legal-tech hackathon" is a
  concrete, checkable credibility marker that substitutes for the case studies and reference customers
  the company does not have yet at this stage.
- **Forcing function for a real, working demo.** The hackathon's judging timeline and its "Hackathon
  Cut" scope (Evidence/Audit + a working blockchain anchor, per `docs/00-project/overview.md`'s
  roadmap summary) means there will be a genuinely demoable product — including the audit-trail and
  blockchain-anchoring pieces that are the sharpest part of the business case
  (`business-case.md`) — on a fixed, near-term timeline, which is exactly the artifact founder-led
  sales conversations need.
- **Direct outreach hook.** "We're building this for the BLI Legal Tech Hackathon, want an early
  look?" is a lower-friction, more specific opener than a cold pitch, and gives prospects a concrete
  reason to engage before the product is fully commercial (i.e., before pricing conversations are
  even necessary) — converting hackathon-stage conversations into design-partner relationships.
- **Content generation.** The hackathon process itself (building in public, the specific technical
  choices like the `AnchoringProvider` abstraction in `ADR-007`) is a natural source of the
  content/community angle below — a real build narrative is more credible than manufactured marketing
  content for a trust-dependent product.

## Content / community angle

Given the trust-dependent nature of the category and the target buyer's professional background
(Legal/Compliance/Procurement, not typically a highly online, product-led-growth-savvy buyer
persona), the content motion should prioritize **substance and specificity over volume**:

- **Portuguese-language, specific, checklist-style content** aimed at the exact pain points named in
  `business-case.md` (e.g., "what should a vendor compliance checklist actually cover before you sign
  a SaaS contract in Brazil" or "how to read a DPA clause for LGPD exposure") — content that is useful
  on its own even to someone who never becomes a customer, which builds the kind of trust a
  compliance-adjacent buyer needs before taking a sales call.
- **Building-in-public narrative tied to the hackathon**, published to founder/company LinkedIn and
  relevant legal-tech communities — technical and product decisions (e.g., why blockchain is used only
  as a verification layer, not the product, per `docs/00-project/overview.md`) double as both
  credibility content and pre-emptive objection handling.
- **Community presence over paid acquisition**: given the segment's B2B, trust-heavy nature and the
  company's early stage, participating genuinely in existing legal-ops/compliance/GRC communities is
  higher-leverage than paid ads at this stage — paid acquisition is a later-stage lever once the
  message and ICP are validated by direct conversations.

## Why founder-led sales specifically fits a compliance-trust product

Beyond the general early-stage-startup logic, this product has a specific reason founder-led sales
matters more than usual: the buyer is being asked to route *legal and compliance judgment calls*
through the product, and the seller needs to be able to answer hard, specific questions live — "what
happens if the AI extraction is wrong," "what exactly gets put on a blockchain," "how does this differ
from what OneTrust already does" — with precision, not a scripted pitch. Early on, only someone with
deep product and domain understanding (a founder, not a generic sales hire) can do this credibly,
and every one of these conversations should be treated as calibrating the objection-handling material
in `business-case.md` for whoever runs sales conversations later.

## Expansion motion after initial traction

Once the first 10–20 customers are live and at least a few have real usage history (usage data that
also feeds the TBD pricing/limit calibration in `pricing-strategy.md`), the motion should evolve in
this order, each stage building on evidence from the previous one rather than being scheduled by
calendar date:

1. **Reference-customer-driven outbound**: use named (with permission) or anonymized case studies from
   the first cohort to support outbound to a wider slice of the same segment — this is the point where
   the "no competitor combines this for this segment" claim (`competitive-landscape.md`) becomes
   provable with a real customer story, not just an architectural argument.
2. **Inbound content scale-up**: once there is real customer language (their words, not the founders'
   assumptions, about the pain and the value delivered) to draw on, content production can scale
   because it stops being speculative.
3. **Early channel/referral formalization**: informal law-firm/consultancy referral relationships
   (sourced above) can be formalized into a lightweight referral program once there is a proven product
   to refer people to — still short of the full partner/marketplace ecosystem named as deferred in
   `business-model.md`.
4. **Upmarket motion toward Growth/Enterprise buyers**: with reference customers and a calibrated
   pricing structure in hand, sales conversations can extend toward the upper end of the segment and
   the first genuinely negotiated Enterprise deals (`pricing-strategy.md`'s Enterprise tier,
   `business-model.md`'s enterprise-contracts analysis) — deliberately sequenced after mid-market proof,
   not before it, for the reasons given in `business-model.md`.
5. **International readiness signal, not international launch**: strong, repeatable Brazilian traction
   is the trigger to begin the LATAM-adjacency exploration named in `international-market.md` — GTM
   expansion into a new country follows product/market proof in Brazil, it does not run in parallel
   with still-unproven initial traction.
