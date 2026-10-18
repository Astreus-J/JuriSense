#!/usr/bin/env python3
"""Builds a <=5min highlights cut of the demo, required for the hackathon submission (the
full 18-segment walkthrough runs 11:40, way over the limit, mostly because record.js's
timeline.json offsets include real AI-extraction wait time, not just narration length).

Instead of the full walkthrough, this keeps only the segments with real demo impact --
real AI extraction, the BLOCK decision, the correction, the REVIEW decision, approval,
the Decision Passport, and the live blockchain verification -- and drops pure-transition/
loading segments (extraction spinners, "review started" pages, the verify page before a
result is typed in). Each kept segment is cut from the real recorded footage at the exact
offset timeline.json captured (when that screen was actually reached), trimmed to its
natural-voice narration length plus a small buffer -- so every frame is still genuinely
real product footage, just not idle real-time waiting. No captions are burned in.
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIDEO_DIR = HERE / "video"
AUDIO_DIR = HERE / "audio_natural"
TMP_DIR = HERE / "_clips"
TMP_DIR.mkdir(exist_ok=True)

ADMIN_VIDEO = VIDEO_DIR / "page@a9993a0bc45d21df642e79fd97bb6d47.webm"
LEGAL_VIDEO = VIDEO_DIR / "page@a1ad506cb3baa204c83c2bd20a217a68.webm"

with open(HERE / "timeline.json") as f:
    timeline = json.load(f)
with open(HERE / "durations_natural.json") as f:
    durations = json.load(f)

AUDIO_BY_ID = {p.stem.split("_", 1)[1]: p for p in AUDIO_DIR.glob("*.wav")}
OFFSET_BY_ID = {}
for bucket, video in (("admin", ADMIN_VIDEO), ("legal", LEGAL_VIDEO)):
    for seg in timeline[bucket]:
        OFFSET_BY_ID[seg["id"]] = (video, seg["offsetSec"])

# Ordered, curated set -- real pipeline once end to end (create, check, upload, real AI
# extraction, BLOCK), then the compact fix cycle (upload v2, REVIEW), then approval,
# passport, anchor note, live verification, close. Drops: extraction-wait,
# extraction-wait-v2, compliance-review-v1, compliance-review-v2, verify-open (all pure
# loading/transition states with no new information of their own).
HIGHLIGHTS = [
    "intro",
    "supplier-create",
    "supplier-check",
    "contract-upload-v1",
    "extraction-result",
    "compliance-result-v1",
    "contract-upload-v2",
    "compliance-result-v2",
    "approval",
    "passport",
    "anchor-note",
    "verify-click",
    "close",
]
BUFFER_S = 1.3

clip_paths = []
total = 0.0
for i, seg_id in enumerate(HIGHLIGHTS):
    video_src, start = OFFSET_BY_ID[seg_id]
    dur = durations[seg_id] + BUFFER_S
    wav = AUDIO_BY_ID[seg_id]
    out = TMP_DIR / f"{i:02d}_{seg_id}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-i", str(video_src),
        "-i", str(wav),
        "-t", str(dur),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]
    print(f"[{i + 1}/{len(HIGHLIGHTS)}] {seg_id}: {dur:.1f}s from {video_src.name} @ {start:.1f}s")
    subprocess.run(cmd, check=True, capture_output=True)
    clip_paths.append(out)
    total += dur

print(f"\nTotal highlights duration: {total:.1f}s ({total / 60:.1f} min)")

concat_list = TMP_DIR / "concat.txt"
concat_list.write_text("".join(f"file '{p}'\n" for p in clip_paths))
final_out = HERE / "jurisense-gate-demo.mp4"
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
     "-c", "copy", str(final_out)],
    check=True, capture_output=True,
)
print("DONE:", final_out)

for p in clip_paths:
    p.unlink(missing_ok=True)
concat_list.unlink(missing_ok=True)
