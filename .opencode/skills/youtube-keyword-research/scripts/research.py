#!/usr/bin/env python3
"""YouTube keyword research for a niche (default: LLM/SLM models).

Combines the YouTube autocomplete API with top-channel RSS feeds, filters to a
recency window, and ranks model families + topic clusters from real titles.

Usage:
  python3 research.py [--seeds "llm,slm,..."] [--channels "handle:cid,..."]
      [--days 7] [--out youtube-top-keywords.md]

No API keys required. Needs network access.
"""

import argparse
import collections
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NS = {"a": "http://www.w3.org/2005/Atom"}

DEFAULT_SEEDS = [
    "llm", "slm", "small language model", "open weights", "open source llm",
    "ai model", "llama", "qwen", "gemma", "phi", "deepseek", "mistral",
    "reasoning model", "agentic ai", "multimodal model", "local llm",
    "on device ai", "model release", "ai news", "llm ranking", "open source ai",
]

DEFAULT_CHANNELS = {
    "matthew_berman": "UCawZsQWqfGSbCI5yjkdVkTA",
    "ai_explained": "UCNJ1Ymd5yFuUPtn21xtRbbw",
    "two_minute_papers": "UCbfYPyITQ-7l4upoX8nvctg",
    "1littlecoder": "UCpV_X0VrL8-jg3t6wYGS-1g",
    "wes_roth": "UCqcbQf6yw5KzRoDDcZ_wBSw",
    "matt_wolfe": "UChpleBmo18P08aKCIgti38g",
    "james_layne": "UCLQHR2BxEfw90QmIwSzkikw",
    "lukes_dev_lab": "UC6YL31AicZzw1-gap7zBm9A",
    "fahd_mirza": "UCPix8N6PMRI4KzgyjuZeF0g",
    "ai_advantage": "UCHhYXsLBEVVnbvsq57n1MTQ",
    "mattvidpro": "UC06GdmaEdCdCFwR3NvszloQ",
}

MODEL_FAMILIES = {
    "qwen": ["qwen", "qwen3", "qwen 3", "qwen3.8", "qwen3.6", "qwen3.5", "omni flash", "27b", "3.8 max", "3.8 flash"],
    "gemma": ["gemma", "gemma 4", "gemma3"],
    "deepseek": ["deepseek", "deepseek v4", "deepseek v3"],
    "llama": ["llama", "llama 4", "llama.cpp"],
    "glm": ["glm", "glm 5", "glm 5.3", "z.ai", "zhipu"],
    "phi": ["phi-4", "phi4", "microsoft phi"],
    "mistral": ["mistral", "ministral", "codestral"],
    "kimi": ["kimi", "kimi k3", "moonshot"],
    "claude": ["claude", "anthropic"],
    "gpt": ["gpt-6", "gpt-5", "openai", "chatgpt"],
    "gemini": ["gemini", "google"],
    "open weights": ["open weights", "open source", "open-source", "open model"],
    "local/inference": ["local", "locally", "llama.cpp", "vllm", "ollama", "16gb", "run locally", "quantiz"],
    "slm/small": ["small", "4b", "1.4b", "slm", "small language model"],
    "reasoning": ["reasoning", "think", "rlcd", "rl", "r1", "o3", "test-time"],
    "multimodal": ["multimodal", "omni", "vision", "images", "audio", "video", "realtime"],
    "agent": ["agent", "agents", "agentic", "tool", "mcp", "coding agent"],
    "benchmark": ["benchmark", "tested", "test", "compare", "comparison", "review"],
    "news": ["news", "ai news", "released", "release", "drops"],
    "safety/policy": ["safety", "pace", "slow down", "warning", "risk", "doom", "jailbreak", "hack"],
}

