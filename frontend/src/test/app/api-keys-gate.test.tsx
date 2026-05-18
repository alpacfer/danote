import { render, screen, fireEvent } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ApiKeysGate } from "@/app/auth/api-keys-gate"

function trialStatus(overrides: Record<string, unknown> = {}) {
  return {
    enabled: true,
    available: true,
    opted_in: false,
    keys_configured: false,
    limit: 50,
    used: 0,
    remaining: 50,
    resets_on: "2026-05-19",
    ...overrides,
  }
}

function accountStatus(opted_in: boolean) {
  return {
    keys_configured: false,
    providers: {},
    missing: ["gemini", "deepl", "azure_translation", "azure_tts"],
    trial: trialStatus({ opted_in }),
  }
}

function ok(payload: unknown): Response {
  return { ok: true, status: 200, json: async () => payload } as Response
}

describe("ApiKeysGate free trial", () => {
  let optedIn = false

  beforeEach(() => {
    optedIn = false
    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method ?? "GET").toUpperCase()
      if (url.includes("/api/account/trial/opt-in") && method === "POST") {
        optedIn = true
        return ok({ trial: trialStatus({ opted_in: true }) })
      }
      if (url.includes("/api/account/status")) {
        return ok(accountStatus(optedIn))
      }
      return ok({})
    }) as unknown as typeof fetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("offers a free trial that, once started, unlocks the app", async () => {
    render(
      <ApiKeysGate enabled>
        <div>PROTECTED APP</div>
      </ApiKeysGate>,
    )

    const trialButton = await screen.findByRole("button", { name: /start free trial/i })
    expect(screen.getByText(/configure your api keys/i)).toBeInTheDocument()
    expect(screen.queryByText("PROTECTED APP")).not.toBeInTheDocument()

    fireEvent.click(trialButton)

    expect(await screen.findByText("PROTECTED APP")).toBeInTheDocument()
  })
})
