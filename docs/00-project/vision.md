# Vision

## Mission

> **Turn contracts, supplier data and company policies into auditable compliance decisions.**

This is not a tagline chosen for effect — it is the literal function JuriSense performs. A company
gives us three inputs it already has (a contract, data about the supplier on the other side of it,
and its own internal policy about what it will and will not accept), and JuriSense returns a fourth
thing the company currently has to manufacture by hand, badly: a decision it can defend, months or
years later, to a regulator, an auditor, a new General Counsel, or its own board. Every product
decision, feature, and line of code in JuriSense Gate should be traceable back to that mission. If a
proposed feature does not make contracts, supplier data, or policy easier to turn into a defensible
decision, it does not belong in the product, no matter how impressive it is on its own.

## Where we are today (the 2026 starting point)

JuriSense Gate is being built for the BLI Legal Tech Hackathon 2 / Legal Hack 2026 (judging
2026-11-05 to 2026-12-05), but it is explicitly not being built *as* a hackathon project — it is
being built as the first commercial product of a company, with the hackathon as its first public
proof point and forcing function. The scope discipline this requires is captured in one question we
apply to every feature decision, hackathon or not:

> **"If the hackathon ended tomorrow, would it still be worth building this as a company?"**

This test is deliberately blunt, and it is meant to be used constantly, not just at planning
milestones. Concretely, it means:

- A demo-only flourish that impresses judges for thirty seconds but that no real Head of Procurement
  would ever click twice — a decorative "AI confidence meter" with no evidentiary backing, a fake
  live blockchain ticker, a hardcoded "success" animation — fails the test and does not get built,
  even if it would score well with judges. It optimizes for the wrong customer.
- A boring, unglamorous feature — an audit log export a compliance officer can hand to an external
  auditor, a policy-versioning mechanism that makes a decision reproducible two years later, a
  webhook that lets a customer's existing procurement tool call our decision API — passes the test
  even though it will never appear in a hackathon pitch video, because it is exactly what a paying
  customer needs on day one of a real deployment.
- Anything that only works "because it's a demo" (seeded data that never gets stale, a policy engine
  that can't actually be edited by a customer, a blockchain anchor that we control end-to-end instead
  of one a third party could independently verify) fails the test, because the value proposition —
  *auditability that survives time and organizational memory loss* — collapses the moment a real
  customer tries to rely on it.

The test is also a filter against scope creep in the other direction: features that would be great
for a company five years from now (a full no-code policy builder UI, a marketplace of pre-built
policy packs, native ERP connectors) are legitimate long-term investments but are evaluated on their
own timeline, not smuggled into the hackathon cut because they sound compelling.

## The next 12 months: prove the pipeline, land the first customers

The immediate horizon (through roughly Q3 2027) is narrow and deliberate: make the full pipeline —
Supplier → Company verification → Documents/Contract ingestion → AI structured extraction → Policy
Engine → Compliance Engine → Risk analysis → APPROVE/REVIEW/BLOCK → Human approval → Decision
Passport → Audit Trail → Blockchain verification — work end to end, for real Brazilian mid-market
technology companies, on real contracts and real suppliers, not synthetic hackathon fixtures. Success
in this window looks like: a handful of design-partner customers with real procurement volume using
JuriSense Gate to gate actual vendor onboarding decisions, a Policy Engine expressive enough that a
Head of Compliance can encode their own rules without engineering help, and an Evidence Package /
Decision Passport that has actually been shown to an external auditor and held up. This is the
foundation everything after it is built on — if the core loop (ingest → extract → evaluate → decide →
evidence) is not trustworthy at small scale, nothing downstream (monitoring, deeper intelligence,
becoming infrastructure) is worth pursuing yet.

## Years 2–3: from a gate you pass once to infrastructure you run on continuously