STOPWORDS = {
    "the", "and", "for", "you", "your", "are", "what", "this", "that", "with",
    "how", "did", "can", "has", "its", "was", "were", "really", "from", "out",
    "here", "more", "back", "still", "needs", "now", "new", "made", "all",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read()


def suggest(seed):
    """Return autocomplete suggestions for a seed term."""
    url = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&hl=en&q={seed}"
    try:
        body = fetch(url).decode("utf-8", "ignore")
        inner = body[body.index("(") + 1: body.rindex(")")]
        return [x[0] for x in json.loads(inner)[1]]
    except Exception:
        return []


def resolve_handle(handle):
    """Resolve a YouTube @handle to a channel_id."""
    url = f"https://www.youtube.com/@{handle}"
    try:
        body = fetch(url).decode("utf-8", "ignore")
        m = re.search(r'"externalId":"(UC[^"]+)"', body)
        return m.group(1) if m else None
    except Exception:
        return None


def channel_titles(cid, cutoff):
    """Return (published_datetime, title) entries from a channel feed."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    try:
        root = ET.fromstring(fetch(url))
    except Exception:
        return []
    out = []
    for e in root.findall("a:entry", NS):
        t = e.find("a:title", NS)
        p = e.find("a:published", NS)
        if t is None or p is None or not t.text:
            continue
        try:
            dt = datetime.fromisoformat(p.text.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
        if dt >= cutoff:
            out.append((dt, t.text))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=",".join(DEFAULT_SEEDS), help="comma-separated seed terms")
    ap.add_argument("--channels", default="", help="comma-separated name:cid or handle:cname pairs (resolves handles)")
    ap.add_argument("--days", type=int, default=7, help="recency window in days")
    ap.add_argument("--out", default="youtube-top-keywords.md", help="output markdown path")
    args = ap.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days)
    start, end = cutoff.date().isoformat(), datetime.now().date().isoformat()

    # 1) autocomplete
    print(f"[1/3] Autocomplete queries ({args.days}d)…")
    sugg = collections.Counter()
    for seed in [s.strip() for s in args.seeds.split(",") if s.strip()]:
        for term in suggest(seed):
            sugg[term] += 1

    # 2) channels
    print("[2/3] Resolving channels…")
    channels = {}
    for spec in [c.strip() for c in args.channels.split(",") if c.strip()]:
        name, _, val = spec.partition(":")
        if not val:  # bare handle
            handle = name.lstrip("@")
            channels[handle] = resolve_handle(handle)
        else:
            channels[name] = val if val.startswith("UC") else resolve_handle(val)
    if not channels:
        channels = dict(DEFAULT_CHANNELS)

    print("[3/3] Pulling RSS feeds…")
    titles = []
    for name, cid in channels.items():
        if not cid:
            print(f"  !! {name}: could not resolve channel")
            continue
        for dt, t in channel_titles(cid, cutoff):
            titles.append((dt, name, t))
    titles.sort(reverse=True)

    # 3) keyword analysis
    fam = collections.Counter()
    for _, _, t in titles:
        tl = t.lower()
        for cat, kws in MODEL_FAMILIES.items():
            if any(k in tl for k in kws):
                fam[cat] += 1

    words = []
    for _, _, t in titles:
        words.append([w for w in re.split(r"[^a-z0-9]+", t.lower()) if len(w) > 2])
    bi = collections.Counter()
    for wl in words:
        for i in range(len(wl) - 1):
            bi[(wl[i], wl[i + 1])] += 1
    uni = collections.Counter(w for wl in words for w in wl)

    # 4) report
    lines = [
        f"# YouTube Top Keywords — {start} → {end}",
        "",
        f"Source: autocomplete API + RSS feeds of {len(channels)} channels = "
        f"**{len(titles)} videos published in the last {args.days} days.**",
        "",
        "## Model-family keyword hits (titles)",
        "",
        "| Category | Hits |",
        "|----------|------|",
    ]
    for cat, c in fam.most_common():
        lines.append(f"| {cat} | {c} |")
    lines += ["", "## Top bigrams", "", "| Bigram | Count |", "|--------|-------|"]
    for b, c in bi.most_common(15):
        lines.append(f"| {b[0]} {b[1]} | {c} |")
    lines += ["", "## Top unigrams", "", "| Term | Count |", "|------|-------|"]
    for w, c in uni.most_common(40):
        if w not in STOPWORDS and c >= 2:
            lines.append(f"| {w} | {c} |")
    lines += ["", "## Recent videos", ""]
    for dt, name, t in titles:
        lines.append(f"- {dt.date()} [{name}] {t}")
    lines += [
        "",
        "## Method (reproducible)",
        "",
        "```",
        'curl "https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&q=<seed>"',
        'curl "https://www.youtube.com/feeds/videos.xml?channel_id=<ID>"',
        "```",
        "",
        "Note: unexplained high-frequency terms still need a web-search pass.",
    ]

    with open(args.out, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {args.out}: {len(titles)} videos, {len(fam)} categories.")


if __name__ == "__main__":
    sys.exit(main())