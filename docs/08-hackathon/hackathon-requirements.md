# Hackathon Requirements

> Research pass date: 2026-09-27. Automated fetches against `dorahacks.io` returned HTTP 405/403
> during this research pass (the platform appears to block automated/headless access), so several
> operational details below are explicit TBDs rather than guesses. See section 2.

## 1. Confirmed facts

These facts are treated as established input to planning and are not re-researched here.

| Item | Value |
|---|---|
| Event name | BLI Legal Tech Hackathon 2 / Legal Hack 2026 |
| Platform | DoraHacks — `dorahacks.io/hackathon/legal-hack-2026` |
| Judging period | 2026-11-05 to 2026-12-05 |
| Award announcements | 2026-12-12 |
| Sponsors / bounty partners | ICP (Caffeine AI / DFINITY), Constellation Network, Story Protocol |
| Focus theme | "Law. Finance. Compliance." — intersection of blockchain, legal tech, and global commercial applications |
| Prior edition (LegalHack 2025) bounty pool | $32,000+ USD across the same three partners |
| This edition's stated value | $50,000+ USD in bounties, support, and promotion |
| Individual bounty range | $1,000–$25,000 |
| Admin Grant option | $5,000 |
| Chainlink | **Not found** as a sponsor of this edition — this corrects the original mission brief, which had assumed Chainlink as the blockchain partner (see `docs/adr/ADR-007-blockchain-anchoring-provider.md` for the resulting architecture decision) |
| Today's date (for planning) | 2026-09-27 — roughly 5–9 weeks exist before the judging window opens |

These confirmed facts are the basis for `docs/08-hackathon/submission-plan.md`'s week-by-week
timeline and for `docs/adr/ADR-007-blockchain-anchoring-provider.md`'s sponsor-based reasoning.

## 2. Explicit TBDs

Three operationally important items could not be confirmed via automated fetch during this research
pass. Each is recorded here in the required TBD format rather than assumed, invented, or silently
skipped.

### 2.1 Exact tracks

Status: TBD
Current preferred option: assume the submission competes as a general "Law. Finance. Compliance."
entry eligible for whichever bounty tracks Constellation Network sponsors (given the genuine
`AnchoringProvider` fit established in `ADR-007` and `hackathon-strategy.md`), and do not assume
eligibility for any ICP/Caffeine AI- or Story Protocol-specific track unless the confirmed track
description makes a real product fit obvious.
Why undecided: `dorahacks.io/hackathon/legal-hack-2026` returned HTTP 405/403 to automated fetch
attempts during this research pass (2026-09-27); the specific track names, per-track eligibility
rules, and per-track prize amounts for the 2026 edition were not retrievable.
Resolution: check `dorahacks.io/hackathon/legal-hack-2026` directly, close to submission, since
automated fetch was blocked during this research pass.
Decision artifact: this section of `hackathon-requirements.md`; update `submission-plan.md`'s
checklist once tracks are confirmed if a specific track requires additional submission material.

### 2.2 Judging criteria

Status: TBD
Current preferred option: build to the criteria implied by the theme and by the sponsor
positioning already documented — technical depth, genuine (not decorative) use of sponsor
technology, real-world applicability to a named market (Brazil-first B2B compliance), and
auditability/verifiability as the differentiating angle — since these are the dimensions every
piece of evidence gathered so far (theme description, prior-edition project patterns, sponsor
positioning statements) consistently points toward.
Why undecided: the same automated-fetch block prevented retrieval of an official, itemized judging
rubric (e.g., weighted categories like "innovation," "technical execution," "market viability,"
"sponsor tech integration") for the 2026 edition specifically.
Resolution: check `dorahacks.io/hackathon/legal-hack-2026` directly, close to submission, since
automated fetch was blocked during this research pass.
Decision artifact: this section of `hackathon-requirements.md`; if an official rubric surfaces with
materially different weighting than assumed here, revisit the emphasis in `pitch.md` accordingly
before the pitch is finalized.

### 2.3 Submission format

Status: TBD
Current preferred option: prepare for the superset of formats DoraHacks hackathons commonly require
— a BUIDL (project) page with a written description, a public GitHub repository link, a demo video
(assume a hard cap in the 3–5 minute range unless the confirmed page states otherwise), and
optionally a live/deployed demo link — so that whatever the confirmed requirement turns out to be,
the needed asset already exists. See `submission-plan.md` for how this shapes the week-by-week plan.
Why undecided: the same automated-fetch block prevented retrieval of the exact submission form
fields, file/video format constraints, and hard deadline time (date-only vs. a specific time zone
cutoff) for `legal-hack-2026`'s BUIDL submission page.
Resolution: check `dorahacks.io/hackathon/legal-hack-2026` directly, close to submission, since
automated fetch was blocked during this research pass.
Decision artifact: this section of `hackathon-requirements.md`; `submission-plan.md`'s final-week
checklist should be re-verified against the confirmed submission form fields before Nov 5.

## 3. Why this matters operationally

None of the three TBDs block starting work: the Hackathon Cut scope (`fallback-mvp.md`), the demo
script (`demo-scenario.md`), and the sponsor-technology evaluation (`hackathon-strategy.md`) do not
depend on knowing the exact track list or rubric weighting. What the TBDs *do* gate is the final
1–2 weeks of submission-packaging work (which exact assets to produce, in which format, against
which deadline time) — which is why `submission-plan.md` schedules a manual verification of this
page explicitly as a dated task rather than leaving it implicit.
