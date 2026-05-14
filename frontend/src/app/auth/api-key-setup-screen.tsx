import { ApiKeysForm } from "@/app/auth/api-keys-form"
import type { AccountStatus } from "@/app/auth/account-api"

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
    </div>
  )
}
