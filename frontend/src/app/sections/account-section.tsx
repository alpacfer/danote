import { UserButton, useUser } from "@clerk/react"
import { useEffect, useState } from "react"

import { ApiKeysForm } from "@/app/auth/api-keys-form"
import { fetchAccountMe, type AccountMe } from "@/app/auth/account-api"
import { GuestProfileCard, GuestUsageCard } from "@/app/auth/guest-account-cards"
import { useAccountStatus } from "@/app/auth/use-account-status"
import { CLERK_PUBLISHABLE_KEY } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"

const IS_CLERK_CONFIGURED = Boolean(CLERK_PUBLISHABLE_KEY)

export function AccountSection() {
  const [account, setAccount] = useState<AccountMe | null>(null)

  useEffect(() => {
    let cancelled = false
    void fetchAccountMe()
      .then((next) => {
        if (!cancelled) {
          setAccount(next)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAccount(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const isGuest = account?.auth_provider === "guest"

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Account</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Manage your profile and the language-service keys danote uses for translations,
          verification, and pronunciation.
        </p>
      </header>
      {isGuest ? <GuestProfileCard /> : IS_CLERK_CONFIGURED ? <ClerkProfileCard /> : <LocalDevCard />}
      {isGuest ? <GuestUsageCard /> : <ApiKeysCard />}
    </div>
  )
}

function ClerkProfileCard() {
  // Only safe to call when wrapped in <ClerkProvider> at the app root.
  const { user, isLoaded } = useUser()
  const email = isLoaded ? user?.primaryEmailAddress?.emailAddress ?? null : null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>
          Your signed-in identity and account menu.
        </CardDescription>
        <CardAction>
          <UserButton />
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Separator />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium">Signed in as</span>
            <span className="text-sm text-muted-foreground">{email ?? "Signed-in user"}</span>
          </div>
          <Badge variant="secondary">Active</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Use the profile menu to change your password, manage connected accounts, or sign out.
        </p>
      </CardContent>
    </Card>
  )
}

function LocalDevCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>
          Sign-in is disabled while the app runs without Clerk configuration.
        </CardDescription>
        <CardAction>
          <Badge variant="outline">Local dev</Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Separator />
        <p className="text-sm text-muted-foreground">
          Set <code className="rounded bg-muted px-1 text-foreground">VITE_CLERK_PUBLISHABLE_KEY</code>{" "}
          in <code className="rounded bg-muted px-1 text-foreground">.env.local</code> to enable real accounts.
        </p>
      </CardContent>
    </Card>
  )
}

function ApiKeysCard() {
  const { state, refetch } = useAccountStatus(true)

  return (
    <Card>
      <CardHeader>
        <CardTitle>API keys</CardTitle>
        <CardDescription>
          Each request to the language services uses your own keys. They are encrypted at rest.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Separator />
        {state.status === "loading" || state.status === "idle" ? (
          <ApiKeysLoadingState />
        ) : state.status === "error" ? (
          <ApiKeysErrorBanner message={state.message} />
        ) : (
          <ApiKeysForm status={state.data} onChange={refetch} />
        )}
      </CardContent>
    </Card>
  )
}


function ApiKeysLoadingState() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-center py-2">
        <Spinner />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 rounded-lg" />
        ))}
      </div>
    </div>
  )
}

function ApiKeysErrorBanner({ message }: { message: string }) {
  const looksLikeEncryptionMissing =
    message.includes("503") || message.toLowerCase().includes("not_initialized")
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
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
