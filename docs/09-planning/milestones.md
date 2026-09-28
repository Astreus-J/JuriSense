# Milestones

Named milestones, timed relative to **today, 2026-09-27**, against the hackathon judging window
(**opens 2026-11-05, closes 2026-12-05, awards 2026-12-12**). That window is roughly **5.6 weeks**
from today — the timeline is genuinely tight (see `risks.md`, hackathon-timeline risk), so every
milestone below is expressed in **relative week numbers**, not fixed calendar dates. Exact calendar
dates are called out as `TBD` pending team capacity confirmation, per the instruction not to invent
commitments the team hasn't sized.

Week numbering: **Week 0 = 2026-09-27 to 2026-10-03** (this week). Judging opens inside **Week 5**
(2026-11-01 to 2026-11-07). Judging closes inside **Week 9** (2026-11-29 to 2026-12-05). Awards land
in **Week 10** (2026-12-12).

## M1 — Foundation + Identity migration complete

- **Covers**: Phase 0 (Foundation) and Phase 1 (Core Platform) from `roadmap.md`.
- **Target**: end of **Week 1** (relative to today) — i.e., roughly one week of focused work on the
  rename/migration plus the RBAC/platform substrate.
  **Status: TBD / Current preferred option: target end of Week 1 (2026-10-10) / Why undecided:
  depends on how much of the ~2,100-line Accounts rename can be mechanized (search/replace + test
  re-run) vs. requires manual review of every renamed identifier / Resolution: confirm once the
  Phase 0 backlog items are pointed and the team's actual weekly capacity is known / Decision
  artifact: sprint planning notes for the first sprint, once scheduled.**
- **Definition of done**: the exit criteria of Phase 0 **and** Phase 1 in `roadmap.md` are both met
  — renamed Identity & Organizations schema passing all existing tests under new names, `AuditEvent`
  foundation live, RBAC deny-by-default verified, frontend app shell with working invite/login flow,
  local s3mock reachable.
- **Why it matters**: this is the milestone that proves the pivot's foundational bet — that the
  audited Accounts code is genuinely reusable, not a rewrite in disguise — actually holds up in
  practice, before any business-domain feature work begins.

## M2 — Supplier + Contract intelligence working end to end

- **Covers**: Phase 2 (Supplier Intelligence) and Phase 3 (Contract Intelligence), built in
  parallel per `dependencies.md`.
- **Target**: end of **Week 3** (relative to today), assuming Phase 2 and Phase 3 genuinely run
  concurrently as two work-streams starting right after M1. If they cannot run in parallel (e.g., a
  single-engineer team), this milestone realistically slips to **Week 4–5** — flagged here explicitly
  rather than assumed away.
- **Definition of done**: a Procurement-role user can register a supplier and get a normalized
  `SupplierProfile` with sanctions status back; a Legal-role user can upload a contract and get a
  structured, clause-cited `ContractVersion` back. Both independently demoable, without needing the
  Policy Engine to exist yet.
- **Why it matters**: this is the first milestone that produces real, inspectable AI-extraction and
  external-verification output — the two hardest-to-validate technical bets in the product (AI
  extraction accuracy, external source reliability) get real signal here, early enough to still
  adjust course before Policy/Compliance is built on top of them.

## M3 — Policy + Compliance engine working on the demo scenario

- **Covers**: Phase 4 (Policy Engine) and Phase 5 (Compliance).
- **Target**: end of **Week 4** (relative to today) — a deliberately thin one-week window after M2,
  reflecting that this is the highest-technical-risk milestone (the `ADR-004` CEL/JSONLogic spike
  lives here) and the schedule cannot assume it goes smoothly.
- **Definition of done**: the worked examples in `docs/03-domain/policy-engine.md` (`SANC-001`,
  `LGPD-001`, `FIN-003`, `FIN-004`, `LEGAL-008`) are authored as a real published `PolicyVersion` and
  correctly evaluated against at least one real supplier + contract combination from M2, producing a
  deterministic `APPROVE`/`REVIEW`/`BLOCK` outcome with linked evidence.
