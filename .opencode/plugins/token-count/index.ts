import { Plugin } from "@opencode/plugin"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import { dirname, join } from "node:path"
import { homedir } from "node:os"

type Tokens = {
  input: number
  output: number
  reasoning: number
  cacheRead: number
  cacheWrite: number
}

type CallRecord = {
  time: number
  model: string
  tokens: Tokens
  cost: number
}

type SessionState = {
  callsCount: number
  calls: CallRecord[]
  tokens: Tokens
  cost: number
}

type Ledger = {
  sessions: Record<string, SessionState>
  total: Tokens & { cost: number }
}

type Options = {
  ledgerPath?: string
  keepCalls?: number
  log?: boolean
}

const ZERO: Tokens = { input: 0, output: 0, reasoning: 0, cacheRead: 0, cacheWrite: 0 }

const defaultLedgerPath = () => {
  const base = process.env.XDG_DATA_HOME || join(homedir(), ".local", "share")
  return join(base, "opencode", "token-count.json")
}

const add = (a: Tokens, b: Tokens) => {
  a.input += b.input
  a.output += b.output
  a.reasoning += b.reasoning
  a.cacheRead += b.cacheRead
  a.cacheWrite += b.cacheWrite
}

const delta = (next: Tokens, prev: Tokens): Tokens => ({
  input: Math.max(0, next.input - prev.input),
  output: Math.max(0, next.output - prev.output),
  reasoning: Math.max(0, next.reasoning - prev.reasoning),
  cacheRead: Math.max(0, next.cacheRead - prev.cacheRead),
  cacheWrite: Math.max(0, next.cacheWrite - prev.cacheWrite),
})

const anyPositive = (t: Tokens) =>
  t.input > 0 || t.output > 0 || t.reasoning > 0 || t.cacheRead > 0 || t.cacheWrite > 0

const fmt = (n: number) => new Intl.NumberFormat("en-US").format(Math.round(n))

export default Plugin.define({
  id: "token-count",

  async setup(ctx) {
    const options = (ctx.options ?? {}) as Options
    const ledgerPath =
      typeof options.ledgerPath === "string" && options.ledgerPath.length > 0
        ? options.ledgerPath
        : defaultLedgerPath()
    const keepCalls =
      typeof options.keepCalls === "number" ? Math.max(1, options.keepCalls) : 200
    const logEnabled = options.log !== false

    const states = new Map<string, SessionState>()
    const models = new Map<string, string>()
    const lastSeen = new Map<string, Tokens>()
    const lastCost = new Map<string, number>()

    const getState = (id: string): SessionState => {
      let state = states.get(id)
      if (!state) {
        state = { callsCount: 0, calls: [], tokens: { ...ZERO }, cost: 0 }
        states.set(id, state)
      }
      return state
    }

    try {
      const ledger = JSON.parse(await readFile(ledgerPath, "utf8")) as Ledger
      for (const [id, state] of Object.entries(ledger.sessions ?? {})) {
        states.set(id, { ...state, tokens: { ...ZERO, ...state.tokens } })
      }
    } catch {
      // no ledger yet
    }

    let writing: Promise<void> = Promise.resolve()
    const persist = () => {
      writing = writing
        .then(async () => {
          const total: Tokens & { cost: number } = { ...ZERO, cost: 0 }
          for (const state of states.values()) {
            add(total, state.tokens)
            total.cost += state.cost
          }
          const ledger: Ledger = { sessions: Object.fromEntries(states), total }
          await mkdir(dirname(ledgerPath), { recursive: true })
          await writeFile(ledgerPath, JSON.stringify(ledger, null, 2))
        })
        .catch(() => {})
      return writing
    }

    const controller = new AbortController()

    void (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          switch (event.type) {
            case "session.model.selected":
              models.set(
                event.data.sessionID,
                `${event.data.model.providerID}/${event.data.model.id}`,
              )
              break

            case "session.usage.updated": {
              const { sessionID } = event.data
              const state = getState(sessionID)
              const current: Tokens = {
                input: event.data.tokens.input,
                output: event.data.tokens.output,
                reasoning: event.data.tokens.reasoning,
                cacheRead: event.data.tokens.cache.read,
                cacheWrite: event.data.tokens.cache.write,
              }
              const cost = event.data.cost

              const step = delta(current, lastSeen.get(sessionID) ?? ZERO)
              const costStep = Math.max(0, cost - (lastCost.get(sessionID) ?? 0))

              lastSeen.set(sessionID, current)
              lastCost.set(sessionID, cost)

              if (!anyPositive(step) && costStep <= 0) break

              add(state.tokens, step)
              state.cost += costStep
              state.callsCount++
              state.calls.push({
                time: Date.now(),
                model: models.get(sessionID) ?? "unknown",
                tokens: step,
                cost: costStep,
              })
              if (state.calls.length > keepCalls) {
                state.calls.splice(0, state.calls.length - keepCalls)
              }

              if (logEnabled) {
                console.log(
                  `token-count: ${sessionID} +${fmt(step.input)} in / ${fmt(step.output)} out`,
                )
              }

              await persist()
              break
            }

            case "session.idle":
              await persist()
              break

            case "session.deleted":
              states.delete(event.data.sessionID)
              models.delete(event.data.sessionID)
              lastSeen.delete(event.data.sessionID)
              lastCost.delete(event.data.sessionID)
              await persist()
              break
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error("token-count: event stream failed", error)
        }
      }
    })()

    return async () => {
      controller.abort()
      await persist()
    }
  },
})
