# Interrogate-Me

A skill for generating comprehensive technical specifications through structured interrogation.

## Project Structure

- `.opencode/agents/` - Custom agents (planning, coding, evaluating)
- `.opencode/skills/interrogate-me/` - Main interrogate-me skill
- `.opencode/skills/deepwrite/` - Deep research to white papers (SKILL.md + scripts + config)

## Agents

- **planning-agent**: Interview-driven requirements gathering and spec generation
- **coding-agent**: Production-ready code generation from specifications
- **evaluating-agent**: Code quality review and security auditing
- **pr-review-agent**: Pull request merge gate — decides whether a PR should be merged (APPROVE / APPROVE WITH COMMENTS / REQUEST CHANGES / BLOCK) with evidence-backed gate checks
- **go-minimalism-expert**: Minimal, idiomatic Go — reviews, refactors, and writes Go with the fewest lines that solve the problem

## Skills

- **interrogate-me**: Complete technical specification interrogation with MCQ-driven design tree walking
- **deepwrite**: Generate opinionated white papers from deep research (web research, source trust scoring, persistent KB)
- **youtube-keyword-research**: Rank top keywords/models trending on YouTube for any niche (autocomplete API + RSS feeds, recency-windowed)

## Commands

- `/interrogate-me` - Full technical spec pipeline
- `/interrogate-me lightweight` - Small change path (<1 day)
- `/interrogate-me gap-fill` - Audit existing draft
- `/interrogate-me architecture` - Skip product framing
- `/interrogate-me wayfinder` - Multi-session map
