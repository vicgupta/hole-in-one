# Hole-In-One

A collection of reusable skills, agents, plugins, and configurations for AI-assisted software development.

## Project Structure

- `.opencode/agents/` - Custom agents (planning, coding, evaluating, pr-review, go-minimalism-expert)
- `.opencode/plugins/` - Token & cost tracking — server plugin (`index.ts`) plus a TUI sidebar panel (`tui.tsx`), V2 `@opencode/plugin` layout
- `.opencode/skills/` - One directory per skill, each with a `SKILL.md`
- `opencode.jsonc` - Agent models and permissions

## Agents

- **planning-agent**: Interview-driven requirements gathering and spec generation
- **coding-agent**: Production-ready code generation from specifications
- **evaluating-agent**: Code quality review and security auditing
- **pr-review-agent**: Pull request merge gate — decides whether a PR should be merged (APPROVE / APPROVE WITH COMMENTS / REQUEST CHANGES / BLOCK) with evidence-backed gate checks
- **go-minimalism-expert**: Minimal, idiomatic Go — reviews, refactors, and writes Go with the fewest lines that solve the problem

## Skills

- **interrogate-me**: Complete technical specification interrogation with MCQ-driven design tree walking
- **deepwrite**: Generate opinionated white papers from deep research (web research, source trust scoring, persistent KB)
- **humanize**: Remove signs of AI-generated writing (47 patterns, rapid checklist, mechanical pre-pass)
- **create-ant-factory**: Turn labelled GitHub issues into reviewed PRs — coding agents in Upstash Box sandboxes started by GitHub Actions
- **youtube-keyword-research**: Rank top keywords/models trending on YouTube for any niche (autocomplete API + RSS feeds, recency-windowed)
- **youtube-short-by-topic**: Turn a topic into a narrated MP4 — research, script, Edge-TTS voiceover, animated deck, captions

## Commands

- `/interrogate-me` - Full technical spec pipeline, auto-detect mode
- `/interrogate-me lightweight` - Small change path (<1 day)
- `/interrogate-me gap-fill` - Audit existing draft
- `/interrogate-me architecture` - Skip product framing
- `/interrogate-me wayfinder` - Multi-session map
- `/interrogate-me resume` - Continue from Decisions[] / map
