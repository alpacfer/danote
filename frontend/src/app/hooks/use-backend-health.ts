import { useEffect, useState } from "react"

import {
  type ConnectionStatus,
  type HealthPayload,
} from "@/app/core"

type UseBackendHealthParams = {
  backendUrl: string
}

export function useBackendHealth({ backendUrl }: UseBackendHealthParams) {
  const [status, setStatus] = useState<ConnectionStatus>("loading")
  const [healthPayload, setHealthPayload] = useState<HealthPayload | null>(null)

  useEffect(() => {
    let cancelled = false

    async function checkHealth() {
      try {
        const response = await fetch(`${backendUrl}/api/health`)
        if (!cancelled && response.ok) {
          const payload = (await response.json()) as HealthPayload
          setHealthPayload(payload)
          if (payload.status === "ok") {
            setStatus("connected")
            return
          }
          if (payload.status === "degraded") {
            setStatus("degraded")
            return
          }
          setStatus("offline")
          setHealthPayload(null)
          return
        }
      } catch {
        // ignore and set offline below
      }

      if (!cancelled) {
        setStatus("offline")
        setHealthPayload(null)
      }
    }

    checkHealth()

    return () => {
      cancelled = true
    }
  }, [backendUrl])

  return {
    status,
    setStatus,
    healthPayload,
    setHealthPayload,
  }
}
