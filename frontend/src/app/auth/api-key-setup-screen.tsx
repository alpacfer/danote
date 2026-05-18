import { useState } from "react"
import { toast } from "sonner"

import { ApiKeysForm } from "@/app/auth/api-keys-form"
import { optInTrial, type AccountStatus } from "@/app/auth/account-api"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"

export type ApiKeySetupScreenProps = {
  status: AccountStatus
  onChange: () => Promise<void> | void
}

export function ApiKeySetupScreen({ status, onChange }: ApiKeySetupScreenProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-12">
      <header className="flex flex-col gap-2 text-center">
        <h1 className="text-2xl font-semibold">Configure your API keys</h1>
        <p className="text-sm text-muted-foreground">
          danote uses your own API keys to translate, verify, and pronounce Danish words.
          Save all four to start.
        </p>
      </header>
      <ApiKeysForm status={status} onChange={onChange} />
      <p className="text-xs text-muted-foreground text-center">
        Keys are encrypted at rest with AES-GCM and only decrypted in memory at request time.
      </p>
      {status.trial.enabled ? (
        <>
          <Separator />
          <TrialCta status={status} onChange={onChange} />
        </>
      ) : null}
    </div>
  )
}

function TrialCta({ status, onChange }: ApiKeySetupScreenProps) {
  const [isStarting, setIsStarting] = useState(false)

  async function handleStartTrial() {
    setIsStarting(true)
    try {
      await optInTrial()
      await onChange()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start the free trial.")
      setIsStarting(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-medium">Not ready to add keys?</h2>
        <p className="text-sm text-muted-foreground">
          Try danote on us with up to {status.trial.limit} word searches per day.
          You can add your own keys anytime from the Account page for unlimited use.
        </p>
      </div>
      <Button
        type="button"
        variant="outline"
        disabled={!status.trial.available || isStarting}
        onClick={() => void handleStartTrial()}
      >
        {isStarting ? <Spinner /> : null}
        Start free trial — {status.trial.limit} searches/day
      </Button>
      {!status.trial.available ? (
        <p className="text-xs text-muted-foreground">
          The free trial is unavailable on this deployment. Add your own API keys to continue.
        </p>
      ) : null}
    </div>
  )
}
