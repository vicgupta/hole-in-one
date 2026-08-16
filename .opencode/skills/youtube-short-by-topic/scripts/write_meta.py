#!/usr/bin/env python3
"""
Stage 5 — metadata.

script.json + build/timing.json  ->  video.md

Writes the upload sheet next to the MP4: the video's own title and
description, plus the runtime, format and sources measured from the actual
render. This is the file you paste from when uploading, and the record of
what a given MP4 actually claims — so a re-render never leaves the title and
the video out of step.

Usage:  python3 write_meta.py PROJECT_DIR [--out video.md]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# keep in step with build_deck.FORMATS
FORMATS = {"short": (1080, 1920), "deck": (1920, 1080)}


def clock(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--out", default="video.md")
    args = ap.parse_args()

    root = args.project.resolve()
    cfg = json.loads((root / "script.json").read_text(encoding="utf-8"))

    timing, capture = {}, {}
    tp, cp = root / "build" / "timing.json", root / "build" / "capture.json"
    if tp.exists():
        timing = json.loads(tp.read_text(encoding="utf-8"))
    if cp.exists():
        capture = json.loads(cp.read_text(encoding="utf-8"))

    fmt = cfg.get("format", "short")
    # `title` is the page/tab title; `video_title` is what gets uploaded.
    # Fall back rather than fail — but say so, since a shared title across
    # videos is exactly what this field exists to prevent.
    video_title = cfg.get("video_title")
    fell_back = not video_title
    if fell_back:
        video_title = cfg.get("title", cfg.get("topic", "Untitled"))
    description = cfg.get("video_description", "").strip()

    # Prefer the final render over a leftover `--draft` file, then most recent.
    mp4s = sorted(root.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    mp4 = next((p for p in mp4s if "draft" not in p.name), None) or (mp4s[0] if mp4s else None)
    scenes = timing.get("scenes", [])

    lines: list[str] = [f"# {video_title}", ""]
    if description:
        lines += [description, ""]

    lines += ["## Video", "", "| | |", "| --- | --- |"]
    if mp4:
        lines.append(f"| File | `{mp4.name}` ({mp4.stat().st_size / 1_048_576:.1f} MB) |")
    if timing:
        lines.append(f"| Runtime | {clock(timing['total'])} ({timing['total']:.1f}s) |")
    if capture:
        # capture.json only carries w/h from newer runs — fall back to the format
        dw, dh = FORMATS.get(fmt, FORMATS["short"])
        w, h = capture.get("w") or dw, capture.get("h") or dh
        lines.append(f"| Format | `{fmt}` · {w}×{h} @ {capture.get('fps')}fps |")
    else:
        w, h = FORMATS.get(fmt, FORMATS["short"])
        lines.append(f"| Format | `{fmt}` · {w}×{h} |")
    if timing.get("voice"):
        lines.append(f"| Voice | `{timing['voice']}` at `{timing.get('rate', '')}` |")
    if scenes:
        lines.append(f"| Scenes | {len(scenes)} |")
    words = sum(len(s.get("narration", "").split()) for s in scenes)
    if words:
        lines.append(f"| Narration | ~{words} words |")
    lines.append("")

    tags = cfg.get("hashtags") or []
    if tags:
        lines += ["## Hashtags", "",
                  " ".join(t if t.startswith("#") else f"#{t}" for t in tags), ""]

    if scenes:
        lines += ["## Scenes", "", "| # | Layout | Length | On screen |",
                  "| --- | --- | --- | --- |"]
        for i, (sc, t) in enumerate(zip(cfg["scenes"], scenes), 1):
            head = (sc.get("headline") or sc.get("kicker") or "—").replace("\n", " ")
            head = head.replace("*", "").replace("|", "\\|")
            lines.append(f"| {i} | `{sc.get('layout', 'statement')}` | "
                         f"{t['duration']:.1f}s | {head} |")
        lines.append("")

    sources = cfg.get("sources") or []
    if sources:
        lines += ["## Sources", ""]
        lines += [f"- [{s.get('title', s.get('url', ''))}]({s.get('url', '')})"
                  for s in sources]
        lines.append("")

    lines += ["---", "",
              f"Generated from `script.json` by the `youtube-short-by-topic` skill. "
              f"Re-run the pipeline to refresh."]

    (root / args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {args.out} — “{video_title}”")
    if fell_back:
        print("  ⚠ no `video_title` in script.json — fell back to `title`. "
              "Set a unique one so each video gets its own.")
    if not description:
        print("  ⚠ no `video_description` in script.json — the sheet has no summary.")


if __name__ == "__main__":
    main()
