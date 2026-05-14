import { useCallback, type ReactNode } from "react"

import { ApiKeySetupScreen } from "@/app/auth/api-key-setup-screen"
import { useAccountStatus } from "@/app/auth/use-account-status"
import { Spinner } from "@/components/ui/spinner"

export type ApiKeysGateProps = {
  enabled: boolean
  children: ReactNode
}

/**
 * Blocks the children until the signed-in user has saved all four API
 * keys (Gemini, DeepL, Azure Translation, Azure TTS). Render this inside
 * a signed-in branch; it assumes the caller has already verified auth.
 *
 * When `enabled` is false (e.g. local dev with auth disabled), the gate
 * is transparent and just renders children.
 */
export function ApiKeysGate({ enabled, children }: ApiKeysGateProps) {
  const { state, refetch } = useAccountStatus(enabled)
  const handleChanged = useCallback(async () => {
    await refetch()
  }, [refetch])

  if (!enabled) {
    return <>{children}</>
  }

  if (state.status === "idle" || state.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }
  if (state.status === "error") {
    return (
      <div className="mx-auto max-w-md py-16 text-center text-sm text-muted-foreground">
        {state.message}
      </div>
    )
  }
  if (!state.data.keys_configured) {
    return <ApiKeySetupScreen status={state.data} onChange={handleChanged} />
  }
  return <>{children}</>
}
