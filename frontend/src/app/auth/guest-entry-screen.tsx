import { AuthSignInButton } from "@/app/auth/auth-sign-in-button"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"

export type GuestEntryScreenProps = {
  error: string | null
  isStartingGuest: boolean
  onStartGuest: () => void
}

export function GuestEntryScreen({ error, isStartingGuest, onStartGuest }: GuestEntryScreenProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
        <h1 className="text-2xl font-semibold tracking-normal">danote</h1>
        <p className="text-sm text-muted-foreground">Sign in to use your Danish notes workspace.</p>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <div className="flex flex-wrap justify-center gap-2">
          <AuthSignInButton>
            <Button type="button">Sign in</Button>
          </AuthSignInButton>
          <Button type="button" variant="outline" disabled={isStartingGuest} onClick={onStartGuest}>
            {isStartingGuest ? <Spinner /> : null}
            Continue as guest
          </Button>
        </div>
      </div>
    </main>
  )
}
