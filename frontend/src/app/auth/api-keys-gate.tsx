import { SignOutButton } from "@clerk/react"
import { useCallback, type ReactNode } from "react"

import { ApiKeySetupScreen } from "@/app/auth/api-key-setup-screen"
import { useAccountStatus } from "@/app/auth/use-account-status"
import { Button } from "@/components/ui/button"
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
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-semibold tracking-normal">Account setup needs attention</h1>
            <p className="text-sm text-muted-foreground">{state.message}</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button type="button" variant="outline" onClick={() => void refetch()}>
              Retry
            </Button>
            <SignOutButton>
              <Button type="button">Sign out</Button>
            </SignOutButton>
          </div>
        </div>
      </main>
    )
  }
  const trialActive = state.data.trial.opted_in && !state.data.trial.keys_configured
  if (!state.data.keys_configured && !trialActive) {
    return <ApiKeySetupScreen status={state.data} onChange={handleChanged} />
  }
  return <>{children}</>
}
