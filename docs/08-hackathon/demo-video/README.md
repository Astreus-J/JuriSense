# Demo video — narrated, captioned recording

`jurisense-gate-demo.mp4` (5:34, 6.5 MB) is a real, automated recording of
`docs/08-hackathon/demo-scenario.md`'s full 23-step walkthrough against the actual running
product — not a mockup, not screenshots, not a scripted/staged UI. Every screen, every extracted
field, every compliance decision, and the final blockchain verification shown in the video are
real outputs of the real backend (including a real Gemini AI extraction and a real Constellation
Network anchor + verification — see `docs/adr/ADR-007-blockchain-anchoring-provider.md`).

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
4. **Assembly**: `assemble.py` places each narration clip at its recorded offset (ffmpeg
   `adelay`/`amix`), muxes it onto its video, concatenates the two videos, generates an SRT
   (`captions.srt`) from the same segment text and offsets, and burns the captions in.

## How to re-run it

Needs: `node` + `npm`, `ffmpeg`, `espeak-ng`, and the stack up (`docker compose up -d`) with the
demo tenant seeded (`docker compose exec backend uv run python scripts/seed_demo.py`).

```bash
cd docs/08-hackathon/demo-video
npm install                       # pulls Playwright + a matching Chromium build
node gen_audio.js                 # writes audio/*.wav + durations.json
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
python3 assemble.py               # produces out/jurisense-gate-demo.mp4 + out/captions.srt
```

`record.js` is idempotent-safe to re-run (it never deletes anything), but each run needs its own
CNPJ as above, and leaves behind a harmless, permanent "CloudDocs Software Ltda." supplier (with
its own contract/decision/evidence trail) in whatever database it targets — fine for a local/dev
demo tenant, not something to run against a real customer's database.

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
- **Synthetic**: only the narration voice (`espeak-ng`, not a human or natural-sounding TTS voice).

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

See `docs/08-hackathon/hackathon-checklist.md` for the full status tracking of these.