JuriSense Gate answers one question extremely well: *can we sign this, right now?* But a signed
contract is not the end of risk — a supplier's registration status can lapse, a sanctions list can
add a name six months into a relationship, a contract's renewal clause can auto-trigger while nobody
is watching, and the policy that approved a vendor last year may no longer reflect this year's risk
appetite. The natural and already-anticipated extension of the product (see
`docs/01-product/future-product-vision.md`) is to stop treating compliance as a one-time gate and
start treating it as a continuously running system of record:

- **Continuous supplier monitoring** (working name: JuriSense Monitor) — re-running `SupplierCheck`s
  on a schedule and on external triggers (a new sanctions list publication, a registry status change)
  instead of only at onboarding, so a decision that was correct in month one does not silently go
  stale by month eight without anyone noticing (this closes the exact gap described by `BR-DEC-004`
  and `compliance.review_required` today, but as an ongoing background process rather than an
  event a customer has to think to ask for).
- **Deeper contract intelligence** (working name: JuriSense Contracts) — moving beyond compliance-gate
  extraction (liability, DPA, termination, value) toward full portfolio-level contract analytics:
  obligation tracking across the whole supplier base, renewal-date rollups, clause-language
  benchmarking across contracts and suppliers, and negotiation-support drafting suggestions grounded
  in the same structured-extraction pipeline already built for Gate.
- **Standalone policy management** (working name: JuriSense Policies) — letting a customer's
  Compliance and Legal teams author, simulate, version, and govern policy independently of any single
  workflow, and eventually letting policy packs be shared or benchmarked across the customer base
  (with appropriate anonymization and consent) the way security benchmarks are shared today.
- **Broader third-party risk and privacy compliance** (working names: JuriSense Risk, JuriSense
  Privacy) — extending the same evidence-and-decision model beyond procurement gating into ongoing
  TPRM and LGPD/data-processing compliance programs, which is where the GRC incumbents (Vanta, Drata,
  OneTrust) currently compete — but arriving there already holding contract- and supplier-specific
  evidence those tools do not natively have.
- **Audit and evidence tooling as its own surface** (working name: JuriSense Audit) — exposing the
  Evidence Package / Decision Passport / Audit Trail machinery directly to auditors and regulators as
  a first-class, permissioned consumer, not just as an internal record the customer exports manually.
- **An open developer platform** (working name: JuriSense API) — this is the structurally important
  one. Once the Compliance Engine can reliably answer "APPROVE/REVIEW/BLOCK, with evidence" for a
  normalized supplier+contract context, that capability stops being useful only inside JuriSense's own
  UI. A customer's existing procurement system, CLM tool, or internal portal should be able to call
  JuriSense's decision API directly and get a policy-governed, evidence-backed answer back, the same
  way a payments company calls a fraud-scoring API instead of rebuilding fraud detection in-house.

The common thread across all of these is that JuriSense stops being "a dashboard you check" and
becomes **compliance infrastructure you build on** — an API and event stream other systems and teams
depend on, backed by the same deterministic Policy Engine, the same append-only Evidence & Audit
core, and the same provider-agnostic Trust Layer that JuriSense Gate proves out first. None of this
is speculative scope creep bolted onto a hackathon pitch: it is the same pipeline, the same eight
bounded contexts, and the same domain model (`docs/03-domain/domain-model.md`) extended in the
directions its own architecture already anticipates (Jurisdiction Packs for international expansion,
an `AnchoringProvider` abstraction that outlives any single chain, a `Policy & Compliance` context
that was designed from day one to be evaluated by more than one product surface).

## What does not change

As the product surface grows, three things must not: (1) AI never unilaterally sets a compliance
outcome — only the deterministic Policy & Compliance context does (`AI-004`); (2) every decision
remains reproducible from its recorded evidence and the exact `PolicyVersion` used, forever, not just
for the customer's current contract term; (3) the company only builds what passes the hackathon test
above, scaled to whatever the current planning horizon is — "would a real customer or investor still
want this if there were no more demos to give." Growth is measured by how much real procurement,
legal, compliance, finance, security, and privacy risk the platform is trusted to gate — not by
feature count.
