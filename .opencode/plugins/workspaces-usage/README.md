# opencode-workspaces-usage

OpenCode plugin (server + TUI) that lists git worktrees (workspaces) for the
current project and aggregates session counts and cost per worktree.

## Load locally

Add the plugin to your OpenCode config:

```jsonc
// ~/.config/opencode/opencode.jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["/private/tmp/opencode-workspaces-usage-plugin"]
}
```

Or for TUI-only usage, add to `~/.config/opencode/cli.json`:

```json
{ "plugins": ["/private/tmp/opencode-workspaces-usage-plugin"] }
```

## Use

- Command palette: "Show workspaces usage"
- Slash command: `/workspaces` (alias `/usage`)
