import { Plugin } from "@opencode/plugin/tui"
import { createSignal, For } from "solid-js"

type Budget = { name?: string; limit?: number; used?: number; remaining?: number }
type GoPeriod = { percent?: number; limited?: boolean; resetsAt?: number }
type UsageData = {
  workspace?: { id?: string; name?: string; usageURL?: string }
  go?: { rolling?: GoPeriod; weekly?: GoPeriod; monthly?: GoPeriod }
  budgets?: Budget[]
}

export default Plugin.define({
  id: "workspaces.usage",
  setup(context) {
    const [lines, setLines] = createSignal<string[]>(["Loading usage..."])

    async function load() {
      try {
        const response = await context.client.experimental.usage.limits({})
        const data = (response?.data ?? {}) as UsageData
        const output: string[] = []
        output.push(data.workspace?.name ?? "Workspace")
        const go = data.go
        if (go) {
          const fmt = (label: string, p?: GoPeriod) =>
            p ? `${label}: ${p.percent ?? 0}%${p.limited ? " (limited)" : ""}` : `${label}: n/a`
          output.push(fmt("Rolling", go.rolling))
          output.push(fmt("Weekly", go.weekly))
          output.push(fmt("Monthly", go.monthly))
        }
        const budgets = data.budgets ?? []
        if (budgets.length) {
          for (const b of budgets) {
            const limit = b.limit ?? 0
            const used = b.used ?? 0
            const remaining = b.remaining ?? Math.max(0, limit - used)
            output.push(`${b.name ?? "Budget"}: $${remaining.toFixed(2)} left`)
          }
        } else {
          output.push("No budgets")
        }
        setLines(output)
      } catch {
        setLines(["Usage unavailable"])
      }
    }

    void load()
    const timer = setInterval(() => void load(), 60000)

    context.ui.slot({
      append: "sidebar.content",
      render: () => (
        <box flexDirection="column" gap={0}>
          <text>Usage</text>
          <For each={lines()}>{(line: string) => <text>{line}</text>}</For>
        </box>
      ),
    })

    context.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "workspaces.usage.refresh",
          title: "Refresh workspace usage",
          group: "Workspaces",
          palette: true,
          slash: { name: "usage" },
          run: async () => {
            await load()
            context.ui.toast.show({ message: "Usage refreshed", variant: "success" })
          },
        },
      ],
    }))

    return () => clearInterval(timer)
  },
})
