---
name: youtube-keyword-research
description: >-
  Research the top keywords, model names, and topic angles about any niche —
  by default LLMs and SLMs — that are actually trending on YouTube right now.
  Use when the user wants to know what AI/model keywords people search and
  create videos about ("top keywords", "trending keywords", "what's hot",
  "keyword research", "what to make a video about"), wants a content/SEO angle
  for YouTube, or wants to identify trending LLM/SLM model names. Combines the
  YouTube search suggest (autocomplete) API with the RSS feeds of top channels
  in the niche, filters to a configurable recency window (default: past 7 days),
  and ranks model families and topic clusters by real title frequency. Outputs
  a ranked markdown report with content-hook recommendations.
version: 1.0.0
metadata:
  author: Vic Gupta
  license: MIT
---

# YouTube Keyword Research

Find out what's actually trending about a topic on YouTube right now — not
what you guess is trending. Two free, no-API-key signals:

1. **YouTube autocomplete** (`suggestqueries.google.com`) — what people are
   literally typing into the search box right now.
2. **Top-channel RSS feeds** (`youtube.com/feeds/videos.xml?channel_id=…`) —
   what creators are actually publishing, filtered by published timestamp.

The agent runs the pipeline, ranks keywords, and writes a markdown report.

```
topic/seeds ──► autocomplete queries ──► trending search terms
            ──► channel RSS feeds    ──► titles published in window
            ──► keyword frequency (model families + topic clusters)
            ──► ranked markdown report + content hooks
```

## Workflow

### 1 · Set the topic and recency window

- Default topic: **LLM / SLM models**. Default window: **past 7 days**.
- Ask only if the user didn't already specify a topic, channel list, or window.
- A window is expressed as a cutoff date; report includes the exact
  `YYYY-MM-DD` range it covers.

### 2 · Query the autocomplete API

For each seed term, hit:

```
https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&hl=en&q=<seed>
```

The response is JSONP (`window.google.ac.h([...])`) — strip the wrapper before
parsing. Collect all returned suggestions as raw search keywords.

Default LLM/SLM seed set (extend from context when the topic differs):

```
llm, slm, small language model, open weights, open source llm, ai model,
llama, qwen, gemma, phi, deepseek, mistral, reasoning model, agentic ai,
multimodal model, local llm, on device ai, model release, ai news,
llm ranking, open source ai
```

Filter out suggestions that are clearly off-topic (the autocomplete API is
global — "slm" also returns unrelated popular queries). Keep only terms that
match the topic's model names, techniques, or formats.

### 3 · Pull top-channel RSS feeds

Resolve channel IDs from handles if you don't have them:

```
curl -s -A "Mozilla/5.0" "https://www.youtube.com/@<handle>" | grep -o '"externalId":"UC[^"]*"'
```

Then fetch each feed and filter entries by the `published` timestamp:

```
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
```

Default channel set for AI/LLM content:

| Channel | Handle |
|---------|--------|
| Matthew Berman | `@matthew_berman` |
| AI Explained | `@aiexplained-official` |
| Two Minute Papers | `@TwoMinutePapers` |
| 1littlecoder | `@1littlecoder` |
| Wes Roth | `@wesroth` |
| Matt Wolfe | `@mreflow` |
| James Layne | `@JamesLayne` |
| Luke's Dev Lab | `@lukesdevlab` |
| Fahd Mirza | `@FahdMirza` |
| AI Advantage | `@aiadvantage` |
| MattVidPro | `@MattVidPro` |

Report how many videos landed in the window (e.g. "49 videos in last 7 days").

### 4 · Extract and rank keywords

From the in-window titles:

1. **Model-family hits** — count titles mentioning each model/company
   (qwen, gemma, deepseek, llama, glm, phi, mistral, kimi, claude, gpt,
   gemini, open weights, local/inference, slm/small, reasoning, multimodal,
   agent, benchmark, news, safety).
2. **Bigrams/unigrams** — tokenize titles, count adjacent-word pairs and
   single terms, drop stopwords.
3. **Cross-check mystery terms** — any high-frequency term you don't recognize
   (e.g. "Jev", "Realtime Venus") must be web-searched so the report explains
   what it is instead of just listing it.

### 5 · Write the report

Markdown report with:

- **Header**: topic, exact date window, number of sources/videos.
- **Hottest model keywords** — ranked table (keyword / hit count / context).
- **Topic clusters** — what creators and searchers care about, with counts.
- **Content-hook signals** — actionable angles ("run <model> locally",
  "vs" comparisons, underserved sub-topics).
- **Raw method** — the exact curl/python commands so it's reproducible.

Save as `youtube-top-keywords-<start>-<end>.md` in the working directory.

### 6 · Optional follow-ups

- Broaden/narrow the window (e.g. 24h, 30 days).
- Swap the channel set for another niche (MLOps, local AI, robotics…).
- Expand seeds with the newly discovered model names and re-run.

## Research principles

- **Prefer signal over volume.** The autocomplete API returns global noise;
  filter for topic relevance before ranking.
- **No guesses on unknown terms.** Every headline keyword must be explainable
  — web-search any model name you don't recognize.
- **Date every claim.** The whole point is recency; the report must state its
  exact window so results age honestly.
- **Both sides of the funnel.** Search suggest = demand (what people type);
  RSS titles = supply (what creators publish). A keyword that appears in both
  is the strongest signal.

## Usage

- `/youtube-keyword-research` — default: LLM/SLM, past 7 days
- `/youtube-keyword-research <topic>` — any topic, past 7 days
- `/youtube-keyword-research <topic> --days 30` — custom window
- `/youtube-keyword-research --channels <csv>` — custom channel set