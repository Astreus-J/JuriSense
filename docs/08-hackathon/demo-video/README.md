# Demo video — narrated recording

`jurisense-gate-demo.mp4` (4:23, natural-voice narration, no burned-in captions, cut 2026-10-18)
is a **highlights cut** of a real, automated recording of
`docs/08-hackathon/demo-scenario.md`'s full 23-step walkthrough against the actual running
product — not a mockup, not screenshots, not a scripted/staged UI. Every screen, every extracted
field, every compliance decision, and the final blockchain verification shown in the video are
real outputs of the real backend (including a real Gemini AI extraction and a real Constellation
Network anchor + verification — see `docs/adr/ADR-007-blockchain-anchoring-provider.md`).

The hackathon submission has a 5-minute hard cap. The full walkthrough recording runs 11:40 (most
of that is real AI-extraction wait time baked into the raw footage, not narration), so
`jurisense-gate-demo.mp4` keeps only the 14 of 18 segments with real demo impact — supplier
create/check, contract upload, the real AI extraction result, the BLOCK decision, the correction,
the REVIEW decision, approval, the Decision Passport, the anchor note, opening the public verify
page, and the live blockchain verification — and drops pure loading/transition segments
(extraction spinners, "review started" pages). See "Highlights cut" below.

## How it was made

