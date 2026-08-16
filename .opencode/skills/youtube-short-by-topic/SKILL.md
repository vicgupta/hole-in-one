---
name: youtube-short-by-topic
description: Turn a topic into a finished narrated video — researches the topic, writes the script, generates an Edge-TTS voiceover, builds an animated deck, and renders it to MP4 with captions. Two formats: `short` (vertical 1080×1920, ≤60s) and `deck` (landscape 1920×1080, long-form explainer). Use when the user asks for a YouTube Short, a vertical/TikTok/Reels clip, a narrated explainer, a talk-style slide video, or says "make a short about X" / "make a N-minute video on X".
---

# YouTube Short by topic

Topic in, MP4 out. You do the research and the scriptwriting; four
deterministic Python stages do the rest.

**Pick the format first** — it is a field in `script.json`, not a flag:

| `format` | Stage | For |
| --- | --- | --- |
| `short` (default) | 1080×1920 vertical | Shorts / Reels / TikTok, ≤60s |
| `deck` | 1920×1080 landscape | Long-form explainers, 3–15 min |

Everything below applies to both; the constraints in step 2 differ.

```
topic ──► research ──► script.json ──► generate_audio ──► audio/*.mp3 + timing.json
                                    ──► build_deck     ──► index.html (preview)
                                    ──► capture_frames ──► build/frames/*.jpg
                                    ──► render_mp4     ──► the .mp4 + captions.srt
                                    ──► write_meta     ──► video.md (upload sheet)
```

## Workflow

### 1 · Research the topic first

Never script from memory alone — Shorts make confident factual claims in very
few words, so a wrong number is the whole video. Before writing:

- Use `WebSearch` / `WebFetch` for current facts, numbers, names, and dates.
- If the user's `/research` skill fits the topic better, use it.
- If the user supplied a URL, file, or notes, script strictly from that.

Collect 2–5 sources. Record them in `script.json` under `sources` — they end up
in the description block you hand back.

**Every hard claim in the narration must trace to a source.** If you can't
source a number, cut it or soften it — do not fabricate a statistic.

### 2 · Write `script.json`

Create a project dir (default `./shorts/<slug>/`) and write `script.json` there.
Read `reference/script-format.md` for the full field list and the eight scene
layouts before writing.

The hard constraints:

Edge TTS runs ~2.6 words/second, so **word count is your runtime dial**.

| | `short` | `deck` |
| --- | --- | --- |
| Runtime | ≤ 60s | whatever was asked (7 min ≈ 1,100 words) |
| Words | ~150 total | ~90 per scene, ~35s per scene |
| Scenes | 4–7 | 10–14 |
| Rate | `+6%` | `+4%` — long-form needs room to breathe |

- **Scene 1 is a hook** — a question, a contradiction, or a stakes-setting
  claim. In a `short` it must land in under 3 seconds; in a `deck` it can be a
  title slide that states what the viewer will be able to do by the end.
- **Last scene is a `cta`.**
- Narration is spoken, not written: contractions, short sentences, no
  parentheses, no bullet syntax. Spell out things TTS mangles — "GPT five
  point two", "S three", "twenty twenty six".
- On-screen text is **not** the narration. It's the 3–6 word anchor for what's
  being said. Redundant word-for-word text is wasted screen.

### 3 · Attach reveal cues

This is the part that makes the deck feel authored rather than generic.

Any revealable element takes a `cue` — a short verbatim phrase from that
scene's own narration. The element appears exactly when the voice reaches
that phrase in the measured audio:

```json
{"text": "75+ providers", "cue": "seventy five"}
```

Cues are matched against the real SRT word timings, so **reveals can't drift
when you reword the narration** — regenerate and they move with it. Elements
without a cue spread evenly across the scene. Prefer cues on every item;
fall back to even spacing only for decorative content.

Cue phrases must appear **verbatim in that scene's `narration`** (matching is
case- and punctuation-insensitive). A cue that doesn't match silently falls
back to even spacing — check the reveal times the build prints.

### 4 · Build

```bash
python3 ~/.claude/skills/youtube-short-by-topic/scripts/make_short.py ./shorts/<slug> --draft
```

Start with `--draft` (12fps, half scale, ~4× faster) to check pacing and
layout. Then the real render:

```bash
python3 ~/.claude/skills/youtube-short-by-topic/scripts/make_short.py ./shorts/<slug>
```

Re-run individual stages instead of the whole pipeline when iterating:

