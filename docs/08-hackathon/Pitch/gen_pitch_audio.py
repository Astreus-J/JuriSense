"""Generates the pitch narration as natural-sounding speech via Gemini's native TTS
(gemini-2.5-flash-preview-tts, voice "Kore") -- the same model and voice used for the
demo video's narration (docs/08-hackathon/demo-video/gen_presentation_audio.py), so both
videos sound like the same presenter. One segment per pitch-deck slide (segments.js),
written one WAV per segment plus a concatenated pitch-narration.mp3, with a short pause
between segments. Safe to re-run: skips any audio_natural/<NN>_<id>.wav that already
exists.
"""
import base64
import json
import subprocess
import time
import wave
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "audio_natural"
OUT_DIR.mkdir(exist_ok=True)

with open("/home/santos/Astreus_dev/JuriSense/backend/.env") as f:
    GEMINI_KEY = next(
        line.split("=", 1)[1].strip() for line in f if line.startswith("GEMINI_API_KEY=")
    )

segments = json.loads(
    subprocess.run(
        ["node", "-e", "console.log(JSON.stringify(require('./segments.js')))"],
        cwd=HERE, capture_output=True, text=True, check=True,
    ).stdout
)

URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-preview-tts:generateContent"
)
VOICE = "Kore"


def synth(text: str) -> bytes:
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }
    for attempt in range(8):
        try:
            r = httpx.post(URL, params={"key": GEMINI_KEY}, json=payload, timeout=60)
        except httpx.TimeoutException:
            print(f"    timeout, retry {attempt + 1}")
            time.sleep(3)
            continue
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"    429 rate-limited, waiting {wait}s")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        return base64.b64decode(b64)
    raise RuntimeError("exhausted retries")


wav_paths = []
for i, seg in enumerate(segments):
    out_path = OUT_DIR / f"{i:02d}_{seg['id']}.wav"
    if out_path.exists():
        print(f"[{i + 1}/{len(segments)}] {seg['id']}: already exists, skipping")
        wav_paths.append(out_path)
        continue
    print(f"[{i + 1}/{len(segments)}] {seg['id']}: synthesizing...")
    pcm = synth(seg["narration"])
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)
    wav_paths.append(out_path)
    time.sleep(25.0)  # be polite to the shared free-tier quota

print(f"\n{len(wav_paths)}/{len(segments)} segments present.")
if len(wav_paths) < len(segments):
    print("Not all segments are done yet -- stopping before the final concat/mp3 step "
          "so an incomplete file is never produced. Re-run this script once the quota "
          "has freed up to pick up where it left off.")
    raise SystemExit(0)

concat_list = OUT_DIR / "concat.txt"
lines = []
silence_path = OUT_DIR / "_silence.wav"
subprocess.run(
    ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.6",
     str(silence_path)],
    check=True, capture_output=True,
)
for p in wav_paths:
    lines.append(f"file '{p}'")
    lines.append(f"file '{silence_path}'")
concat_list.write_text("\n".join(lines))

final_wav = HERE / "pitch-narration.wav"
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy",
     str(final_wav)],
    check=True, capture_output=True,
)

final_mp3 = HERE / "pitch-narration.mp3"
subprocess.run(
    ["ffmpeg", "-y", "-i", str(final_wav), "-codec:a", "libmp3lame", "-qscale:a", "2",
     str(final_mp3)],
    check=True, capture_output=True,
)
print("DONE:", final_mp3)
