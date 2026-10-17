# ADR-007 — Blockchain Anchoring Provider Abstraction

## Status
Accepted (spike concluded 2026-10-07, STORY-8.1.1) — see "Spike findings" below. Credentials
provisioned and the adapter switched active 2026-10-15 — see that addendum.

## Context
The mission brief originally assumed Chainlink as the blockchain partner. Research on 2026-09-27
found that the **BLI Legal Tech Hackathon 2 / Legal Hack 2026** (judging 2026-11-05 to 2026-12-05,
awards 2026-12-12) is sponsored by **ICP (Caffeine AI / DFINITY), Constellation Network, and Story
Protocol** — Chainlink was not found among sponsors or bounty partners for this edition.
Constellation's positioning ("immutable anchoring," used in the prior LegalHack for "audit-grade,
multi-chain IP records") is a close conceptual match to JuriSense Gate's Evidence Package /
Decision Passport anchoring need. The user decided (2026-09-27) that the Trust Layer must not be
hard-locked to a single network.

## Decision
Define an **`AnchoringProvider` interface** in `06-blockchain/anchoring-providers.md`:
`submit_hash(evidence_hash) -> anchor_ref`, `get_proof(anchor_ref) -> proof`,
`verify(evidence_hash, proof) -> bool`. All blockchain interaction in the product goes through this
interface; no other code depends on a specific chain SDK. Only **hashes** (Merkle roots of the
Evidence Package) are ever submitted on-chain — never raw contract/supplier data (see
`06-blockchain/privacy.md`).

## Spike findings (2026-10-07, STORY-8.1.1)

The spike attempted Constellation first, per this ADR's own preferred order, and did not need to
fall back to the EVM L2 path or evaluate ICP/Caffeine AI — the finding below explains why, and
also why "attempted" does not yet mean "live."

**Constellation has a purpose-built product for exactly this use case, not just a generic SDK.**
Research found **Digital Evidence Depository (DED)** — "create, sign, and submit cryptographic
fingerprints for document notarization" — with a first-party Python package
(`constellation-digital-evidence-sdk`, confirmed installable, Apache-2.0) and a live, documented
REST API confirmed by hand: `GET https://de-api.constellationnetwork.io/v1/fingerprints/<hash>`
returned exactly the documented 404 JSON shape for an unknown hash, with **no authentication at
all**. That single fact resolves the hardest part of `docs/06-blockchain/verification.md`'s
requirement directly: a third party can check an anchor without ever calling a JuriSense API.

A full adapter was built and tested against this API (mocked transport in tests; the public GET
confirmed live, by hand, outside the test suite) —
`app/evidence/infrastructure/anchoring/constellation_provider.py`. The SDK's `generate_fingerprint`
signs a `document_ref` (our `EvidencePackage.merkle_root`) directly with SECP256K1/RFC8785, exactly
matching the documented wire format; no EVM or ICP path needed to be attempted for comparison,
because this one cost nothing resembling the "high effort, unfamiliar tooling" risk this ADR's
original candidate table flagged as Constellation's main uncertainty.

