#!/usr/bin/env python3
"""Assembles the final demo video: mux each raw Playwright recording with its narration
audio (placed at the exact offsets timeline.json captured), concatenate admin+legal,
then burn in captions built from segments.js + the same offsets."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIDEO_DIR = HERE / "video"
AUDIO_DIR = HERE / "audio"
OUT_DIR = HERE / "out"
OUT_DIR.mkdir(exist_ok=True)

with open(HERE / "timeline.json") as f:
    timeline = json.load(f)
with open(HERE / "durations.json") as f:
    durations = json.load(f)

# segments.js -> parse narration text per id (reuse via a tiny node eval, avoids
# reimplementing the JS array in Python)
segments_json = subprocess.run(
    ["node", "-e", "console.log(JSON.stringify(require('./segments.js')))"],
    cwd=HERE, capture_output=True, text=True, check=True,
).stdout
segments = {s["id"]: s for s in json.loads(segments_json)}

ADMIN_VIDEO = VIDEO_DIR / "page@1abb2af390c031eb6b4c3094fb76e44c.webm"
LEGAL_VIDEO = VIDEO_DIR / "page@72c00f33a18bf6cd143272e3f1e01371.webm"


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def mux_with_audio(video_path, segs, out_path):
    """segs: list of {id, offsetSec}. Builds a delayed-and-mixed audio track and muxes
    it onto video_path (re-encoding to a seekable, editing-friendly mp4: h264 + aac)."""
    duration = probe_duration(video_path)
    inputs = ["-i", str(video_path)]
    filter_parts = []
    mix_labels = []
    for i, seg in enumerate(segs):
        wav = AUDIO_DIR / f"{seg['id']}.wav"
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


admin_out = OUT_DIR / "admin_with_audio.mp4"
legal_out = OUT_DIR / "legal_with_audio.mp4"
admin_duration = mux_with_audio(ADMIN_VIDEO, timeline["admin"], admin_out)
legal_duration = mux_with_audio(LEGAL_VIDEO, timeline["legal"], legal_out)

# Concatenate (re-encode via concat demuxer's "safe" stream copy since both are already
# the same codec/resolution from the mux step above).
concat_list = OUT_DIR / "concat.txt"
concat_list.write_text(f"file '{admin_out}'\nfile '{legal_out}'\n")
combined = OUT_DIR / "combined.mp4"
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
     "-c", "copy", str(combined)],
    check=True, capture_output=True,
)
print("combined duration (admin+legal):", admin_duration + legal_duration)

# Build SRT captions: admin segments at their own offset; legal segments offset by
# admin_duration (since legal plays after admin in the concatenated timeline).
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
        # Wrap at ~70 chars for readable on-screen lines
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

srt_path = OUT_DIR / "captions.srt"
srt_path.write_text("\n".join(srt_lines))
print("wrote", srt_path)

# Burn in captions -- explicit PlayRes avoids libass guessing a script resolution that
# scales the font far larger than FontSize implies at 1280x720.
final_out = OUT_DIR / "jurisense-gate-demo.mp4"
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
