# Hole-In-One

A collection of reusable skills, agents, plugins, and configurations for AI-assisted software development. Includes structured workflows (skills), role-based agents (planning, coding, evaluating), plugins (token usage tracking), and an opencode config to tie it all together.

## Skills

| Skill | Description |
|-------|-------------|
| [interrogate-me](./.opencode/skills/interrogate-me/) | Complete technical specification interrogation — turns vague ideas into implementation-ready specs via MCQ-driven design tree walking |
| [deepwrite](./.opencode/skills/deepwrite/) | Generate opinionated white papers from deep research — autonomous web research, source trust scoring, and a persistent knowledge base |
| [humanize](./.opencode/skills/humanize/) | Remove signs of AI-generated writing using 47 researched patterns, a rapid checklist, and a mechanical pre-pass |
| [youtube-short-by-topic](./.opencode/skills/youtube-short-by-topic/) | Turn a topic into a finished narrated MP4 — research, script, Edge-TTS voiceover, animated deck, captions. Vertical shorts or landscape explainers |
| [youtube-keyword-research](./.opencode/skills/youtube-keyword-research/) | Rank the top keywords/models trending on YouTube for any niche — autocomplete API + top-channel RSS feeds, recency-windowed, report + content hooks |

## Plugins

| Plugin | Description |
|--------|-------------|
| [token-count](./.opencode/plugins/) | Per-session token & cost tracking — persists a ledger, logs each model call, shows a TUI sidebar panel with live token usage |

### Installing a plugin

Copy the plugin files into the project's `.opencode/plugins/` directory (or `~/.config/opencode/plugins/` for global use). opencode auto-loads every plugin found there. The token-count plugin requires `@opencode-ai/plugin` in `.opencode/package.json`.

## Agents

Three specialized agents that work together in a pipeline: **Plan → Code → Evaluate**.

| Agent | Purpose | Permissions |
|-------|---------|-------------|
| [planning-agent](./.opencode/agents/planning-agent.md) | Requirements gathering, specs, PRDs, technical design docs | Read-only (no edits, no shell) |
| [coding-agent](./.opencode/agents/coding-agent.md) | Production-ready code from specifications | Full access (edit + shell) |
| [evaluating-agent](./.opencode/agents/evaluating-agent.md) | Code review, security audit, quality assessment | Read-only (no edits, no shell) |

### Workflow

```
User idea → planning-agent (spec) → coding-agent (implementation) → evaluating-agent (review)
```

The planning-agent never writes code. The coding-agent never writes specs. The evaluating-agent never rewrites — only reports. Each agent is scoped to its job.

## Configuration

The `opencode.jsonc` file configures the agents for use with [opencode](https://opencode.ai):

```jsonc
{
  "agent": {
    "planning-agent": {
      "mode": "primary",
      "model": "opencode-go/qwen3.7-plus",
      "permission": { "edit": "deny", "bash": "deny" }
    },
    "coding-agent": {
      "mode": "primary",
      "model": "opencode-go/kimi-k2.7-code",
      "permission": { "edit": "allow", "bash": "allow" }
    },
    "evaluating-agent": {
      "mode": "primary",
      "model": "opencode-go/deepseek-v4-flash",
      "permission": { "edit": "deny", "bash": "deny" }
    }
  }
}
```

## Structure

```
hole-in-one/
├── README.md
├── opencode.jsonc
├── .opencode/
│   ├── agents/
│   │   ├── planning-agent.md
│   │   ├── coding-agent.md
│   │   └── evaluating-agent.md
│   ├── plugins/
│   │   ├── token-count.ts
│   │   └── token-count-tui.tsx
│       └── skills/
│           ├── interrogate-me/SKILL.md
│           ├── deepwrite/
│           │   ├── SKILL.md
│           │   ├── config.json
│           │   └── scripts/kb.py
│           ├── humanize/
│           │   ├── SKILL.md
│           │   ├── README.md
│           │   ├── artifacts/
│           │   └── scripts/humanize.py
│           └── youtube-keyword-research/
│               ├── SKILL.md
│               └── scripts/research.py
```

## Adding a Skill

1. Create a new directory `.opencode/skills/<skill-name>/`
2. Add a `SKILL.md` file with YAML frontmatter (name, description, version, metadata)
3. Define the workflow phases, MCQ formats, and output templates
4. Update this README

## Adding an Agent

1. Create a new `.md` file in `.opencode/agents/`
2. Add YAML frontmatter with `description` and `mode`
3. Define the agent's approach, constraints, and example flow
4. Add a corresponding entry in `opencode.jsonc` with model and permissions
5. Update this README

## License

MIT
