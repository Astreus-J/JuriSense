# Submission Plan

> Cross-references: `docs/08-hackathon/hackathon-requirements.md` (dates, TBDs),
> `docs/08-hackathon/fallback-mvp.md` (scope), `docs/08-hackathon/demo-scenario.md` (demo content),
> `docs/adr/ADR-007-blockchain-anchoring-provider.md` (anchoring provider spike).

## 1. Submission checklist

This is what must exist by submission time, independent of the exact DoraHacks form fields (still
TBD per `hackathon-requirements.md` §2.3 — this checklist deliberately covers the superset of likely
requirements so nothing is built at the last minute).

- [ ] **Working demo** — deployed (preferred) or, at minimum, a recorded video walkthrough following
      `demo-scenario.md` end to end: Organization → Supplier/CNPJ check → Contract upload → AI
      extraction → Policy Engine evaluation → Decision → human approval → Decision Passport →
      blockchain anchor → public verification page. A recorded video is the fallback if live-deploy
      reliability is a risk close to submission — a working recording beats a flaky live demo.
- [ ] **Pitch deck** — built from `docs/08-hackathon/pitch.md` (problem, solution, why now, why us,
      the ask, closing line), 8–12 slides, readable in under 3 minutes if judges skim it without a
      live narration.
- [ ] **Public GitHub repository** — this repository (or a clean export of the relevant subset),
      public, with this `docs/` tree intact as the project's credibility signal: judges evaluating
      "genuine use of sponsor technology" and "technical execution" can read `ADR-007`,
      `docs/03-domain/domain-model.md`, `docs/03-domain/policy-engine.md`, and
      `docs/adr/ADR-010-decision-aggregation-model.md` directly instead of taking marketing claims on
      faith. A top-level `README.md` should point directly at `docs/00-project/overview.md` and at
      this hackathon documentation tree.
- [ ] **Technical write-up of the blockchain integration** — a focused document (can live in
      `docs/06-blockchain/` once that tree is populated, or be extracted into the BUIDL submission
      text) explaining: the `AnchoringProvider` interface (`ADR-007`), which concrete adapter was
      selected after the Phase 8 spike and why, what exactly gets anchored (`EvidencePackage.merkle_root`
      — never raw contract or personal data, per `docs/06-blockchain/privacy.md`), and how a third
      party independently verifies an anchor via the public verification page. This is the artifact a
      sponsor-bounty judge (Constellation specifically) will read most closely.
- [ ] **Team info** — names, roles, and (if the confirmed submission form asks for it) contact
      details for whoever presents/answers judge questions.
- [ ] **BUIDL / project page content** — written project description, tags, and links, once the
      exact DoraHacks form fields are confirmed (`hackathon-requirements.md` §2.3).
- [ ] **Manual check of `dorahacks.io/hackathon/legal-hack-2026`** — tracks, judging criteria, and
      exact submission format, per the TBDs in `hackathon-requirements.md`. This is a dated task
      below, not left implicit.

## 2. Week-by-week plan (2026-09-27 → 2026-11-05)

Today is 2026-09-27 (Sunday); judging opens 2026-11-05 (Thursday) — a **5.5-week** build window.
Weeks are Sunday-to-Saturday except the final partial week.

### Week 1 — Sep 27 to Oct 3: Foundation + Identity

- Confirm scope against `fallback-mvp.md`; freeze the Hackathon Cut checklist (no scope additions
  after this week without an explicit cut elsewhere).
- Stand up the modular monolith skeleton and multi-tenant `Organization` model (roadmap Phase 0–1).
- Do the manual `dorahacks.io/hackathon/legal-hack-2026` check *early* (not deferred to the last
  week) to catch any track/format surprise while there is still time to react — re-check again in
  Week 5 in case the page changes closer to the deadline.

### Week 2 — Oct 4 to Oct 10: Suppliers + Contracts intake

- `Supplier`, `SupplierProfile`, `SupplierCheck` with at least one real CNPJ/sanctions source
  integration (fallback: manual entry behind a "demo mode" badge — see `fallback-mvp.md` item 2).
- `Document` upload + `Contract`/`ContractVersion` scaffolding (roadmap Phase 2–3 start).

### Week 3 — Oct 11 to Oct 17: AI extraction + Policy Engine

