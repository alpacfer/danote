import { UserButton, useUser } from "@clerk/react"

import { ApiKeysForm } from "@/app/auth/api-keys-form"
import { useAccountStatus } from "@/app/auth/use-account-status"
import { CLERK_PUBLISHABLE_KEY } from "@/app/core"
import { Spinner } from "@/components/ui/spinner"

const IS_CLERK_CONFIGURED = Boolean(CLERK_PUBLISHABLE_KEY)

export function AccountSection() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 py-8">
      {IS_CLERK_CONFIGURED ? <ClerkProfileHeader /> : <LocalDevHeader />}
      <ApiKeysCard />
      {IS_CLERK_CONFIGURED ? <ClerkProfileFooter /> : null}
    </div>
  )
}

function ClerkProfileHeader() {
  // Only safe to call when wrapped in <ClerkProvider> at the app root.
  const { user, isLoaded } = useUser()
  const email = isLoaded ? user?.primaryEmailAddress?.emailAddress ?? null : null
  return (
    <section className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Account</h1>
        <p className="text-sm text-muted-foreground">{email ?? "Signed-in user"}</p>
      </div>
      <UserButton />
    </section>
  )
}

function LocalDevHeader() {
  return (
    <section className="flex flex-col gap-1">
      <h1 className="text-2xl font-semibold">Account</h1>
      <p className="text-sm text-muted-foreground">
        Local dev mode — sign-in is disabled. Set <code className="rounded bg-muted px-1">VITE_CLERK_PUBLISHABLE_KEY</code>{" "}
        in <code className="rounded bg-muted px-1">.env.local</code> to enable real accounts.
      </p>
    </section>
  )
}

function ClerkProfileFooter() {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-medium">Profile &amp; password</h2>
      <p className="text-sm text-muted-foreground">
        Use the user menu in the top right to change your password, manage
        connected accounts, or sign out.
      </p>
    </section>
  )
}

function ApiKeysCard() {
  const { state, refetch } = useAccountStatus(true)

  return (
    <section className="flex flex-col gap-3">
      <header className="flex flex-col gap-1">
        <h2 className="text-lg font-medium">API keys</h2>
        <p className="text-sm text-muted-foreground">
          Each request to the language services uses these keys. They are encrypted at rest.
        </p>
      </header>
      {state.status === "loading" || state.status === "idle" ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : state.status === "error" ? (
        <ApiKeysErrorBanner message={state.message} />
      ) : (
        <ApiKeysForm status={state.data} onChange={refetch} />
      )}
    </section>
  )
}

function ApiKeysErrorBanner({ message }: { message: string }) {
  const looksLikeEncryptionMissing =
    message.includes("503") || message.toLowerCase().includes("not_initialized")
  return (
    <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm text-destructive">
      {looksLikeEncryptionMissing ? (
        <>
          API key storage is not initialized. Set{" "}
          <code className="rounded bg-muted px-1 text-foreground">DANOTE_KEY_ENCRYPTION_SECRET</code>{" "}
          in <code className="rounded bg-muted px-1 text-foreground">.env.local</code> (generate
          one with <code className="rounded bg-muted px-1 text-foreground">openssl rand -base64 32</code>)
          and restart the backend.
        </>
      ) : (
        message
      )}
    </div>
  )
}
