#!/usr/bin/env python3
"""Assembles the final demo video from the 2026-10-18 slower-paced recording, using the
natural-voice (Gemini TTS) narration in audio_natural/ instead of the espeak-ng clips in
audio/. Same approach as assemble.py (mux each raw Playwright recording with its
narration audio at the offsets timeline.json captured, concatenate admin+legal, burn in
captions), adapted for: audio_natural/<NN>_<id>.wav filenames, durations_natural.json,
and this run's specific video/page@*.webm filenames (record.js never deletes old
recordings, so video/ accumulates files from every past attempt -- these two are
this run's, identified by being the most recently modified non-empty pair)."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIDEO_DIR = HERE / "video"
AUDIO_DIR = HERE / "audio_natural"

with open(HERE / "timeline.json") as f:
    timeline = json.load(f)
with open(HERE / "durations_natural.json") as f:
    durations = json.load(f)

segments_json = subprocess.run(
    ["node", "-e", "console.log(JSON.stringify(require('./segments.js')))"],
    cwd=HERE, capture_output=True, text=True, check=True,
).stdout
segments = {s["id"]: s for s in json.loads(segments_json)}

AUDIO_BY_ID = {p.stem.split("_", 1)[1]: p for p in AUDIO_DIR.glob("*.wav")}

ADMIN_VIDEO = VIDEO_DIR / "page@a9993a0bc45d21df642e79fd97bb6d47.webm"
LEGAL_VIDEO = VIDEO_DIR / "page@a1ad506cb3baa204c83c2bd20a217a68.webm"


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def mux_with_audio(video_path, segs, out_path):
    duration = probe_duration(video_path)
    inputs = ["-i", str(video_path)]
    filter_parts = []
    mix_labels = []
    for i, seg in enumerate(segs):
        wav = AUDIO_BY_ID[seg["id"]]
        inputs += ["-i", str(wav)]
        delay_ms = int(seg["offsetSec"] * 1000)
        label = f"a{i}"
        filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms}[{label}]")
        mix_labels.append(f"[{label}]")
    filter_complex = ";".join(filter_parts) + ";" + "".join(mix_labels) + \
        f"amix=inputs={len(segs)}:duration=longest:dropout_transition=0[aout]"

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(out_path),
    ]
    print("muxing:", out_path.name)
    subprocess.run(cmd, check=True, capture_output=True)
    return duration


admin_out = HERE / "_admin_with_audio.mp4"
legal_out = HERE / "_legal_with_audio.mp4"
admin_duration = mux_with_audio(ADMIN_VIDEO, timeline["admin"], admin_out)
legal_duration = mux_with_audio(LEGAL_VIDEO, timeline["legal"], legal_out)

concat_list = HERE / "_concat.txt"
concat_list.write_text(f"file '{admin_out}'\nfile '{legal_out}'\n")
combined = HERE / "_combined.mp4"
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
     "-c", "copy", str(combined)],
    check=True, capture_output=True,
)
print("combined duration (admin+legal):", admin_duration + legal_duration)


def fmt_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


srt_lines = []
idx = 1
for bucket, base_offset in (("admin", 0.0), ("legal", admin_duration)):
    for seg in timeline[bucket]:
        start = base_offset + seg["offsetSec"]
        dur = durations.get(seg["id"], 4)
        end = start + dur
        text = segments[seg["id"]]["narration"]
        words = text.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 85:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            lines.append(cur)
        srt_lines.append(f"{idx}\n{fmt_ts(start)} --> {fmt_ts(end)}\n" + "\n".join(lines) + "\n")
        idx += 1

srt_path = HERE / "captions.srt"
srt_path.write_text("\n".join(srt_lines))
print("wrote", srt_path)

final_out = HERE / "jurisense-gate-demo.mp4"
style = (
    "FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,"
    "Alignment=2,MarginV=18,MarginL=40,MarginR=40,PlayResX=1280,PlayResY=720"
)
subprocess.run(
    ["ffmpeg", "-y", "-i", str(combined),
     "-vf", f"subtitles={srt_path}:force_style='{style}'",
     "-c:a", "copy",
     str(final_out)],
    check=True, capture_output=True,
)
print("DONE:", final_out)

for tmp in (admin_out, legal_out, combined, concat_list):
    tmp.unlink(missing_ok=True)
