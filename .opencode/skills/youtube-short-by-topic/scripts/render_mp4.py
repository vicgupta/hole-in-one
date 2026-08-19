#!/usr/bin/env python3
"""
Stage 4 — mux.

frames/*.png + audio/*.mp3  ->  short.mp4

Concatenates the per-scene voiceover into one track, merges the per-scene
SRTs into a single timeline-offset subtitle file, and burns those captions
into the video (Shorts are largely watched muted, so burned-in captions are
not optional). Output is YouTube-ready H.264/AAC at 1080×1920.

Usage:  python3 render_mp4.py PROJECT_DIR [--music bed.mp3] [--music-db -22]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def merged_srt(timing: dict) -> str:
    """Per-scene cues, offset onto the global timeline."""
    out, i, offset = [], 1, 0.0
    for scene in timing["scenes"]:
        for cue in scene["cues"]:
            start, end = cue["start"] + offset, cue["end"] + offset
            end = min(end, offset + scene["duration"])
            if end <= start:
                continue
            out.append(f"{i}\n{ts(start)} --> {ts(end)}\n{cue['text']}\n")
            i += 1
        offset += scene["duration"]
    return "\n".join(out)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{proc.stderr[-2500:]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--music", type=Path, help="optional background bed")
    ap.add_argument("--music-db", type=float, default=-24.0,
                    help="bed level in dB relative to voice (default -24)")
    ap.add_argument("--out", default="short.mp4")
    args = ap.parse_args()

    root = args.project.resolve()
    build = root / "build"
    timing = json.loads((build / "timing.json").read_text(encoding="utf-8"))
    capture = json.loads((build / "capture.json").read_text(encoding="utf-8"))
    fps = capture["fps"]

    # 1 · one voice track
    listing = "\n".join(f"file '{(root / s['audio']).as_posix()}'"
                        for s in timing["scenes"])
    (build / "concat.txt").write_text(listing + "\n", encoding="utf-8")
    voice = build / "voice.m4a"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(build / "concat.txt"), "-c:a", "aac", "-b:a", "192k", str(voice)])

    # 2 · optional music bed, ducked under the voice
    audio_in, filter_a = ["voice.m4a"], []
    if args.music:
        audio_in.append(str(args.music.resolve()))
        filter_a = [
            f"[1:a]volume={args.music_db}dB,afade=t=out:st="
            f"{max(timing['total'] - 1.5, 0):.2f}:d=1.5[bed];"
            "[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        ]

    # 3 · captions sidecar
    #    Captions are already painted into the frames by the deck, so nothing
    #    is burned in here. This .srt ships alongside the MP4 so the user can
    #    upload real subtitles to YouTube instead of relying on auto-captions.
    (root / "captions.srt").write_text(merged_srt(timing), encoding="utf-8")

    vf = ["format=yuv420p"]

    cmd = ["ffmpeg", "-y",
           "-framerate", str(fps), "-i", f"frames/f%05d.{capture.get('ext', 'jpg')}"]
    for a in audio_in:
        cmd += ["-i", a]
    if filter_a:
        cmd += ["-filter_complex", filter_a[0], "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-vf", ",".join(vf),
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            "-s", f"{capture.get('w', 1080)}x{capture.get('h', 1920)}",
            str(root / args.out)]
    print(f"  encoding {args.out} …")
    run(cmd, cwd=build)

    size = (root / args.out).stat().st_size / 1_048_576
    print(f"\n  ✓ {args.out} · {timing['total']:.1f}s · {size:.1f} MB · "
          f"{capture.get('w', 1080)}×{capture.get('h', 1920)} @ {fps}fps")
    print("  ✓ captions.srt (upload alongside the video)")


if __name__ == "__main__":
    main()
