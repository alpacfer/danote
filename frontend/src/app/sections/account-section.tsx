import { UserButton, useUser } from "@clerk/react"
import { useEffect, useState } from "react"
import { Trash2 } from "lucide-react"
import { toast } from "sonner"
import { useTheme } from "next-themes"

import { cn } from "@/lib/utils"
import { ApiKeysForm } from "@/app/auth/api-keys-form"
import { deleteAccountLearningData, fetchAccountMe, type AccountMe } from "@/app/auth/account-api"
import { GuestProfileCard, GuestUsageCard } from "@/app/auth/guest-account-cards"
import { useAccountStatus } from "@/app/auth/use-account-status"
import { CLERK_PUBLISHABLE_KEY } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"

const IS_CLERK_CONFIGURED = Boolean(CLERK_PUBLISHABLE_KEY)

export function AccountSection({ onFreshStart }: { onFreshStart?: () => void }) {
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
        <h1 className="font-section-title text-2xl leading-none font-semibold">Account</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Manage your profile and the language-service keys danote uses for translations,
          verification, and pronunciation.
        </p>
      </header>
      {isGuest ? <GuestProfileCard /> : IS_CLERK_CONFIGURED ? <ClerkProfileCard /> : <LocalDevCard />}
      <ThemeSelectorCard />
      <FreshStartCard onFreshStart={onFreshStart} />
      {isGuest ? <GuestUsageCard /> : <ApiKeysCard />}
    </div>
  )
}

function ThemeSelectorCard() {
  const { theme, setTheme } = useTheme()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Theme</CardTitle>
        <CardDescription>
          Customize the appearance of danote on your device.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Separator />
        <div className="grid grid-cols-2 gap-4">
          {/* Light Theme Button */}
          <button
            type="button"
            onClick={() => setTheme("light")}
            className={cn(
              "flex flex-col items-center gap-3 rounded-xl border-2 p-3 text-left transition-all hover:bg-accent/40 active:scale-[0.98]",
              theme === "light"
                ? "border-primary bg-accent/30 shadow-sm"
                : "border-muted bg-card hover:border-muted-foreground/30"
            )}
          >
            <div className="flex h-20 w-full flex-col gap-1.5 rounded-lg border border-border bg-slate-50 p-2 select-none">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <div className="size-2 rounded-full bg-slate-300" />
                  <div className="h-1.5 w-8 rounded-full bg-slate-200" />
                </div>
                <div className="size-2 rounded-full bg-slate-300" />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <div className="h-2 w-full rounded-sm bg-slate-200" />
                <div className="h-2 w-3/4 rounded-sm bg-slate-200" />
              </div>
              <div className="mx-auto h-3 w-16 rounded-full border border-slate-200 bg-white" />
            </div>
            <span className="text-xs font-semibold text-foreground">Light</span>
          </button>

          {/* Dark Theme Button */}
          <button
            type="button"
            onClick={() => setTheme("dark")}
            className={cn(
              "flex flex-col items-center gap-3 rounded-xl border-2 p-3 text-left transition-all hover:bg-accent/40 active:scale-[0.98]",
              theme === "dark"
                ? "border-primary bg-accent/30 shadow-sm"
                : "border-muted bg-card hover:border-muted-foreground/30"
            )}
          >
            <div className="flex h-20 w-full flex-col gap-1.5 rounded-lg border border-zinc-800 bg-zinc-950 p-2 select-none">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <div className="size-2 rounded-full bg-zinc-700" />
                  <div className="h-1.5 w-8 rounded-full bg-zinc-800" />
                </div>
                <div className="size-2 rounded-full bg-zinc-700" />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <div className="h-2 w-full rounded-sm bg-zinc-800" />
                <div className="h-2 w-3/4 rounded-sm bg-zinc-800" />
              </div>
              <div className="mx-auto h-3 w-16 rounded-full border border-zinc-800 bg-zinc-900" />
            </div>
            <span className="text-xs font-semibold text-foreground">Dark</span>
          </button>
        </div>
      </CardContent>
    </Card>
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

function FreshStartCard({ onFreshStart }: { onFreshStart?: () => void }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleFreshStart() {
    setBusy(true)
    try {
      const payload = await deleteAccountLearningData()
      toast.success(payload.message)
      onFreshStart?.()
      setOpen(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete saved words and sentences.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Start fresh</CardTitle>
        <CardDescription>
          Delete your saved words, sentences, and custom categories while keeping your account and service credentials.
        </CardDescription>
        <CardAction>
          <Button type="button" variant="destructive" size="sm" onClick={() => setOpen(true)}>
            <Trash2 data-icon="inline-start" />
            Delete data
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Separator />
        <p className="text-sm text-muted-foreground">
          This clears wordbank entries, sentencebank entries, custom categories, related generated cache, and pending word jobs for this account only.
        </p>
      </CardContent>
      <Dialog open={open} onOpenChange={(nextOpen) => {
        if (!busy) setOpen(nextOpen)
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete all words and sentences?</DialogTitle>
            <DialogDescription>
              This gives your account a clean slate with the standard categories. Service credentials, sign-in, and trial status are not changed.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
            Saved wordbank entries, sentencebank entries, custom categories, generated word jobs, and related word cache will be permanently deleted.
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={busy}>Cancel</Button>
            </DialogClose>
            <Button type="button" variant="destructive" disabled={busy} onClick={() => void handleFreshStart()}>
              <Trash2 data-icon="inline-start" />
              {busy ? "Deleting..." : "Delete all words and sentences"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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