| Change | Command |
| --- | --- |
| Narration wording | full run (audio timings change) |
| Layout, text, colours only | `--from deck` |
| fps / scale only | `--from frames` |
| Captions or music only | `--from mp4` |
| Title or description only | `--from meta` (instant, no re-render) |

`--from deck` and later skip TTS entirely, so they're fast and need no network.

### 5 · Check it before handing it over

`build_deck.py` prints each scene's duration and reveal times. Verify:

- Runtime is what was asked. For `short`, the audio stage warns when you are
  over 60s and says roughly how many words to cut.
- No reveal fires so late it only flashes: past ~85% of a scene in a `short`,
  or with under ~3s left in a `deck`. Reword the narration so the cue lands
  earlier rather than deleting the cue.
- Printed reveal times are in DOM order, not chronological — in a `split`
  scene the code block is emitted last but usually reveals mid-scene. Read
  them per element, not as a sequence.

Open `index.html` in a browser for the interactive preview (audio-driven, same
timeline as the render). Then hand back `short.mp4` with `SendUserFile`.

### 6 · Upload metadata → `video.md`

Every video gets its own title and description, set in `script.json` and
written to `video.md` by the last stage. **Set these when you write the
script** — don't leave them to the end:

```json
{
  "title": "Advanced OpenCode",
  "video_title": "Advanced OpenCode: config, agents, permissions & CI",
  "video_description": "A walkthrough of the layer underneath the chat box …",
  "hashtags": ["opencode", "devtools", "cli"]
}
```

| Field | Is | Rules |
| --- | --- | --- |
| `title` | The browser/tab title of the preview deck | Short, plain |
| `video_title` | **The upload title. Unique per video.** | ≤ 60 chars, front-loaded with the hook, no clickbait the video doesn't pay off |
| `video_description` | The blurb under the video | 1–3 sentences. YouTube truncates around 150 chars, so lead with the payload |
| `hashtags` | 3–5 tags, no `#` needed | Specific over generic — `#rustlang` beats `#coding` |

`video_title` falling back to `title` is a warning, not an error — but two
videos sharing a title is exactly what the field exists to prevent, so set it.

`write_meta.py` composes the sheet from `script.json` plus the *measured*
render: real runtime, real dimensions, real word count, the scene table, and
the sources. Re-run it alone any time the title or description changes:

```bash
python3 ~/.claude/skills/youtube-short-by-topic/scripts/write_meta.py ./shorts/<slug>
```

Then point the user at `video.md` rather than retyping the metadata in chat.

## Options

| Flag | Effect |
| --- | --- |
| `--draft` | 12fps @ 0.5 scale — fast pacing check |
| `--fps N` | Capture rate, default 24 |
| `--voice V` | Any Edge TTS voice (`edge-tts --list-voices`) |
| `--music bed.mp3` | Mixes a bed under the voice at −24 dB with a tail fade |
| `--from STAGE` | Resume at `audio` / `deck` / `frames` / `mp4` / `meta` |
| `--out NAME.mp4` | Output filename, default `short.mp4` |

Per-project overrides — `voice`, `rate`, `theme`, `accent`, `accent2`, `brand`
— live in `script.json` and don't need flags. `theme` names an overlay in
`assets/template/themes/` (`nightowl-glass`, `light-theme`); see
`reference/script-format.md` before writing a new one.

## Requirements

`edge-tts`, `playwright` (drives system Chrome), `ffmpeg` + `ffprobe`. No libass
build of ffmpeg is needed — see below. The audio stage needs network; every
later stage is offline.

## Notes

- Capture runs at roughly 18–28 frames/second, and it dominates the runtime.
  A 34s Short takes ~65s end to end; a 7-minute deck takes ~7 minutes. Run
  long decks in the background. `--draft` roughly halves it.
- Captions are painted by the deck and screenshotted, **not** burned in with
  ffmpeg's `subtitles` filter: that filter needs libass, which plenty of ffmpeg
  builds ship without (including current Homebrew). Doing it in CSS also means
  captions use the deck's own typeface. A sidecar `captions.srt` on the global
  timeline is still written next to the MP4 for upload.
- Frames are JPEG, not PNG — Chrome encodes them ~5× faster, and it's well
  above what H.264 keeps. `--png` if you need lossless stills.
- Frames seek deterministically via `window.__seek(scene, t)`; animations freeze
  at exact offsets using a paused animation with a negative `animation-delay`,
  so mid-fade frames are reproducible rather than wall-clock dependent.
