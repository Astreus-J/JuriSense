# Hackathon Requirements

> Research pass date: 2026-09-27. Automated fetches against `dorahacks.io` returned HTTP 405/403
> during this research pass (the platform appears to block automated/headless access), so several
> operational details below are explicit TBDs rather than guesses. See section 2.
>
> **Update 2026-10-16 (user-provided screenshots of the live `dorahacks.io/hackathon/legal-hack-2026`
> page)**: most of section 2's TBDs are now resolved with real data — see the corrected facts in
> section 1 and the new section 2.4. **Important correction**: the 2026-09-27 research pass's central
> claim — that this edition is sponsored by ICP/Constellation Network/Story Protocol and *not*
> Chainlink — is **wrong for this edition as it actually stands today**. The live page's Bounties tab
> shows exactly two bounties: **Chainlink** ("Best workflow with CRE") and **RYO-CHAN** ("Autonomous
> Agents") — no Constellation, ICP, or Story Protocol bounty is listed. This directly affects
> `ADR-007`'s sponsor-based reasoning — see that ADR's 2026-10-16 addendum for the full correction and
> what it does and does not change about the architecture already built.

## 1. Confirmed facts

These facts are treated as established input to planning and are not re-researched here.

| Item | Value |
|---|---|
| Event name | BLI Legal Tech Hackathon 2 / Legal Hack 2026 (a.k.a. "Legal Tech Hackathon Edition 2"), organized by the Blockchain Legal Institute with Cogent Law, `www.bli.tools` |
| Platform | DoraHacks — `dorahacks.io/hackathon/legal-hack-2026` |
| Format | Virtual |
| Submission deadline | **2026-10-31, 22:01** (timezone as shown on the platform not confirmed from the screenshot — treat as the platform's own displayed time, verify again close to submission) — this matches the 2026-10-14 user-confirmed date, now with an exact time |
| Judging period | 2026-11-05 to 2026-12-05 *(as previously researched; not re-confirmed against the live page in the 2026-10-16 screenshots — re-verify before relying on it)* |
| Award announcements | 2026-12-12 *(not re-confirmed in the 2026-10-16 screenshots — re-verify)* |
| ~~Sponsors / bounty partners~~ **Live bounty partners as of 2026-10-16** | **Chainlink** ("Best workflow with CRE — 2x $1,000", $2,000 total) and **RYO-CHAN** ("Autonomous Agents", $6,000) — only two bounties exist on the live Bounties tab. ICP/Caffeine AI, Constellation Network, and Story Protocol are **not** currently listed as bounty sponsors for this edition — see the correction note above and `ADR-007`'s 2026-10-16 addendum. |
| Focus theme | "Law. Finance. Compliance." — confirmed verbatim on the live page banner |
| Hackathon tags (live page) | Blockchain, Crypto, Legal, Finance, Compliance, AI, RWA, RegTech |
| Platform technology (live page) | Bitcoin, Ethereum |
| Prize pool (live sidebar stat) | **$20,000 USD** total — the Details page's intro blurb separately says "$10,000+ USD value in bounties, support, and promotion," which reads as generic/templated marketing copy rather than the live total; the sidebar's $20,000 is the more concrete, current figure. The page itself carries a disclaimer: "Prize pool is still developing... may not reflect the actual prize amount... subject to withdraw or change." |
| Prior edition (LegalHack 2025) bounty pool | $32,000+ USD across ICP/Constellation/Story Protocol *(historical fact from the original research pass — does not describe this edition's actual bounty partners, see above)* |
| Admin Grant option | $5,000 *(from the original research pass — not re-confirmed on the live page)* |
| Registered hackers | 464–480 (observed across two 2026-10-16 screenshots taken a short time apart) |
| Builds submitted so far | 1 (as of 2026-10-16) |
| Chainlink | **Is** a bounty sponsor of this edition (confirmed via the live Bounties tab, 2026-10-16) — this **reverses** the original mission-brief correction below, which had found Chainlink absent. See the correction note at the top of this file and `ADR-007`'s 2026-10-16 addendum for what this does and does not change. |
| Today's date (for planning) | 2026-09-27 at the time of the original research pass — roughly 5–9 weeks existed before the judging window opened. As of the 2026-10-16 update, the real deadline (2026-10-31) is roughly 2 weeks out. |

These confirmed facts are the basis for `docs/08-hackathon/submission-plan.md`'s week-by-week
timeline and for `docs/adr/ADR-007-blockchain-anchoring-provider.md`'s sponsor-based reasoning —
though that reasoning needs the 2026-10-16 correction above applied before being taken at face
value.

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
