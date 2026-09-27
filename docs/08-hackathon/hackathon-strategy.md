# Hackathon Strategy

> Cross-references: `docs/00-project/overview.md`, `docs/adr/ADR-007-blockchain-anchoring-provider.md`,
> `docs/03-domain/domain-model.md`, `docs/03-domain/policy-engine.md`, `docs/adr/ADR-010-decision-aggregation-model.md`,
> `docs/09-planning/roadmap.md` (roadmap phases themselves are owned by that document; this file only
> references the phase boundary relevant to the hackathon).

## 1. What we are submitting

We are **not** submitting a hackathon toy built to look impressive for five minutes and then
discarded. We are submitting the **Hackathon Cut** of JuriSense Gate: the first eight phases of a
twelve-phase product roadmap, built as real, working software with a real domain model
(`docs/03-domain/domain-model.md`), a real deterministic decision algorithm (`ADR-010`), and a real
(if minimal) blockchain evidence-anchoring integration (`ADR-007`). Per `docs/00-project/overview.md`,
the roadmap has an explicit **Hackathon Cut after Phase 8 (Evidence/Audit + a working blockchain
anchor)** — that is precisely the submission boundary. Everything through that cut must actually
run end-to-end; everything after it (continuous monitoring, deeper contract intelligence,
international jurisdiction packs, standalone policy management as a product, etc.) is explicitly
out of scope for the submission and described as *future work*, not implied to already exist.

Concretely, what gets demoed and judged is the full pipeline from `docs/00-project/overview.md`:

```
Supplier → Company verification → Contract ingestion → AI structured extraction →
Policy Engine → Compliance Engine → APPROVE/REVIEW/BLOCK → Human approval (when required) →
Decision Passport → Audit Trail → Blockchain verification (evidence anchoring)
```

The exact scope checklist and per-item fallback plan is `docs/08-hackathon/fallback-mvp.md`; the
literal walkthrough a presenter follows is `docs/08-hackathon/demo-scenario.md`. This document is
about *why* this scope, *why* this hackathon, and *why* these sponsor technologies — the strategic
layer underneath those two operational documents.

## 2. Why this hackathon fits the product (not the other way around)

The temptation in any hackathon is to reverse-engineer a product idea from the sponsor list. We are
doing the opposite: JuriSense Gate was conceived as a standalone company (see
`docs/00-project/overview.md` — "the first commercial product built on it is JuriSense Gate") before
this specific hackathon was chosen as the venue for its first public milestone. The fit is genuine,
not manufactured, for three concrete reasons:

1. **The theme is literally the product.** BLI Legal Tech Hackathon 2 / Legal Hack 2026's stated
   focus is "Law. Finance. Compliance." at the intersection of blockchain, legal tech, and global
   commercial applications. JuriSense Gate's one-line description is "turn contracts, supplier data
   and company policies into auditable compliance decisions" — it *is* law (contract analysis),
   finance (contract value thresholds, `FIN-003`/`FIN-004` rules), and compliance (LGPD, sanctions
   screening, policy rule evaluation), unified by a blockchain-backed trust layer. There is no
   theme-stretching required.
2. **The judging window is a real deadline for a real milestone.** Judging runs 2026-11-05 to
   2026-12-05 with awards on 2026-12-12. That is a legitimate forcing function to get Phases 0–8 of
   the roadmap working end-to-end on a compressed timeline — which is work the company needs done
   regardless of the hackathon outcome.
3. **The blockchain-trust-layer angle is a pre-existing architectural decision, not a hackathon
   add-on.** `docs/00-project/overview.md` states the product's core promise is "auditability that
   survives time and organizational memory loss," and that a hash of the Evidence Package anchored
   on a public, tamper-evident ledger gives a verifiable answer to "was this evidence altered after
   the fact?" that a purely internal database log cannot give an external auditor. That need exists
   with or without a hackathon; the hackathon is simply where we get pushed to actually build the
   anchor instead of leaving it as an architecture diagram.

## 3. Using sponsor technology honestly

The instruction we are following here is blunt and worth stating plainly: **do not integrate a
sponsor's technology to chase bounty count if it does not genuinely serve the product.** A judge who
has seen a hundred hackathon projects can tell the difference between an integration that does real
work and one that exists to tick a box, and a bolted-on integration is also, simply, wasted
engineering time we do not have. Below is the honest evaluation of each of the three sponsors —
ICP/Caffeine AI (DFINITY), Constellation Network, and Story Protocol.

### 3.1 Constellation Network — genuine architectural fit

This is not decoration. `ADR-007` already defines an `AnchoringProvider` interface
(`submit_hash(evidence_hash) -> anchor_ref`, `get_proof(anchor_ref) -> proof`,
`verify(evidence_hash, proof) -> bool`) that every blockchain interaction in the product must go
through — the Trust Layer was explicitly designed to be provider-agnostic *before* any sponsor was
locked in, precisely so we would not be dependent on one chain's roadmap. Constellation is the
**current preferred candidate** for the concrete default adapter behind that interface, per ADR-007's
resolution, for reasons that hold regardless of the hackathon: Constellation's own positioning is
"immutable anchoring," which is exactly what `EvidencePackage.merkle_root` → `BlockchainAnchor`
needs — submit a hash, get a durable reference, let anyone independently verify it later. In the
prior LegalHack, projects combining Story Protocol IP licensing + ICP escrow + Constellation
anchoring produced "audit-grade, multi-chain IP records," which validates that Constellation's
tooling has already been exercised successfully for a structurally similar problem (anchor a hash,
prove it later) in this exact hackathon ecosystem.