**What is NOT resolved: provisioning.** `POST /fingerprints` (submission) requires an `X-API-Key`
plus an `org_id`/`tenant_id` that Constellation issues directly — there is no self-service signup
page (confirmed by reading the SDK's own quickstart, which says these are "provided by
Constellation," and the gitbook docs, which document no signup flow). This is a credential handoff,
not an engineering task — tracked as Plane #198, to be requested through the hackathon's
Constellation sponsor channel.

**Decision: Constellation DED is the chosen adapter, activated by configuration once credentials
arrive.** Until then, the project's default `AnchoringProvider` is the transparency-log fallback
this ADR already anticipated as a contingency (`docs/09-planning/risks.md` risk 4) — not because
Constellation failed the spike, but because going live needs a credential this spike could not
self-serve. Both adapters are fully implemented, tested, and interface-identical
(`app.evidence.domain.anchoring.AnchoringProvider`); switching the active one is the same
config-only change `Settings.anchoring_provider` already is for every other provider swap in this
codebase (e.g. the AI Gateway's interim OpenRouter choice, ADR-005's addendum). The EVM L2 and
ICP/Caffeine AI candidates remain documented fallbacks (`docs/06-blockchain/anchoring-providers.md`
§2) but were not built, since Constellation's spike did not fail in a way that required reaching
for them.

## Alternatives Considered
- **Hard-commit to Chainlink now** (original brief): rejected — not a sponsor of this hackathon
  edition, and locking to one chain before validating integration effort risks the hackathon
  deadline for no confirmed benefit. Chainlink CRE/Data Feeds/Functions remain a legitimate future
  `AnchoringProvider` adapter if a customer/partnership reason emerges later.
- **No blockchain component**: rejected by explicit product requirement (Trust Layer is core to the
  Decision Passport's value proposition and to the hackathon's blockchain-track fit).

## Consequences
- Hackathon narrative and product architecture stay decoupled from any single sponsor's roadmap.
- `06-blockchain/*` documents the abstraction and privacy model now; the concrete adapter choice is
  explicitly deferred and tracked, not silently assumed.
- Until Constellation DED credentials were provisioned (Plane #198), every `BlockchainAnchor`'s
  `provider` was `"transparency_log"` — every caller that renders this to a human (the Decision
  Passport, the public verification page) must show it as a labeled fallback, never as a
  blockchain anchor (`docs/09-planning/risks.md` risk 4's non-negotiable labeling requirement). That
  changed 2026-10-15 — see the addendum below — but the labeling requirement itself does not: a
  caller still renders whichever provider is actually active truthfully, never assuming which one
  that is.

## Addendum (2026-10-15) — Constellation DED credentials provisioned, adapter switched active

All 4 Constellation DED credentials (`CONSTELLATION_DED_API_KEY`/`ORG_ID`/`TENANT_ID`/
`PRIVATE_KEY`) arrived and were live-verified 2026-10-12. `Settings.anchoring_provider` was
switched from `transparency_log` to `constellation_digital_evidence` 2026-10-15 — the config-only
change this ADR's own Consequences section anticipated. Verified live the same day: a real
compliance decision's automatic anchor submission called the actual Constellation DED API
(`POST /fingerprints` → 200), and a follow-up `GET` on that fingerprint returned
`"status":"FINALIZED_COMMITMENT"` with a real `batchGlobalSnapshotHash`/`batchMetagraphSnapshotHash`
— genuine inclusion in Constellation's snapshot-based consensus, not merely accepted into an
internal queue. The `transparency_log` adapter remains fully implemented as the fallback if
Constellation DED ever becomes unreachable; it is no longer the default.

This is a runtime configuration value (`ANCHORING_PROVIDER`), not a permanent architectural fact —
anyone citing "which provider is active" in a live demo or pitch should reconfirm it at that moment
rather than relying on this document alone, exactly as `docs/09-planning/risks.md` risk 4's
labeling requirement already implies.

## Addendum (2026-10-16) — Sponsor/bounty correction: Chainlink and RYO-CHAN, not ICP/Constellation/Story

This ADR's Context and `anchoring-providers.md` §2 state, as established fact from 2026-09-27
research, that this hackathon edition is sponsored by ICP (Caffeine AI/DFINITY), Constellation
Network, and Story Protocol, and explicitly *not* Chainlink. **That research pass could not actually
load the live DoraHacks page** (`dorahacks.io/hackathon/legal-hack-2026` returned HTTP 405/403 to
automated fetch) and was built from indirect/historical signals instead — see
`docs/08-hackathon/hackathon-requirements.md`'s original §2 TBDs, which flagged this gap honestly
rather than hiding it.

On 2026-10-16 the user supplied screenshots of the actual live page. The Bounties tab lists exactly
two bounties for this specific edition: **Chainlink** ("Best workflow with CRE — 2x $1,000") and
**RYO-CHAN** ("Autonomous Agents", a crypto-market-intelligence-agent bounty with no legal/compliance
relevance). **Neither Constellation Network, ICP, nor Story Protocol appears as a bounty sponsor on
the live page.** This reverses the 2026-09-27 finding and means this ADR's "why Constellation, not
Chainlink" sponsor-fit reasoning was built on an incorrect premise. Full corrected facts:
`docs/08-hackathon/hackathon-requirements.md` §1.

**Decision (user, 2026-10-16): keep Constellation Network DED as the active `AnchoringProvider`
implementation.** The team is not pivoting to a Chainlink CRE integration for this submission. This
is a deliberate choice, not an oversight — practical reasons that make it the sound call even with
the sponsor premise corrected:

- Constellation DED is already built, tested, and **live-verified end to end** (real `POST
  /fingerprints` → 200, confirmed `FINALIZED_COMMITMENT` on a follow-up `GET`, 2026-10-15 addendum
  above). Chainlink CRE would be a new integration started from zero.
- The submission deadline is 2026-10-31 — about two weeks out as of this addendum. Starting a new
  SDK integration (Chainlink's CRE workflow tooling, Go/TypeScript, a DON-based execution model
  neither this ADR nor the codebase has touched) this close to the deadline is a materially higher
  risk than finishing the packaging work already in flight (`docs/08-hackathon/hackathon-checklist.md`
  §3–4).
- The `AnchoringProvider` abstraction (§1 above) was built sponsor-agnostic by design specifically so
  the concrete provider choice would not gate the rest of the product — that design goal holds
  regardless of which sponsor turns out to be live-listed. Constellation DED remains a genuinely
  sound, independently-verifiable implementation of it on its own technical merits, not only as a
  bounty-fit play.

**What this does change**: any submission material (pitch, write-up, BUIDL page copy) must stop
asserting "Constellation is a confirmed sponsor of this edition" or "we picked Constellation over
Chainlink because Chainlink wasn't a sponsor" as a current fact — that framing is now known false for
this specific edition. The honest framing is: the `AnchoringProvider` abstraction avoids hard-locking
to any one sponsor's roadmap; Constellation DED is the adapter actually built and live-verified;
whether that happens to match a live bounty track is a separate, now-open question the team is
choosing not to chase. **What this does not change**: the architecture, the live-verified
Constellation integration, or the transparency-log fallback — all remain exactly as documented in the
2026-10-15 addendum above.
