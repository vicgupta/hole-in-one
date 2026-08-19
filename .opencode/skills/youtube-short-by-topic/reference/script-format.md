# `script.json` format

One file describes the whole video. Everything else is generated.

## Top level

| Field | Required | Notes |
| --- | --- | --- |
| `topic` | ✓ | The user's ask, verbatim — provenance for later re-runs. |
| `format` | | `short` (default, 1080×1920 vertical) or `deck` (1920×1080 landscape). |
| `theme` | | Overlay stylesheet from `assets/template/themes/`, e.g. `nightowl-glass`. |
| `title` | ✓ | Browser/tab title of the preview deck. |
| `video_title` | ✓ | **The upload title — unique per video.** ≤ 60 chars. Written to `video.md`. |
| `video_description` | ✓ | 1–3 sentence blurb for the upload. Written to `video.md`. |
| `hashtags` | | `["opencode", "cli"]` — the `#` is added for you. |
| `scenes` | ✓ | Scene objects in order — 4–7 for a `short`, 10–14 for a `deck`. |
| `voice` | | Edge TTS voice. Default `en-US-AndrewMultilingualNeural`. |
| `rate` | | Default `+6%`. `+12%` punchier; `+4%` for long-form decks. |
| `pitch` | | Default `+0Hz`. |
| `accent` | | Primary hex, default `#6ee7ff`. |
| `accent2` | | Gradient partner, default `#a78bfa`. |
| `brand` | | Small handle top-left, e.g. `@yourhandle`. Omit for none. |
| `sources` | | `[{title, url}]` — everything the script's claims rest on. |

## Scene fields

| Field | Applies to | Notes |
| --- | --- | --- |
| `layout` | all | One of the eight below. |
| `narration` | all | What the voice says. The only text that is spoken. |
| `kicker` | all | Small uppercase mono label. Appears at t=0. |
| `headline` | all | The big line. `*stars*` wrap a gradient span. `\n` breaks. |
| `sub` | all | Supporting line under the headline. |
| `items` | bullets, steps, statement, hook, split | Strings, or `{text, cue}`. |
| `code` | code, split | `[lines]`, or `{label, lines}`. |
| `compare` | compare | `{left: {label, items, cue}, right: {...}}`. Right is accented. |
| `stat` | stat | `{value, caption, cue}`. |
| `cta` | cta | Pill button text. |

Timing overrides: `headline_cue`, `sub_cue`, `code_cue`, `cta_cue`, and a `cue`
inside any item or column.

## Layouts

| `layout` | Use for |
| --- | --- |
| `hook` | Scene 1. Oversized headline, optional items. |
| `split` | **`deck` workhorse.** Items left, code right, shared header. |
| `statement` | One claim, big. The default. |
| `bullets` | 2–4 parallel points as accented cards. |
| `steps` | An ordered procedure — cards get numbers. |
| `code` | A command or snippet. Prompts, flags, strings, comments auto-colour. |
| `compare` | Before/after, wrong/right. Two stacked columns. |
| `stat` | One number that carries the scene. |
| `cta` | Final scene. Centred, with a pill. |

## Themes

`theme` names a stylesheet in `assets/template/themes/` that is **appended
after** the format base, so it can restyle anything without the base being
touched. Layer order is: format base → theme → `accent`/`accent2` overrides.
Omit `accent` when using a theme, or you will override the theme's palette.

| Theme | Looks like |
| --- | --- |
| *(none)* | Slate/cyan default |
| `nightowl-glass` | OpenCode's Night Owl palette, frosted-glass panels over blurred colour orbs |
| `light-theme` | Warm paper, burnt-orange accent, teal secondary, white cards — with a dark code slab |

Writing one: set the `--acc` / `--acc-2` / `--ink` custom properties, then
restyle `.item`, `.col`, `.code`, `.cta-pill` as needed.

`light-theme` is worth reading before writing your own: it is a light theme, so
it has to invert things a dark theme never touches — `.captions` switch to dark
ink with a paper-coloured stroke, and `.grad` drops the gradient for a solid
accent because gradient type reads poorly on paper.

Three things to get right in a theme:

- **Only set `z-index` on `.scene`, `.ticks`, `.brand`, `.captions`** — never
  `position`. They are already absolutely positioned by the base sheet, and
  re-declaring `position: relative` drops the captions out of their
  bottom-anchored slot, silently removing them from the whole render.
- **`backdrop-filter` needs something behind it.** Glass over a flat fill just
  looks grey. Put blurred colour orbs on `.stage::before` for it to refract.
- **Light themes must restyle `.captions`.** The base draws them as white text
  with a near-black stroke, which is invisible on paper. Flip both.