- AI structured extraction producing the normalized evaluation context described in
  `docs/03-domain/policy-engine.md` (value, duration, liability type, DPA presence, personal-data
  processing flag).
- Author and publish the demo `PolicyVersion` with `LGPD-001`, `LEGAL-008`, `FIN-003` (and ideally
  `FIN-004`, `SANC-001`) as real, evaluable `Rule`s (roadmap Phase 3–4).
- **Checkpoint**: by end of this week, a `ContractVersion` should be evaluable against the policy
  and produce a `RuleEvaluation` set, even before the full UI exists.

### Week 4 — Oct 18 to Oct 24: Compliance Engine + Approvals + Decision Passport

- Wire the `ADR-010` aggregation (any BLOCK → BLOCK; else any REVIEW → REVIEW; else APPROVE) end to
  end into a real `ComplianceReview` → `Decision` flow.
- Minimal `ApprovalRequest` human-approval step for REVIEW outcomes (roadmap Phase 5–6).
- First pass at the Decision Passport view/export (roadmap Phase 7).
- **Checkpoint**: the full demo scenario (`demo-scenario.md`) should run manually end to end through
  the Decision Passport, even if the blockchain anchor is still stubbed.

### Week 5 — Oct 25 to Oct 31: Evidence, blockchain anchor, hardening

- Run the ADR-007 technical spike: benchmark Constellation Network's SDK against the EVM-testnet
  fallback (Base Sepolia / Polygon Amoy) for integration effort, cost, and reliability; lock the
  default `AnchoringProvider` adapter for the demo.
- Build `EvidencePackage` (Merkle root) → `BlockchainAnchor` → public verification page (roadmap
  Phase 8 — the Hackathon Cut boundary).
- Second manual check of `dorahacks.io/hackathon/legal-hack-2026` for any late-breaking track/format
  changes.
- Start the pitch deck and technical write-up drafts in parallel with engineering — do not leave
  both for Week 6.
- **Risk buffer**: this is the week most likely to slip (blockchain integrations are the least
  predictable dependency). If the spike shows Constellation is too heavy, fall back to the EVM
  testnet adapter immediately rather than burning further days — the `AnchoringProvider` interface
  makes this swap cheap by design (`ADR-007`).

### Week 6 — Nov 1 to Nov 5: Freeze, record, submit

- **Nov 1–2**: feature freeze. No new scope; only bug fixes and demo-path hardening. Re-run the full
  `demo-scenario.md` walkthrough at least twice, exactly as a presenter would.
- **Nov 2–3**: record the demo video (even if a live deploy also exists, a recorded fallback removes
  live-demo risk on presentation day). Finalize the pitch deck.
- **Nov 3–4**: finish the technical write-up of the blockchain integration; finalize the public
  GitHub repo (clean commit history, README pointing at `docs/00-project/overview.md`).
- **Nov 4**: fill out the BUIDL/project submission page per the (by now hopefully confirmed) format;
  do a full checklist pass against §1 above.
- **Nov 5 (before judging opens)**: submit. Do not submit on the last possible hour if avoidable —
  DoraHacks submission pages can have upload issues under last-minute load.

### Nov 5 – Dec 5: judging window

- No new features expected, but stay reachable for judge questions and be ready to fix a broken
  live-demo link within hours, not days, since the deployed demo (if used instead of only a video)
  needs to keep running for the full judging window, not just launch day.

### Dec 12: award announcement

- Regardless of outcome, this is the trigger point for the post-hackathon narrative in
  `hackathon-strategy.md` §4 — folding the milestone into the next roadmap phases and, separately,
  into go-to-market conversations with early Brazilian customers.

## 3. Ownership and risk notes

- The single highest-risk item is the blockchain anchor (Week 5) — it is the newest, least-exercised
  part of the stack and the one most exposed to a sponsor's SDK maturity. The plan deliberately puts
  it before the freeze week, not during it, so a fallback-provider swap is still possible without
  touching the freeze.
- The single highest-risk *external* dependency is the CNPJ/sanctions source integration (Week 2) —
  see `fallback-mvp.md` item 2 for the explicit manual-entry fallback and the rule that a fallback
  must be visibly labeled, never silently faked.
- Documentation (this tree) is treated as a submission asset, not an afterthought — `README.md`
  should link to it, and the write-up items above are drafted in Week 5, in parallel with
  engineering, specifically so they are not rushed in Week 6.
