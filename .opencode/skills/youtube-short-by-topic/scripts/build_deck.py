#!/usr/bin/env python3
"""
Stage 2 — deck.

script.json + build/timing.json  ->  index.html, data.js, styles.css, app.js

Reveal timings are DERIVED, never hand-tuned: each revealable element may
carry a `cue` — a short phrase lifted from that scene's narration — and the
element appears at the moment the voice reaches that phrase in the measured
SRT. Elements without a cue spread evenly across the scene body. Re-record
the narration and the reveals move with it, so wording changes can't drift
out of sync with the visuals.

Usage:  python3 build_deck.py PROJECT_DIR
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template"

LAYOUTS = {"hook", "statement", "bullets", "steps", "code", "compare", "stat",
           "split", "cta"}

# format -> (stage width, stage height, stylesheet)
FORMATS = {
    "short": (1080, 1920, "short.css"),   # vertical, YouTube Shorts / Reels
    "deck":  (1920, 1080, "deck.css"),    # landscape, long-form presentation
}


# ── cue → timestamp ─────────────────────────────────────────
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def token_timeline(cues: list[dict]) -> list[tuple[str, float]]:
    """Flatten caption cues into (word, approximate_start) pairs."""
    toks: list[tuple[str, float]] = []
    for c in cues:
        words = norm(c["text"]).split()
        if not words:
            continue
        span = max(c["end"] - c["start"], 0.001)
        for i, w in enumerate(words):
            toks.append((w, c["start"] + span * i / len(words)))
    return toks


def cue_time(toks: list[tuple[str, float]], phrase: str | None,
             fallback: float) -> float:
    """When does the narrator start saying `phrase`?"""
    if not phrase or not toks:
        return round(fallback, 3)
    target = norm(phrase).split()
    if not target:
        return round(fallback, 3)
    words = [t[0] for t in toks]
    n = len(target)
    for i in range(len(words) - n + 1):
        if words[i:i + n] == target:
            return round(toks[i][1], 3)
    # phrase not found verbatim — fall back to its first distinctive word
    for i, w in enumerate(words):
        if w == target[0]:
            return round(toks[i][1], 3)
    return round(fallback, 3)


def spread(count: int, duration: float, start=0.22, end=0.80) -> list[float]:
    """Even fallback timings across the meat of a scene."""
    if count <= 0:
        return []
    a, b = duration * start, duration * end
    if count == 1:
        return [round(a, 3)]
    step = (b - a) / (count - 1)
    return [round(a + step * i, 3) for i in range(count)]


# ── html helpers ────────────────────────────────────────────
def e(s) -> str:
    return html.escape(str(s), quote=True)


def rev(at: float, cls: str = "") -> str:
    c = f"{cls} r".strip()
    return f'class="{c}" data-at="{at:.3f}"'


def code_line(line: str) -> str:
    """Light auto-highlighting: prompts, comments, flags, strings."""
    if line.strip().startswith("#"):
        return f'<span class="c-dim">{e(line)}</span>'
    out = e(line)
    out = re.sub(r"^(\s*)((?:\$|❯|&gt;)\s)",
                 r'\1<span class="c-acc">\2</span>', out)
    out = re.sub(r"(&quot;[^&]*?&quot;|&#x27;[^&]*?&#x27;)",
                 r'<span class="c-str">\1</span>', out)
    out = re.sub(r"(\s)(--?[a-zA-Z][\w-]*)", r'\1<span class="c-key">\2</span>', out)
    return out


def headline_html(text: str) -> str:
    """Inline markup: `code` spans, *accent gradient* segments, \\n breaks."""
    out = []
    for i, chunk in enumerate(re.split(r"`([^`]+)`", text)):
        if not chunk:
            continue
        if i % 2:
            out.append(f"<code>{e(chunk)}</code>")
            continue
        for j, part in enumerate(re.split(r"\*(.+?)\*", chunk)):
            if not part:
                continue
            out.append(f'<span class="grad">{e(part)}</span>' if j % 2 else e(part))
    return "".join(out).replace("\n", "<br>")


# ── scene rendering ─────────────────────────────────────────
def render_scene(scene: dict, timing: dict, n: int) -> str:
    layout = scene.get("layout", "statement")
    if layout not in LAYOUTS:
        raise SystemExit(f"scene {n}: unknown layout {layout!r} "
                         f"(pick one of {', '.join(sorted(LAYOUTS))})")

    dur = timing["duration"]
    toks = token_timeline(timing["cues"])
    body: list[str] = []

    if scene.get("kicker"):
        body.append(f'<span {rev(0.0, "kicker")}>{e(scene["kicker"])}</span>')

    if scene.get("headline"):
        tag = "h1" if layout in ("hook", "cta") else "h2"
        at = cue_time(toks, scene.get("headline_cue"), 0.15)
        body.append(f'<{tag} {rev(at)}>{headline_html(scene["headline"])}</{tag}>')

    if scene.get("sub"):
        at = cue_time(toks, scene.get("sub_cue"), dur * 0.16)
        body.append(f'<p {rev(at, "sub")}>{e(scene["sub"])}</p>')

    items = scene.get("items") or []
    if items and layout in ("bullets", "steps", "statement", "hook", "split"):
        fallbacks = spread(len(items), dur)
        rows = []
        for i, item in enumerate(items):
            text = item if isinstance(item, str) else item.get("text", "")
            cue = None if isinstance(item, str) else item.get("cue")
            at = cue_time(toks, cue, fallbacks[i])
            lead = (f'<span class="num">{i + 1}</span>' if layout == "steps"
                    else '<span class="dot"></span>')
            cls = "item item--step" if layout == "steps" else "item"
            rows.append(f'<li {rev(at, cls)}>{lead}<span>{headline_html(text)}</span></li>')
        body.append(f'<ul class="items">{"".join(rows)}</ul>')

    if layout in ("code", "split") and scene.get("code"):
        code = scene["code"]
        lines = code if isinstance(code, list) else code.get("lines", [])
        label = "" if isinstance(code, list) else code.get("label", "terminal")
        at = cue_time(toks, scene.get("code_cue"), dur * 0.25)
        rendered = "\n".join(code_line(ln) for ln in lines)
        body.append(
            f'<div {rev(at, "code")}>'
            f'<div class="code-bar"><i></i><i></i><i></i><span>{e(label or "terminal")}</span></div>'
            f'<pre>{rendered}</pre></div>'
        )

    if layout == "compare" and scene.get("compare"):
        cmp_ = scene["compare"]
        cols = []
        for side, key in (("left", "col"), ("right", "col col--good")):
            col = cmp_.get(side) or {}
            at = cue_time(toks, col.get("cue"),
                          dur * (0.22 if side == "left" else 0.52))
            lis = "".join(f"<li>{headline_html(x)}</li>" for x in col.get("items", []))
            cols.append(
                f'<div {rev(at, key)}><h3>{e(col.get("label", ""))}</h3><ul>{lis}</ul></div>'
            )
        body.append(f'<div class="compare">{"".join(cols)}</div>')

    if layout == "stat" and scene.get("stat"):
        st = scene["stat"]
        at = cue_time(toks, st.get("cue"), dur * 0.2)
        body.append(
            f'<div {rev(at, "stat")}>'
            f'<div class="big">{e(st.get("value", ""))}</div>'
            f'<div class="cap">{e(st.get("caption", ""))}</div></div>'
        )

    if layout == "cta" and scene.get("cta"):
        at = cue_time(toks, scene.get("cta_cue"), dur * 0.55)
        body.append(f'<div {rev(at, "cta-pill")}>{e(scene["cta"])}</div>')

    if layout == "split":
        # header stays full width; the list and the code sit side by side
        head = [b for b in body if "<ul" not in b and 'class="code r' not in b]
        rest = [b for b in body if b not in head]
        body = head + [f'<div class="split">{"".join(rest)}</div>']

    inner = "\n          ".join(body)
    return (f'      <section class="scene scene--{layout}" data-scene="{n}">\n'
            f'          {inner}\n'
            f'      </section>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    args = ap.parse_args()
    root = args.project.resolve()

    cfg = json.loads((root / "script.json").read_text(encoding="utf-8"))
    timing_path = root / "build" / "timing.json"
    if not timing_path.exists():
        raise SystemExit("build/timing.json missing — run generate_audio.py first.")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))

    fmt = cfg.get("format", "short")
    if fmt not in FORMATS:
        raise SystemExit(f"unknown format {fmt!r} (short | deck)")
    stage_w, stage_h, css_file = FORMATS[fmt]

    scenes, tscenes = cfg["scenes"], timing["scenes"]
    if len(scenes) != len(tscenes):
        raise SystemExit(f"script.json has {len(scenes)} scenes but timing.json "
                         f"has {len(tscenes)} — re-run generate_audio.py.")

    sections = "\n".join(
        render_scene(s, t, i + 1) for i, (s, t) in enumerate(zip(scenes, tscenes))
    )
    ticks = "".join('<div class="tick"><i></i></div>' for _ in scenes)

    brand = cfg.get("brand", "")
    brand_html = (f'<div class="brand"><span class="mark"></span>{e(brand)}</div>'
                  if brand else "")

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(cfg.get("title", "Short"))}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>

<div class="stage-wrap">
  <div class="stage" id="stage">
    <div class="ticks">{ticks}</div>
    {brand_html}

{sections}

    <div class="captions" id="captions"><span id="captionText"></span></div>
  </div>
</div>

<div class="bar">
  <button id="btnPrev">←</button>
  <button id="btnPlay">play / pause</button>
  <button id="btnNext">→</button>
  <span class="t" id="t">0.0s / 0.0s</span>
</div>

<div class="gate" id="gate"><button id="btnStart">▶  Preview short</button></div>

<audio id="player" preload="auto"></audio>
<script src="data.js"></script>
<script src="app.js"></script>
</body>
</html>
"""
    (root / "index.html").write_text(doc, encoding="utf-8")

    data = [{"id": t["id"], "audio": t["audio"], "duration": t["duration"],
             "cues": t["cues"]} for t in tscenes]
    (root / "data.js").write_text(
        "// Generated by build_deck.py — do not edit by hand.\n"
        f"const STAGE = [{stage_w}, {stage_h}];\n"
        f"const TOTAL_DURATION = {timing['total']};\n"
        "const SCENES = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    shutil.copy(TEMPLATE / "app.js", root / "app.js")

    # stylesheet = format base + optional theme overlay + project accents.
    # Composed by appending rather than substituting, so later layers win by
    # normal cascade order and a theme can restyle anything the base sets.
    css = (TEMPLATE / css_file).read_text(encoding="utf-8")
    theme = cfg.get("theme")
    if theme:
        tp = TEMPLATE / "themes" / f"{theme}.css"
        if not tp.exists():
            available = sorted(p.stem for p in (TEMPLATE / "themes").glob("*.css"))
            raise SystemExit(f"unknown theme {theme!r} "
                             f"(available: {', '.join(available) or 'none'})")
        css += f"\n\n/* ── theme: {theme} ─────────────────────────── */\n"
        css += tp.read_text(encoding="utf-8")

    overrides = [f"  --acc: {cfg[k]};" if k == "accent" else f"  --acc-2: {cfg[k]};"
                 for k in ("accent", "accent2") if cfg.get(k)]
    if overrides:
        css += ("\n\n/* per-project accents */\n:root {\n"
                + "\n".join(overrides) + "\n}\n")
    (root / "styles.css").write_text(css, encoding="utf-8")

    print(f"  built {len(scenes)} scenes → index.html  [{fmt} {stage_w}×{stage_h}]")
    for i, (s, t) in enumerate(zip(scenes, tscenes), 1):
        ats = re.findall(r'data-at="([\d.]+)"',
                         render_scene(s, t, i))
        print(f"    {i}. {s.get('layout','statement'):9} {t['duration']:5.1f}s  "
              f"reveals @ {', '.join(f'{float(a):.1f}' for a in ats)}")


if __name__ == "__main__":
    main()
