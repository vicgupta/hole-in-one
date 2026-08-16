# YouTube Short by topic

A Claude Code and OpenCode skill that turns a topic into a finished narrated video. It is included in the [Hole-In-One](https://github.com/vicgupta/hole-in-one) collection.

The model does the research and the scriptwriting; five deterministic Python stages do everything else.

```
topic ──► research ──► script.json ──► generate_audio ──► audio/*.mp3 + timing.json
                                    ──► build_deck     ──► index.html (preview)
                                    ──► capture_frames ──► build/frames/*.jpg
                                    ──► render_mp4     ──► the .mp4 + captions.srt
                                    ──► write_meta     ──► video.md (upload sheet)
```

Two formats, chosen by a field in `script.json`:

| `format` | Stage | For |
| --- | --- | --- |
| `short` (default) | 1080×1920 vertical | Shorts / Reels / TikTok |
| `deck` | 1920×1080 landscape | Long-form explainers, 3–15 min |

## Requirements

```bash
pip install edge-tts playwright
playwright install chrome
brew install ffmpeg          # needs ffmpeg and ffprobe
```

No libass build of ffmpeg is required — captions are painted by the deck and screenshotted, so they use the deck's own typeface. A sidecar `captions.srt` is still written for upload.

Only the audio stage needs network access. Every later stage is offline.

## Installation

Clone the collection and use the skill from its project-local `.opencode/skills/` directory:

```bash
git clone https://github.com/vicgupta/hole-in-one.git
cd hole-in-one
```

For a global installation, copy this directory to either tool's skills directory:

```bash
cp -R .opencode/skills/youtube-short-by-topic ~/.config/opencode/skills/youtube-short-by-topic
```

OpenCode also scans `~/.claude/skills/` for compatibility.

`SKILL.md` spells the build command as `python3 ~/.claude/skills/youtube-short-by-topic/scripts/make_short.py`. If you install somewhere else, substitute your own path — the scripts resolve their template assets relative to themselves, so they run correctly from any location.

## Usage

Ask for a video in plain language:

```
make a short about what Rust's borrow checker actually does
make a 7 minute explainer on how DNS resolution works
```

The model researches the topic, writes `script.json` into `./shorts/<slug>/`, and runs the pipeline. Then build directly:

```bash
python3 scripts/make_short.py ./shorts/<slug> --draft   # 12fps half-scale pacing check
python3 scripts/make_short.py ./shorts/<slug>           # the real render
```

Re-run individual stages instead of the whole pipeline while iterating:

| Change | Command |
| --- | --- |
| Narration wording | full run (audio timings change) |
| Layout, text, colours only | `--from deck` |
| fps / scale only | `--from frames` |
| Captions or music only | `--from mp4` |
| Title or description only | `--from meta` |

## How reveals stay in sync

Any element in `script.json` can take a `cue` — a short verbatim phrase from that scene's own narration:

```json
{"text": "75+ providers", "cue": "seventy five"}
```

Cues are matched against the measured SRT word timings, so an element appears exactly when the voice reaches that phrase. Reword the narration, regenerate, and every reveal moves with it. Elements without a cue spread evenly across the scene.

## Themes

`theme` in `script.json` names a stylesheet in `assets/template/themes/`, appended after the format base so it can restyle anything without the base being forked.

| Theme | Looks like |
| --- | --- |
| *(none)* | Slate / cyan default |
| `nightowl-glass` | Night Owl palette, frosted-glass panels over blurred colour orbs |
| `light-theme` | Warm paper, burnt-orange accent, teal secondary, dark code slab |
| `light-motion` | `light-theme` plus a motion layer — per-element entrance curves, drifting orbs |
| `ocean-sunset` | Prussian blue water, jasmine sun on the horizon, ember and blood-red afterglow |
| `spike-factor` | Bold editorial, high-contrast |
| `green-lawn` | Charcoal blue, pumpkin spice, golden pollen |

### Writing your own

Set `--acc` / `--acc-2` / `--ink`, then restyle `.item`, `.col`, `.code`, `.cta-pill`. Read `light-theme.css` first — it is a light theme, so it inverts things a dark theme never has to touch.

Four invariants that break renders silently if crossed:

1. Set `z-index` on `.scene`, `.ticks`, `.brand`, `.captions` — but never `position`. They are already absolutely positioned by the base sheet, and re-declaring position drops the captions out of their bottom-anchored slot, removing them from the whole render with no error.
2. Custom entrance animations must fit inside 0.55s. `app.js` freezes each animation at a negative delay capped to that; anything longer freezes mid-way and never completes on screen.
3. Light themes must restyle `.captions`. The base draws white text with a near-black stroke, which is invisible on paper.
4. Anything animated on wall-clock rather than through the reveal system is not seek-frozen, so keep those cycles long — 30s and up. Faster ambient motion shows sampling jitter across captured frames.

## Files

| Path | Does |
| --- | --- |
| `SKILL.md` | The workflow the model follows |
| `reference/script-format.md` | Every `script.json` field, the 8 layouts, size limits |
| `scripts/make_short.py` | Orchestrator; `--from STAGE` resumes mid-pipeline |
| `scripts/generate_audio.py` | Edge TTS → mp3 plus word-level `timing.json` |
| `scripts/build_deck.py` | `script.json` + timings → `index.html` |
| `scripts/capture_frames.py` | Headless Chrome, deterministic per-frame seek |
| `scripts/render_mp4.py` | Frames + audio → mp4, writes `captions.srt` |
| `scripts/write_meta.py` | `video.md` upload sheet from the measured render |
| `assets/template/` | Base stylesheets, `app.js`, embedded fonts, themes |

Frames seek deterministically through `window.__seek(scene, t)`, and animations freeze at exact offsets using a paused animation with a negative `animation-delay` — so a capture is reproducible rather than wall-clock dependent.

## Fonts

Open Sans and JetBrains Mono ship embedded as base64 data URIs so rendering does not depend on what is installed on the capture machine. Both are licensed under the SIL Open Font License.
