#!/usr/bin/env python3
"""
Stage 1 — voiceover.

Reads script.json, produces:
  audio/scene-01.mp3 …            Edge TTS voiceover, one track per scene
  audio/scene-01.srt …            boundary subtitles
  build/timing.json               per-scene duration + normalised caption cues

Every later stage reads build/timing.json, so real measured durations — not
guesses — drive slide length, reveal timing, and frame counts.

Usage:  python3 generate_audio.py PROJECT_DIR [--voice V] [--rate R] [--pitch P]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts is not installed.  pip install edge-tts")

SRT_TIME = re.compile(
    r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)"
)

# Vertical video is narrow: keep caption lines short or they wrap badly.
MAX_CHARS = 42


def srt_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: Path) -> list[dict]:
    """Turn an edge-tts SRT into [{start, end, text}] cues."""
    if not path.exists():
        return []
    cues: list[dict] = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        stamp = next((ln for ln in lines if SRT_TIME.search(ln)), None)
        if not stamp:
            continue
        m = SRT_TIME.search(stamp)
        text = " ".join(lines[lines.index(stamp) + 1:]).strip()
        if not text:
            continue
        cues.append({
            "start": round(srt_seconds(*m.groups()[:4]), 3),
            "end": round(srt_seconds(*m.groups()[4:]), 3),
            "text": text,
        })
    return cues


def split_cue(cue: dict) -> list[dict]:
    """Break one long cue into caption-sized lines, timed by character share."""
    words = cue["text"].split()
    if not words:
        return []
    lines: list[list[str]] = [[]]
    for word in words:
        candidate = len(" ".join(lines[-1] + [word]))
        if lines[-1] and candidate > MAX_CHARS:
            lines.append([word])
        else:
            lines[-1].append(word)

    span = max(cue["end"] - cue["start"], 0.001)
    total = sum(len(" ".join(ln)) for ln in lines) or 1
    out, t = [], cue["start"]
    for ln in lines:
        text = " ".join(ln)
        end = t + span * (len(text) / total)
        out.append({"start": round(t, 3), "end": round(end, 3), "text": text})
        t = end
    out[-1]["end"] = cue["end"]
    return out


def group_cues(cues: list[dict]) -> list[dict]:
    """Normalise boundary cues (word- or sentence-level) into caption lines."""
    merged: list[dict] = []
    for cue in cues:
        if merged and len(merged[-1]["text"]) + len(cue["text"]) + 1 <= MAX_CHARS:
            last = merged[-1]
            last["text"] = f"{last['text']} {cue['text']}"
            last["end"] = cue["end"]
        else:
            merged.append(dict(cue))

    grouped = [line for cue in merged for line in split_cue(cue)]
    # Hold each caption until the next begins — no flicker gaps.
    for i, cue in enumerate(grouped[:-1]):
        cue["end"] = grouped[i + 1]["start"]
    return grouped


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


async def synth(text: str, voice: str, rate: str, pitch: str,
                mp3: Path, srt: Path) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    submaker = edge_tts.SubMaker()
    with mp3.open("wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                # Multilingual voices emit sentence boundaries; others emit words.
                submaker.feed(chunk)
    srt.write_text(submaker.get_srt(), encoding="utf-8")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--voice")
    ap.add_argument("--rate")
    ap.add_argument("--pitch")
    args = ap.parse_args()

    root = args.project.resolve()
    cfg = json.loads((root / "script.json").read_text(encoding="utf-8"))

    voice = args.voice or cfg.get("voice", "en-US-AndrewMultilingualNeural")
    rate = args.rate or cfg.get("rate", "+6%")
    pitch = args.pitch or cfg.get("pitch", "+0Hz")

    audio_dir = root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    (root / "build").mkdir(parents=True, exist_ok=True)

    scenes = cfg["scenes"]
    out: list[dict] = []
    total = 0.0

    for i, scene in enumerate(scenes, 1):
        n = f"{i:02d}"
        mp3, srt = audio_dir / f"scene-{n}.mp3", audio_dir / f"scene-{n}.srt"
        label = scene.get("headline") or scene.get("layout", "scene")
        print(f"  [{n}/{len(scenes):02d}] {label[:38]:38} … ", end="", flush=True)
        await synth(scene["narration"], voice, rate, pitch, mp3, srt)
        secs = duration_of(mp3)
        total += secs
        print(f"{secs:5.1f}s")
        out.append({
            "id": i,
            "audio": f"audio/scene-{n}.mp3",
            "duration": secs,
            "narration": scene["narration"],
            "cues": group_cues(parse_srt(srt)),
        })

    (root / "build" / "timing.json").write_text(
        json.dumps({"voice": voice, "rate": rate, "pitch": pitch,
                    "total": round(total, 3), "scenes": out},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n  total runtime {total // 60:.0f}m {total % 60:04.1f}s · voice {voice}")
    if cfg.get("format", "short") != "short":
        pass          # long-form decks have no 60s ceiling
    elif total > 60:
        over = total - 60
        print(f"  ⚠ {over:.1f}s over the 60s Shorts target — trim narration "
              f"(roughly {int(over * 2.6)} words) and re-run.")
    elif total < 15:
        print("  ⚠ under 15s — very short for a Short; consider adding a beat.")


if __name__ == "__main__":
    asyncio.run(main())
