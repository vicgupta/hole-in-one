#!/usr/bin/env python3
"""
Stage 3 — frames.

Drives index.html?render=1 in headless Chrome and screenshots one PNG per
output frame at 1080×1920. Frames are seeked deterministically through
window.__seek(scene, t), so a capture is reproducible: no reliance on
wall-clock playback, and mid-fade frames land exactly where intended.

Usage:  python3 capture_frames.py PROJECT_DIR [--fps 24] [--scale 1]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# keep in step with build_deck.FORMATS
FORMATS = {"short": (1080, 1920), "deck": (1920, 1080)}

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is not installed.  pip install playwright")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--scale", type=float, default=1.0,
                    help="device scale factor; 0.5 halves resolution for a fast draft")
    # JPEG encodes ~5x faster than PNG in Chrome and is still well above what
    # H.264 preserves, so frames are throwaway JPEGs unless asked otherwise.
    ap.add_argument("--png", action="store_true",
                    help="lossless frames (much slower; only for stills)")
    ap.add_argument("--quality", type=int, default=94)
    args = ap.parse_args()

    root = args.project.resolve()
    timing = json.loads((root / "build" / "timing.json").read_text(encoding="utf-8"))
    cfg = json.loads((root / "script.json").read_text(encoding="utf-8"))
    sw, sh = FORMATS.get(cfg.get("format", "short"), FORMATS["short"])
    frames_dir = root / "build" / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    url = (root / "index.html").as_uri() + "?render=1"
    total_frames = sum(max(1, round(s["duration"] * args.fps))
                       for s in timing["scenes"])
    print(f"  capturing {total_frames} frames @ {args.fps}fps · {sw}×{sh} …")

    started = time.time()
    n = 0
    with sync_playwright() as p:
        for launch in ({"channel": "chrome"}, {}):
            try:
                browser = p.chromium.launch(**launch)
                break
            except Exception:
                browser = None
        if browser is None:
            sys.exit("could not launch Chromium — try: python3 -m playwright install chromium")

        page = browser.new_page(
            viewport={"width": sw, "height": sh},
            device_scale_factor=args.scale,
        )
        page.goto(url, wait_until="load")
        page.wait_for_function("window.__ready === true", timeout=15000)
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(300)

        ext = "png" if args.png else "jpg"
        shot = ({"type": "png"} if args.png
                else {"type": "jpeg", "quality": args.quality})

        for si, scene in enumerate(timing["scenes"]):
            count = max(1, round(scene["duration"] * args.fps))
            for f in range(count):
                t = f / args.fps
                page.evaluate("([s, t]) => window.__seek(s, t)", [si, t])
                page.screenshot(path=str(frames_dir / f"f{n:05d}.{ext}"), **shot)
                n += 1
            done = n / total_frames
            elapsed = time.time() - started
            eta = elapsed / done - elapsed if done else 0
            print(f"    scene {si + 1}/{len(timing['scenes'])} "
                  f"· {n}/{total_frames} frames · eta {eta:4.0f}s", flush=True)

        browser.close()

    elapsed = time.time() - started
    print(f"  {n} frames in {elapsed:.0f}s ({n / max(elapsed, .01):.1f} fps) → build/frames/")
    (root / "build" / "capture.json").write_text(
        json.dumps({"fps": args.fps, "frames": n, "scale": args.scale,
                    "ext": ext, "w": sw, "h": sh}),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