The decision is **not yet final** — ADR-007 correctly keeps its status as "Proposed, pending
technical spike," because the real determinant is whether Constellation's SDK integration effort
fits inside the remaining build time. The Phase 8 technical spike (see `fallback-mvp.md` item 9)
will benchmark it directly against a generic EVM-compatible L2 testnet (Base Sepolia or Polygon
Amoy) — the safest fallback if Constellation's tooling proves too heavy — before locking the
hackathon demo's default provider. Either outcome keeps the same interface above it in the stack;
what changes is only which adapter answers `submit_hash`.

### 3.2 ICP / Caffeine AI — evaluated, no clear fit beyond the fallback role ADR-007 already gives it

We looked for a genuine use, and found a weak one at best. ICP/Caffeine AI's positioning is
no-code/low-code application hosting — genuinely useful for spinning up a full-stack app quickly,
but that is not what the Trust Layer needs. The Trust Layer needs a component that can
(a) accept a hash, (b) return a durable, publicly verifiable reference to it, and (c) let a third
party independently confirm the hash was anchored at a point in time. "Host an app" and "anchor a
hash" are different problems, and ICP's canister/app-hosting model is a heavier, less direct fit for
the second one than either Constellation's anchoring positioning or a minimal EVM smart contract.
ADR-007 already reflects this honestly: ICP/Caffeine AI is listed as the **third**-priority
candidate, "evaluated only if the spike shows unusually low integration effort," precisely because
its core strength does not map cleanly onto what `AnchoringProvider` requires.

One secondary idea was considered and explicitly rejected: hosting the public verification page
(see `demo-scenario.md`, step "public verification page") on Caffeine AI instead of alongside the
rest of the stack. This would not be a real use of ICP's differentiated capability — a static or
lightly dynamic verification page has no dependency on no-code app hosting, and building it there
solely to claim an ICP integration is exactly the "bolt it on for a bounty" pattern this strategy
rejects. If, during the Phase 8 spike, ICP/Caffeine AI turns out to make the anchor adapter itself
unusually cheap to build, we will use it as the default adapter and say so plainly. Short of that,
we are not forcing an ICP integration into the submission, and the write-up will state this
directly rather than implying a fit that is not there.

### 3.3 Story Protocol — evaluated, no clear fit

Story Protocol's core value proposition is on-chain IP licensing and provenance for creative/media
assets (registering an IP asset, defining licensing terms, tracking derivative works and royalties).
JuriSense Gate's domain model (`docs/03-domain/domain-model.md`) has no entity that resembles a
licensable IP asset: a `Contract`, `ContractVersion`, and `Clause` are records *about* an agreement
between an organization and a supplier — they are compliance evidence, not creative works whose
licensing terms need on-chain registration and enforcement. The nearest theoretical bridge — "treat
a `PolicyVersion` or a `Decision` as IP and register it with Story Protocol" — does not correspond to
any real business need: organizations do not license their compliance policies to third parties, and
a `Decision`'s value is its auditability (covered by `EvidencePackage` + `BlockchainAnchor`), not its
IP provenance. Forcing this integration would be integration theater: technically callable, narratively
incoherent, and a drain on the limited build time better spent hardening the Policy Engine and the
Constellation/EVM anchor.

**Conclusion**: beyond Constellation as the `AnchoringProvider` default, there is no clear genuine
fit for ICP/Caffeine AI or Story Protocol in the Hackathon Cut scope. We say this plainly in the
submission write-up rather than inventing a superficial integration — a judge evaluating "genuine
use of sponsor technology" should read that honesty as a signal of technical judgment, not as a
missed opportunity. This does not preclude a real ICP or Story Protocol integration for a *specific
future bounty track* if the confirmed track list (see `hackathon-requirements.md`, TBD item) reveals
a track/prize structured around one of them in a way that maps to a genuine future product need
(e.g., a jurisdiction-pack-specific IP-licensing compliance module, which does not exist today and
is not invented for this hackathon) — that evaluation is deferred to when the track list is
confirmed, not decided speculatively here.

## 4. Post-hackathon narrative

JuriSense Gate is explicitly framed, in `docs/00-project/overview.md`, as "the hackathon submission
[serving] as the first public proof point" within a larger commercial strategy: "land technology
companies in Brazil with real procurement volume and no TPRM tooling today... then expand toward
larger/regulated buyers and international jurisdiction packs." The hackathon is milestone one, not
the whole project. Two concrete things follow from that framing, and both should show up in the
pitch and the write-up:

1. **The roadmap does not stop at Phase 8.** Phases 9–12 (continuous supplier monitoring, deeper
   contract intelligence, standalone policy management, broader third-party risk tooling, an open
   developer platform — see `docs/01-product/future-product-vision.md`) are real, planned, and
   documented, not hand-waved. The submission should say what comes next, concretely, not just
   "we'll keep building."
2. **The guiding question for every feature — hackathon or not — is stated in the overview
   document**: *"If the hackathon ended tomorrow, would it still be worth building this as a
   company?"* Every scope decision in `fallback-mvp.md` and every line in `pitch.md` should be able
   to answer "yes" to that question. Anything that only exists to look good for five minutes of
   judging and has no post-hackathon life (e.g., a Story Protocol integration bolted on for bounty
   count) fails that test and is excluded on that basis, independent of the sponsor-fit analysis
   above.

The bounty money and award announcement (2026-12-12) matter operationally — they are a credible early
revenue/runway signal for a pre-seed company — but the submission's real audience is threefold:
hackathon judges, potential early Brazilian customers who see a working product, and potential
co-founders/early hires who see technical depth (the policy engine's deterministic aggregation model,
the evidence/anchoring design) rather than a demo built to be thrown away.
