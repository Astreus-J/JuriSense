# ADR-007 — Blockchain Anchoring Provider Abstraction

## Status
Accepted (spike concluded 2026-10-07, STORY-8.1.1) — see "Spike findings" below.

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
- Until Constellation DED credentials are provisioned (Plane #198), every `BlockchainAnchor`'s
  `provider` is `"transparency_log"` — every caller that renders this to a human (the Decision
  Passport, the public verification page) must show it as a labeled fallback, never as a
  blockchain anchor (`docs/09-planning/risks.md` risk 4's non-negotiable labeling requirement).
  Flipping `Settings.anchoring_provider` to `"constellation"` the moment credentials arrive
  changes nothing above the `AnchoringProvider` interface.