- **Why it matters**: this is the product's actual core value proposition (executable policy +
  explainable aggregation) working against real data for the first time. If this milestone slips
  materially, it is the clearest early signal that the Hackathon Cut itself is at risk (see
  `risks.md`).

## M4 — Approvals + Evidence + Anchoring (Hackathon Cut complete)

- **Covers**: Phase 6 (Approvals), Phase 7 (Evidence/Audit), Phase 8 (Blockchain) — the entire
  remainder of the Hackathon Cut scope.
- **Target**: end of **Week 5** (relative to today), landing just before or right at the judging
  window's open (**2026-11-05**, itself inside Week 5). This is intentionally the tightest-margin
  milestone in the plan.
  **Status: TBD / Current preferred option: target 2026-11-01–2026-11-03 (a 2–4 day buffer before
  judging opens) / Why undecided: Phase 8's `ADR-007` anchoring-provider spike has an inherently
  unpredictable duration until it is actually attempted / Resolution: re-forecast this date
  immediately after M3 lands, using actual Phase 4/5 velocity as the input, not this document's
  guess / Decision artifact: the spike's own findings write-up, feeding an updated `ADR-007`.**
- **Definition of done**: the exit criteria of Phase 6, 7, and 8 in `roadmap.md` are all met — most
  importantly, a real `Decision` is packaged into an `EvidencePackage`, anchored (or covered by the
  documented fallback), and independently verifiable via the public verification page.
- **Why it matters**: this is the Hackathon Cut. Everything the hackathon submission demonstrates
  must exist by this milestone. It is also the milestone most exposed to the blockchain-integration
  risk and the general hackathon-timeline risk documented in `risks.md` — if only one milestone in
  this document gets contingency buffer, it should be this one.

## M5 — Hackathon submission

- **Covers**: final demo polish, landing-page rewrite completion, submission materials (pitch deck,
  demo video, README), and the actual submission action.
- **Target**: submission-ready by the **start of the judging window, 2026-11-05**, with the
  understanding that judging itself runs through **2026-12-05** and awards land **2026-12-12**. Any
  post-submission fixes during the judging window should be treated as a stabilization buffer, not
  a place to land new Hackathon Cut scope.
- **Definition of done**: the submission is filed with a working public verification page link, a
  demo video covering the full Supplier → Contract → Policy → Compliance → Approval → Decision →
  Evidence → Anchor → Verify pipeline, and an updated root `README.md` reflecting the pivoted
  product (not the legacy legal-ERP description).
- **Why it matters**: this is the externally-visible commitment the whole roadmap through Phase 8
  exists to meet — per `docs/00-project/overview.md`, "the first public milestone of a real
  commercial product — not a disposable demo."

## Summary timeline

| Milestone | Covers | Target (relative) | Falls within calendar week |
|---|---|---|---|
| M1 | Phase 0–1 | End of Week 1 | 2026-10-04 – 2026-10-10 |
| M2 | Phase 2–3 | End of Week 3 (Week 4–5 if not parallelized) | 2026-10-18 – 2026-10-24 |
| M3 | Phase 4–5 | End of Week 4 | 2026-10-25 – 2026-10-31 |
| M4 | Phase 6–8 (Hackathon Cut) | End of Week 5 | 2026-11-01 – 2026-11-07 |
| M5 | Hackathon submission | Start of judging window | 2026-11-05 |
| — | Judging closes | — | 2026-11-29 – 2026-12-05 |
| — | Awards | — | 2026-12-12 |

All calendar-week mappings above are computed from today's date (2026-09-27) and the published
judging window; they are **not** a confirmed team capacity plan. Any milestone marked `TBD` above
should be re-confirmed once actual sprint velocity exists (i.e., after M1), because a five-and-a-half
week runway to judging leaves essentially no slack to absorb a wrong early estimate.