## Inline markup

Works in `headline`, `sub`, and any item or column text:

| Syntax | Renders as |
| --- | --- |
| `` `code` `` | An accent-tinted monospace chip — use it for every path, flag, and key |
| `*text*` | The accent gradient |
| `\n` | A line break (headlines only) |

Ligatures are disabled in code, so `--flag` stays two hyphens instead of
collapsing into an em-dash.

## Limits that keep layout intact

The stage is fixed and does not reflow — overflow is clipped, not wrapped onto
a new screen. Stay inside these:

| | `short` (1080×1920) | `deck` (1920×1080) |
| --- | --- | --- |
| `headline` | ≤ 42 chars (`hook` ≤ 34) | ≤ 46 chars |
| `sub` | ≤ 90 chars | ≤ 130 chars |
| `items` | ≤ 4, ≤ 52 chars each | ≤ 4, ≤ 46 chars each |
| `code.lines` | ≤ 6 lines, ≤ 38 chars | ≤ 10 lines, ≤ 52 chars |
| `compare` cols | ≤ 3 items, ≤ 40 chars | ≤ 4 items, ≤ 38 chars |
| `stat.value` | ≤ 5 chars (`75+`, `10x`) | ≤ 5 chars |

In `deck`, a `hook` with a two-line headline fits at most 3 items — the stage
is only 1080px tall and the caption band claims the bottom 208px.

## Worked example

```json
{
  "topic": "why rust's borrow checker is worth the fight",
  "title": "Rust's borrow checker, in 45 seconds",
  "accent": "#ffb86c",
  "accent2": "#ff6e6e",
  "brand": "@devnotes",
  "scenes": [
    {
      "layout": "hook",
      "kicker": "Rust",
      "headline": "Everyone *quits* at the borrow checker",
      "narration": "Almost everyone who tries Rust hits the borrow checker and wants to quit. Here's why you shouldn't."
    },
    {
      "layout": "compare",
      "headline": "What it actually stops",
      "compare": {
        "left":  {"label": "C++", "items": ["Use after free", "Data races"], "cue": "in c plus plus"},
        "right": {"label": "Rust", "items": ["Caught at compile time"], "cue": "at compile time"}
      },
      "narration": "In C plus plus, a use after free or a data race ships to production and crashes at three a.m. In Rust the same bug is caught at compile time. It never runs."
    },
    {
      "layout": "steps",
      "headline": "The whole rule",
      "items": [
        {"text": "Many readers", "cue": "many readers"},
        {"text": "*Or* one writer", "cue": "or one writer"},
        {"text": "Never both", "cue": "never both"}
      ],
      "narration": "The entire rule is this. Many readers, or one writer. Never both at once. That's it — every borrow checker error is that one rule."
    },
    {
      "layout": "cta",
      "headline": "Push through *week one*",
      "sub": "It stops being a fight and starts being a spell-checker.",
      "cta": "Follow for more Rust",
      "narration": "Push through the first week. After that it stops feeling like a fight and starts feeling like a spell checker for concurrency. Follow for more."
    }
  ],
  "sources": [
    {"title": "The Rust Book — Ownership", "url": "https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html"}
  ]
}
```

~112 words of narration ≈ 43 seconds.

## A `deck` scene

`split` is what most long-form technical slides want — the claim as cards on
the left, the config or command it refers to on the right:

```json
{
  "layout": "split",
  "kicker": "05 — Permissions",
  "headline": "Allow, ask, or *deny*",
  "items": [
    {"text": "Last matching pattern wins", "cue": "the last matching rule wins"},
    {"text": "Reading `.env` is denied by default", "cue": "denied out of the box"}
  ],
  "code": {
    "label": "opencode.json",
    "lines": ["\"bash\": {", "  \"git *\": \"allow\",", "  \"rm *\":  \"deny\"", "}"]
  },
  "code_cue": "glob patterns",
  "narration": "The bash permission takes glob patterns, and the last matching rule wins…"
}
```

## Word budget

Edge TTS at `+6%` ≈ **2.6 words/second**.

| Target | Words |
| --- | --- |
| 30s | ~78 |
| 45s | ~117 |
| 60s (`short` max) | ~156 |
| 5 min | ~780 |
| 7 min | ~1,090 |
| 10 min | ~1,560 |

For a `deck`, budget per scene: ~90 words ≈ 35s is a comfortable slide. Under
20s feels rushed for a landscape slide; over 45s and the visuals go stale
before the voice moves on.

Count before generating — the audio stage measures the real duration and warns
when you're over, but a re-record costs a full pipeline run.
