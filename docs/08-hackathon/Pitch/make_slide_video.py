"""Builds a silent video of the pitch deck itself (slides_hires/slide-NN.png, 1920x1080),
one static shot per slide, each held for its matching narration segment's real duration
(from audio_natural/*.wav) plus a small buffer -- so the pacing already matches the
voice recording even though no audio is muxed in here. No narration, no music, no
captions: this is just the deck as a video, meant to be synced/edited together with
pitch-narration.mp3 (or the individual audio_natural/ clips) in an external editor.
"""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLIDES_DIR = HERE / "slides_hires"
AUDIO_DIR = HERE / "audio_natural"
TMP_DIR = HERE / "_slide_clips"
TMP_DIR.mkdir(exist_ok=True)

BUFFER_S = 1.0
FPS = 30


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


slide_files = sorted(SLIDES_DIR.glob("slide-*.png"))
audio_files = sorted(AUDIO_DIR.glob("*.wav"))
assert len(slide_files) == len(audio_files) == 12, (len(slide_files), len(audio_files))

clip_paths = []
total = 0.0
for slide_path, audio_path in zip(slide_files, audio_files):
    dur = probe_duration(audio_path) + BUFFER_S
    out = TMP_DIR / f"{slide_path.stem}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(slide_path),
        "-t", str(dur),
        "-r", str(FPS),
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(out),
    ]
    print(f"{slide_path.name}: {dur:.1f}s")
    subprocess.run(cmd, check=True, capture_output=True)
    clip_paths.append(out)
    total += dur

print(f"\nTotal (silent) video duration: {total:.1f}s ({total / 60:.1f} min)")

concat_list = TMP_DIR / "concat.txt"
concat_list.write_text("".join(f"file '{p}'\n" for p in clip_paths))
final_out = HERE / "pitch-deck-video.mp4"
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
     "-c", "copy", str(final_out)],
    check=True, capture_output=True,
)
print("DONE:", final_out)

for p in clip_paths:
    p.unlink(missing_ok=True)
concat_list.unlink(missing_ok=True)
