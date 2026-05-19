import { SignInButton } from "@clerk/react"

import { useAccountStatus } from "@/app/auth/use-account-status"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"

export function GuestProfileCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>
          You are using a fresh guest workspace for this browser session.
        </CardDescription>
        <CardAction>
          <Badge variant="secondary">Guest mode</Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Separator />
        <p className="text-sm text-muted-foreground">
          Guest notes are session-scoped and are not restored when you start guest mode again.
        </p>
        <div className="flex flex-wrap gap-2">
          <SignInButton mode="modal">
            <Button type="button" size="sm">Sign in to save notes</Button>
          </SignInButton>
        </div>
      </CardContent>
    </Card>
  )
}

export function GuestUsageCard() {
  const { state, refetch } = useAccountStatus(true)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Guest usage</CardTitle>
        <CardDescription>
          Guest searches use danote's hosted language-service keys.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <Separator />
        {state.status === "loading" || state.status === "idle" ? (
          <GuestUsageLoadingState />
        ) : state.status === "error" ? (
          <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
            {state.message}
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium">
                {state.data.trial.remaining} of {state.data.trial.limit} searches remaining today
              </span>
              <span className="text-sm text-muted-foreground">
                Your guest quota resets on {state.data.trial.resets_on}.
              </span>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={() => void refetch()}>
              Refresh
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function GuestUsageLoadingState() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-center py-2">
        <Spinner />
      </div>
      <Skeleton className="h-16 rounded-lg" />
    </div>
  )
}
