import { Plugin } from "@opencode/plugin/tui"
import type { Context } from "@opencode/plugin/tui/context"
import { createMemo, For, Show } from "solid-js"

const fmt = new Intl.NumberFormat("en-US")
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })

type CallSummary = {
  input: number
  output: number
  reasoning: number
  cacheRead: number
  cacheWrite: number
  cost: number
}

type Totals = CallSummary & { count: number }

function collect(ctx: Context, sessionID: string): CallSummary[] {
  return (ctx.data.session.message.list(sessionID) ?? [])
    .filter((message) => message.type === "assistant")
    .map((message) => {
      const assistant = message as Extract<typeof message, { type: "assistant" }>
      return {
        input: assistant.tokens?.input ?? 0,
        output: assistant.tokens?.output ?? 0,
        reasoning: assistant.tokens?.reasoning ?? 0,
        cacheRead: assistant.tokens?.cache?.read ?? 0,
        cacheWrite: assistant.tokens?.cache?.write ?? 0,
        cost: assistant.cost ?? 0,
      }
    })
    .filter((call) => call.input > 0 || call.output > 0 || call.reasoning > 0)
}

function summarize(calls: CallSummary[]): Totals {
  const totals: Totals = {
    input: 0,
    output: 0,
    reasoning: 0,
    cacheRead: 0,
    cacheWrite: 0,
    cost: 0,
    count: calls.length,
  }
  for (const call of calls) {
    totals.input += call.input
    totals.output += call.output
    totals.reasoning += call.reasoning
    totals.cacheRead += call.cacheRead
    totals.cacheWrite += call.cacheWrite
    totals.cost += call.cost
  }
  return totals
}

function TokenCountView(props: { ctx: Context; sessionID: string; maxCalls: number }) {
  const calls = createMemo(() => collect(props.ctx, props.sessionID))
  const totals = createMemo(() => summarize(calls()))
  const recent = createMemo(() => calls().slice(-props.maxCalls))
  const firstIndex = () => calls().length - recent().length

  return (
    <box>
      <text fg={props.ctx.theme.text.base}>
        <b>Token Usage</b>
      </text>
      <text fg={props.ctx.theme.text.muted}>
        {fmt.format(totals().input)} in / {fmt.format(totals().output)} out
      </text>
      <Show when={totals().reasoning > 0}>
        <text fg={props.ctx.theme.text.muted}>+{fmt.format(totals().reasoning)} reasoning</text>
      </Show>
      <Show when={totals().cacheRead > 0}>
        <text fg={props.ctx.theme.text.muted}>{fmt.format(totals().cacheRead)} cache read</text>
      </Show>
      <Show when={totals().cacheWrite > 0}>
        <text fg={props.ctx.theme.text.muted}>{fmt.format(totals().cacheWrite)} cache written</text>
      </Show>
      <text fg={props.ctx.theme.text.muted}>
        {totals().count} call{totals().count === 1 ? "" : "s"} · {money.format(totals().cost)}
      </text>
      <For each={recent()}>
        {(call, index) => (
          <text fg={props.ctx.theme.text.muted}>
            {firstIndex() + index() + 1}. {fmt.format(call.input)} in / {fmt.format(call.output)} out
          </text>
        )}
      </For>
    </box>
  )
}

export default Plugin.define({
  id: "token-count",

  setup(ctx) {
    const options = ctx.options as { maxCalls?: number; toast?: boolean }
    const maxCalls =
      typeof options.maxCalls === "number"
        ? Math.min(20, Math.max(1, Math.round(options.maxCalls)))
        : 3

    const stop =
      options.toast === true
        ? ctx.data.on("session.idle", ({ data }) => {
            const totals = summarize(collect(ctx, data.sessionID))
            const reasoning =
              totals.reasoning > 0 ? ` (+${fmt.format(totals.reasoning)} reasoning)` : ""
            ctx.ui.toast.show({
              message: `token-count: session ${fmt.format(totals.input)} in / ${fmt.format(totals.output)} out (${totals.count} calls)${reasoning}`,
              variant: "info",
              sessionID: data.sessionID,
            })
          })
        : undefined

    const unregister = ctx.ui.slot({
      append: "sidebar.content",
      render: ({ sessionID }) => (
        <TokenCountView ctx={ctx} sessionID={sessionID} maxCalls={maxCalls} />
      ),
    })

    return () => {
      stop?.()
      unregister()
    }
  },
})
