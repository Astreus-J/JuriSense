# Pitch

> Source material: `docs/00-project/overview.md`, `docs/08-hackathon/demo-scenario.md`,
> `docs/adr/ADR-007-blockchain-anchoring-provider.md`. This is the narrative script for the pitch
> deck built in `docs/08-hackathon/submission-plan.md`; slide-by-slide layout is left to whoever
> builds the deck, but the content and ordering below should not be rewritten from scratch.

## Problem (30 seconds)

Every growing company buys from outside vendors constantly — SaaS tools, consultancies, cloud
providers, outsourced teams. Before signing, someone is supposed to check: is this supplier real and
in good standing? Are they on a sanctions list? Does the contract have a data-processing agreement if
they'll touch personal data? Is the liability clause reasonable? Is the value big enough to need
Legal's sign-off?

In practice, that checking happens across Procurement, Legal, Compliance, Finance, Security, and
Privacy — coordinated by email and spreadsheets, with no single reproducible record of *why* a
vendor was approved. Ask "why did we approve this vendor's unlimited-liability clause?" six months
later, and the honest answer is usually "someone probably looked at it." That is not a process — it's
an audit and legal liability waiting to surface at the worst possible time, and it does not scale
past a handful of contracts a month.

## Solution (30 seconds)

JuriSense Gate turns that fragmented, manual, unauditable process into one pipeline: supplier
verification against official sources → AI-structured contract extraction → evaluation against the
company's own **executable** policy rules → a deterministic **APPROVE / REVIEW / BLOCK** decision,
always with WHY, EVIDENCE, POLICY, SOURCE, RISK, REQUIRED ACTION, APPROVER — never a bare status →
routed human approval when a rule requires it → a **Decision Passport** that packages the entire
evidentiary trail → a hash of that evidence anchored on a public, tamper-evident ledger, so anyone —
an auditor, a regulator, an acquirer's due diligence team — can independently verify the decision
wasn't altered after the fact.

AI reads and extracts; it never decides. The Policy Engine's aggregation is simple enough to explain
to a compliance team in one sentence — *any BLOCK wins* — and every decision is reproducible months
or years later from its recorded rule evaluations and the exact policy version used.

## Why now (30 seconds)

Three trends are converging, and none of them existed together five years ago: **AI** finally makes
structured extraction from real, messy contracts fast and cheap enough to run on every vendor, not
just the biggest ones. **Compliance automation** has proven commercial demand (Vanta, Drata, OneTrust
built real businesses on "turn manual compliance checklists into software") but nobody has combined
that with contract intelligence and an *executable* policy layer specifically for the
supplier-onboarding moment. And **blockchain-based evidence anchoring** has matured from a novelty
into a genuinely useful, cheap way to prove "this record hasn't been altered" to a party who does not
trust your internal database — which is exactly the trust gap that makes compliance audits painful
today. JuriSense Gate sits at the intersection of all three, which is also exactly this hackathon's
stated focus: Law, Finance, Compliance, at the intersection of blockchain and legal tech.

## Why us (30 seconds)

We are not building a generic global TPRM tool and hoping Brazil is a rounding-error market later —
we are building **Brazil-first**, on purpose: CNPJ-based supplier identity, Brazilian sanctions and
registry sources (CEIS/CNEP/CEPIM), and LGPD compliance are first-class from day one, targeting
technology companies with 50–1,000 employees that have real procurement volume and no dedicated TPRM
tooling today — a segment every existing competitor (Vanta, Drata, OneTrust, Ironclad, Harvey,
Spellbook, Norm AI) treats as an afterthought at best. And the technical core is not superficial: the
Policy Engine compiles rules to CEL with a deterministic, order-independent aggregation algorithm
(documented and reasoned about explicitly, not ad hoc), and the Evidence/Decision Passport model was
designed around a real question — "can this survive an audit two years from now, and can a third
party verify it without trusting us?" — before a single line of blockchain code was written.

## The ask

To hackathon judges: evaluate us on whether the Policy Engine's decision logic and the evidence/
anchoring model actually hold up under questioning — they are built to. To the Constellation Network
bounty specifically: we adopted the `AnchoringProvider` abstraction and evaluated Constellation as
our default adapter for real architectural reasons, documented in `ADR-007`, not to chase a bounty
line item. To early Brazilian tech companies watching this space: this is not a hackathon toy that
disappears on December 13th — it is milestone one of a company being built to solve a real, currently
unsolved procurement-compliance gap in this exact market segment.

## Closing line

> Turn contracts, supplier data and company policies into auditable compliance decisions.

That is JuriSense's core product principle, stated once in `docs/00-project/overview.md`, and it is
the entire pitch in a single sentence: every claim in this deck — the AI extraction, the policy
engine, the blockchain anchor — exists only in service of making that sentence true, verifiably, for
every contract a company signs.
