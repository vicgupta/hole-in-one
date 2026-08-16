#!/usr/bin/env python3
"""
Orchestrator — runs the whole pipeline over a project directory that already
contains a script.json.

    python3 make_short.py PROJECT_DIR [--fps 24] [--draft] [--music bed.mp3]
    python3 make_short.py PROJECT_DIR --from build     # skip TTS, re-render

Stages: audio -> deck -> frames -> mp4 -> meta
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES = ("audio", "deck", "frames", "mp4", "meta")


def run(script: str, *extra: str) -> None:
    cmd = [sys.executable, str(HERE / script), *extra]
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"\n✗ {script} failed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--draft", action="store_true",
                    help="12fps at half scale — fast preview render")
    ap.add_argument("--music", type=Path)
    ap.add_argument("--from", dest="start", choices=STAGES, default="audio",
                    help="resume from a stage (skips TTS when set past 'audio')")
    ap.add_argument("--voice")
    ap.add_argument("--out", help="output filename, default short.mp4")
    args = ap.parse_args()

    root = args.project.resolve()
    if not (root / "script.json").exists():
        sys.exit(f"no script.json in {root}")

    fps = 12 if args.draft else args.fps
    scale = "0.5" if args.draft else "1"
    todo = STAGES[STAGES.index(args.start):]
    started = time.time()

    if "audio" in todo:
        print("\n▸ 1/5  voiceover")
        run("generate_audio.py", str(root), *(["--voice", args.voice] if args.voice else []))
    if "deck" in todo:
        print("\n▸ 2/5  deck")
        run("build_deck.py", str(root))
    if "frames" in todo:
        print("\n▸ 3/5  frames")
        run("capture_frames.py", str(root), "--fps", str(fps), "--scale", scale)
    if "mp4" in todo:
        print("\n▸ 4/5  encode")
        out = args.out or ("short-draft.mp4" if args.draft else "short.mp4")
        run("render_mp4.py", str(root), "--out", out,
            *(["--music", str(args.music)] if args.music else []))
    if "meta" in todo:
        print("\n▸ 5/5  metadata")
        run("write_meta.py", str(root))

    print(f"\n✓ done in {time.time() - started:.0f}s → {root}")


if __name__ == "__main__":
    main()