1. **Screen recording**: [Playwright](https://playwright.dev) (`record.js`) drives a real headless
   Chromium browser through the entire demo script against `docker compose`'s running stack
   (`http://localhost:3000`) — login, create a supplier, upload a contract, watch AI extraction
   run, trigger a compliance review, see the BLOCK decision, correct the contract, see it move to
   REVIEW, approve it as Legal, open the Decision Passport, and verify the blockchain anchor. Two
   video files come out (one per browser context — admin, then the Legal approver), because
   switching users needs a fresh context.
2. **Narration**: `segments.js` holds the English narration text per step (same content as
   `docs/08-hackathon/demo-video-script.md`). `gen_audio.js` synthesizes each line with
   `espeak-ng` (a local, offline, robotic-sounding TTS — not a natural voice; no natural-voice TTS
   was available in the build environment) and measures each clip's exact duration.
3. **Timing**: `record.js` uses those exact durations as the on-screen "dwell" time after each
   action completes, and additionally records (`timeline.json`) the real wall-clock offset, inside
   each video file, at which the UI actually reached the state the narration describes — this
   absorbs the unpredictable extra time real actions take (login, file upload, and especially real
   AI extraction latency), so the audio placed in the next step lines up with what's on screen
   rather than drifting from narration text alone.
4. **Assembly**: `assemble_natural.py` places each narration clip at its recorded offset (ffmpeg
   `adelay`/`amix`), muxes it onto its video, and concatenates the two videos into the full,
   11:40 walkthrough (not committed — see "Highlights cut" below for what actually ships).
   `assemble.py` is the older equivalent for the original `espeak-ng` narration and still burns
   in captions from an SRT; the natural-voice pipeline doesn't use captions at all.

## How to re-run it

Needs: `node` + `npm`, `ffmpeg`, and the stack up (`docker compose up -d`) with the demo tenant
seeded (`docker compose exec backend uv run python scripts/seed_demo.py`). `node_modules/`
(pulled by `npm install`, including a matching Chromium build via
`npx playwright install chromium`) isn't committed, so a fresh checkout needs that step re-run
once.

```bash
cd docs/08-hackathon/demo-video
npm install                       # pulls Playwright
npx playwright install chromium   # pulls a matching Chromium build (not committed)
# record.js's CNPJ constant must be a fresh, checksum-valid value each run — decisions
# are append-only (DB trigger), so a prior run's CloudDocs supplier/contract/decision
# chain can never be deleted, only left in place; reusing the same CNPJ would create a
# second "CloudDocs Software Ltda." supplier rather than failing cleanly. Generate one:
python3 -c "
def cd(d,w): 
    r = sum(int(x)*y for x,y in zip(d,w)) % 11
    return '0' if r < 2 else str(11-r)
import random
base = '98765432' + str(random.randint(2,9999)).zfill(4)
f = cd(base, (5,4,3,2,9,8,7,6,5,4,3,2))
print(base + f + cd(base+f, (6,5,4,3,2,9,8,7,6,5,4,3,2)))
"
# paste that into record.js's `const CNPJ = "...";` line, then:
node record.js                    # produces video/*.webm + timeline.json + run-info.json
python3 assemble_highlights.py    # produces jurisense-gate-demo.mp4 (<=5min, no captions)
```

`record.js` is idempotent-safe to re-run (it never deletes anything), but each run needs its own
CNPJ as above, and leaves behind a harmless, permanent "CloudDocs Software Ltda." supplier (with
its own contract/decision/evidence trail) in whatever database it targets — fine for a local/dev
demo tenant, not something to run against a real customer's database. `video/` accumulates one
`page@<hash>.webm` pair (admin + legal context) per run and is never cleaned up automatically;
both `assemble_natural.py` and `assemble_highlights.py` hardcode the filenames of the pair to use
(`ADMIN_VIDEO`/`LEGAL_VIDEO` near the top of each), so after a re-run, update those in both scripts
to the newest pair in `video/` before assembling — the larger/more-recently-modified file of the
pair is the admin context (the long walkthrough), the smaller one is the legal context (the short
approval+verify segment).

`durations.json`/`audio/`/`gen_audio.js` (`espeak-ng`) are the original, robotic-voice pipeline, kept
for reference but superseded by `durations_natural.json`/`audio_natural/`/`gen_presentation_audio.py`
(Gemini TTS).

## Highlights cut

The hackathon submission has a 5-minute hard cap, and the full 18-segment walkthrough — even with
natural-voice narration — runs 11:40, mostly because `timeline.json`'s offsets include real AI
extraction wait time (the script actually waits for the real backend, up to 180s per upload), not
just narration length. `assemble_highlights.py` is what actually produces the committed
`jurisense-gate-demo.mp4`: it keeps a curated, ordered subset of `HIGHLIGHTS` (currently 14 of the
18 segment ids — edit that list directly to change which moments are included), and for each one
cuts a real-footage clip starting at that segment's exact `timeline.json` offset (the moment the
UI actually reached that state), trimmed to that segment's natural-voice narration length plus a
`BUFFER_S` (1.3s). Every frame is still genuinely real product footage — segments are just not
played in real time, so idle waiting (extraction spinners, "review started" transition pages) never
appears. No subtitles/captions are generated or burned in. Re-run it any time after
`assemble_natural.py` or directly after `node record.js` (it reads `video/*.webm` +
`timeline.json` + `durations_natural.json` + `audio_natural/*.wav` directly, not
`assemble_natural.py`'s output).

## Standalone narration audio (natural voice)

`gen_presentation_audio.py` generates the narration alone (no video) using Gemini's native
TTS (`gemini-2.5-flash-preview-tts`, voice "Kore") instead of `espeak-ng` — a real, natural-
sounding voice, for use as a standalone audio track or to practice the presentation against.
This corrects the note above: natural-voice TTS *is* available via the same `GEMINI_API_KEY`
already configured for extraction (`backend/.env`), it just wasn't tried until 2026-10-17.

**Done: `presentation-narration.mp3`** (4:32, all 18 segments, one consistent voice throughout).
Built across two days: 12 of 18 segments finished 2026-10-17, then the free-tier TTS quota on this
key ran out (confirmed real, not just request pacing — waiting up to 120s mid-run never recovered
it that day). By explicit decision, the remaining segments were not filled in with the `espeak-ng`
fallback, so the presentation would stay one consistent voice rather than mixing a natural and a
robotic one. The quota had reset by 2026-10-18 and the remaining 6 segments (`approval` through
`close`) completed without a single retry. `audio_natural/*.wav` (the 18 individual segments) and
`presentation-narration.mp3` are committed; the uncompressed intermediate
`presentation-narration.wav` is not (same audio, just 5x the size — regenerate it locally with
`gen_presentation_audio.py` if you need the lossless version). Re-running the script is still safe
and idempotent if any segment ever needs to be redone — it skips every
`audio_natural/<NN>_<id>.wav` that already exists.

## What's genuinely real vs. what's staged

- **Real**: every UI screen, the AI extraction (Gemini — see `ai_execution` on the Decision
  Passport), the policy evaluation and BLOCK/REVIEW outcomes, the approval flow, the Decision
  Passport contents, and the final "Verified" result and Constellation anchor timestamp.
- **Fictional, labeled as such throughout**: "Acme Tecnologia Ltda." and "CloudDocs Software
  Ltda." are the same fictional demo organizations used in `demo-scenario.md` and the generated
  contracts in `docs/08-hackathon/demo-assets/contracts/`.
- **Synthetic**: only the narration voice (Gemini TTS, a natural-sounding but still synthetic
  voice, not a human one).

## Found and fixed while building this

Recording the real walkthrough (rather than staging screenshots) surfaced several real bugs, all
fixed in the same pass this video was built in:

- A stalled-response hang in the AI Gateway's HTTP client that could leave a worker process stuck
  indefinitely (`app/ai_services/infrastructure/openrouter_gateway.py`,
  `app/ai_services/infrastructure/gemini_gateway.py`).
- A dead OpenRouter fallback model slug that had silently 404'd on every call
  (`app/core/config.py`).
- A frontend crash when `fields.parties.value` isn't an array
  (`frontend/src/components/contracts/ExtractedDataView.tsx`) and when a `date` field isn't a
  parseable ISO date (`frontend/src/lib/format.ts`) — both now degrade gracefully instead of
  crashing the page, and the AI extraction prompt (`app/ai_services/infrastructure/
  prompt_builder.py`) was clarified to reduce how often a provider gets either shape wrong.
- A Next.js hydration race where a click on the "Approve" button could silently do nothing if it
  landed before the client component finished hydrating.
- Confirmed there is no UI path to find a Decision's id after approving a REVIEW-outcome request —
  `record.js` queries the database directly to get it, the same kind of legitimate pre-staging
  `demo-scenario.md` already documents for the blockchain anchor.

Re-recording on 2026-10-18 (after merging in the login-screen redesign and other frontend work)
surfaced two more real bugs in `record.js` itself, both fixed in the same commit:

- The redesigned split-card login nests its "Show password" toggle button inside the same
  `<label>` as the password input, so `getByLabel("Password")` started matching two elements
  instead of one — scoped to `getByRole("textbox", { name: "Password" })` instead.
- The Approvals page now shows a confirmation modal ("Approve this request?") before actually
  submitting an approval — the script was clicking the row's "Approve" button and immediately
  waiting for the API response, which now only opens the modal; fixed by clicking the modal's own
  "Approve request" button before waiting for the response.

See `docs/08-hackathon/hackathon-checklist.md` for the full status tracking of these.
