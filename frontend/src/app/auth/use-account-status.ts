import { useCallback, useEffect, useState } from "react"

import { fetchAccountStatus, type AccountStatus } from "@/app/auth/account-api"

export type AccountStatusState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: AccountStatus }
  | { status: "error"; message: string }

export function useAccountStatus(enabled: boolean) {
  const [state, setState] = useState<AccountStatusState>({ status: "idle" })

  const refetch = useCallback(async () => {
    setState({ status: "loading" })
    try {
      const data = await fetchAccountStatus()
      setState({ status: "ready", data })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load account status."
      setState({ status: "error", message })
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      return
    }

    let cancelled = false

    async function loadStatus() {
      try {
        const data = await fetchAccountStatus()
        if (!cancelled) {
          setState({ status: "ready", data })
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Could not load account status."
          setState({ status: "error", message })
        }
      }
    }

    void loadStatus()

    return () => {
      cancelled = true
    }
  }, [enabled])

  const visibleState: AccountStatusState = !enabled
    ? { status: "idle" }
    : state.status === "idle"
      ? { status: "loading" }
      : state

  return { state: visibleState, refetch }
}
