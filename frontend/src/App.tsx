import { SignInButton, SignOutButton, useAuth } from "@clerk/react"
import { useCallback, useEffect, useRef, useState } from "react"

import { ApiKeysGate } from "@/app/auth/api-keys-gate"
import { AppSidebar } from "@/app/chrome"
import { setAuthTokenProvider } from "@/app/core"
import { useAppController } from "@/app/hooks/app/use-app-controller"
import { SectionContent } from "@/app/layout/section-content"
import { GeneratedExampleDialog } from "@/app/sections/sentencebank/generated-example-dialog"
import { Button } from "@/components/ui/button"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Spinner } from "@/components/ui/spinner"

type AppProps = {
  requiresAuth?: boolean
}

type TokenState =
  | { status: "loading"; slow: boolean }
  | { status: "ready" }
  | { status: "error"; message: string }

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function getTokenWithTimeout(
  getToken: () => Promise<string | null>,
  timeoutMs: number,
): Promise<string | null> {
  let timeoutId = 0
  const timeout = new Promise<null>((resolve) => {
    timeoutId = window.setTimeout(() => resolve(null), timeoutMs)
  })
  try {
    return await Promise.race([getToken(), timeout])
  } finally {
    window.clearTimeout(timeoutId)
  }
}

function sameTokenState(a: TokenState, b: TokenState): boolean {
  if (a.status !== b.status) {
    return false
  }
  if (a.status === "loading" && b.status === "loading") {
    return a.slow === b.slow
  }
  if (a.status === "error" && b.status === "error") {
    return a.message === b.message
  }
  return true
}

function AuthenticatedApp() {
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const [tokenState, setTokenStateRaw] = useState<TokenState>({ status: "loading", slow: false })
  const [tokenRetryKey, setTokenRetryKey] = useState(0)
  const tokenWaitStartRef = useRef<number | null>(null)
  const lastRetryKeyRef = useRef(tokenRetryKey)

  const setTokenState = useCallback((next: TokenState) => {
    setTokenStateRaw((prev) => (sameTokenState(prev, next) ? prev : next))
  }, [])

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setAuthTokenProvider(null)
      tokenWaitStartRef.current = null
      const resetId = window.setTimeout(() => {
        setTokenState({ status: "loading", slow: false })
      }, 0)
      return () => window.clearTimeout(resetId)
    }

    if (lastRetryKeyRef.current !== tokenRetryKey) {
      lastRetryKeyRef.current = tokenRetryKey
      tokenWaitStartRef.current = null
    }
    if (tokenWaitStartRef.current === null) {
      tokenWaitStartRef.current = Date.now()
    }

    let cancelled = false
    const elapsed = Date.now() - tokenWaitStartRef.current
    const slowId = window.setTimeout(() => {
      if (!cancelled) {
        setTokenState({ status: "loading", slow: true })
      }
    }, Math.max(0, 2500 - elapsed))
    const errorId = window.setTimeout(() => {
      if (!cancelled) {
        setAuthTokenProvider(null)
        setTokenState({
          status: "error",
          message: "danote could not get a sign-in token from Clerk.",
        })
      }
    }, Math.max(0, 8000 - elapsed))

    async function waitForToken() {
      for (let attempt = 0; attempt < 10; attempt += 1) {
        try {
          const token = await getTokenWithTimeout(getToken, 1000)
          if (cancelled) {
            return
          }
          if (token) {
            window.clearTimeout(slowId)
            window.clearTimeout(errorId)
            setAuthTokenProvider(() => getToken())
            setTokenState({ status: "ready" })
            return
          }
        } catch {
          if (!cancelled) {
            window.clearTimeout(slowId)
            window.clearTimeout(errorId)
            setAuthTokenProvider(null)
            setTokenState({
              status: "error",
              message: "Clerk returned an error while preparing your sign-in session.",
            })
          }
          return
        }
        await wait(250)
      }
      if (!cancelled) {
        window.clearTimeout(slowId)
        window.clearTimeout(errorId)
        setAuthTokenProvider(null)
        setTokenState({
          status: "error",
          message: "danote could not get a sign-in token from Clerk.",
        })
      }
    }

    void waitForToken()

    return () => {
      cancelled = true
      window.clearTimeout(slowId)
      window.clearTimeout(errorId)
      setAuthTokenProvider(null)
    }
  }, [getToken, isLoaded, isSignedIn, tokenRetryKey, setTokenState])

  if (!isLoaded) {
    return null
  }

  if (!isSignedIn) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-semibold tracking-normal">danote</h1>
          <p className="text-sm text-muted-foreground">Sign in to use your Danish notes workspace.</p>
          <SignInButton mode="modal">
            <button className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-xs transition-colors hover:bg-primary/90">
              Sign in
            </button>
          </SignInButton>
        </div>
      </main>
    )
  }

  if (tokenState.status === "loading") {
    return (
      <SessionLoadingScreen
        slow={tokenState.slow}
        onRetry={() => {
          setTokenState({ status: "loading", slow: false })
          setTokenRetryKey((current) => current + 1)
        }}
      />
    )
  }

  if (tokenState.status === "error") {
    return (
      <SessionRecoveryScreen
        message={tokenState.message}
        onRetry={() => {
          setTokenState({ status: "loading", slow: false })
          setTokenRetryKey((current) => current + 1)
        }}
      />
    )
  }

  return (
    <ApiKeysGate enabled>
      <AppShell />
    </ApiKeysGate>
  )
}

function SessionLoadingScreen({ slow, onRetry }: { slow: boolean; onRetry: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
        <Spinner />
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-normal">Finishing sign in</h1>
          <p className="text-sm text-muted-foreground">
            {slow ? "This is taking longer than expected." : "Waiting for Clerk to prepare your session."}
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button type="button" variant="outline" onClick={onRetry}>
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

function SessionRecoveryScreen({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-normal">Session unavailable</h1>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button type="button" variant="outline" onClick={onRetry}>
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

function AppShell() {
  const {
    activeSection,
    status,
    lemmas,
    sentences,
    wordbankRefreshTick,
    searchTranslationConfigVersion,
    unreadWordbankNotificationCount,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    selectAccount,
    openWordbankLemma,
    openWordbankLemmaRaw,
    openWordbankMeaning,
    openSentence,
    addSentenceToSentencebank,
    addWordFromSearch,
    sectionProps,
    generatedExamplePreview,
    isGeneratingExample,
    isSavingGeneratedExample,
    saveGeneratedExample,
    regenerateExample,
    discardGeneratedExample,
  } = useAppController()

  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        sentences={sentences}
        wordbankCacheVersion={wordbankRefreshTick}
        searchTranslationConfigVersion={searchTranslationConfigVersion}
        unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        onSelectWordbank={selectWordbank}
        onSelectSentencebank={selectSentencebank}
        onSelectDeveloper={selectDeveloper}
        onSelectAccount={selectAccount}
        onOpenWordbankLemma={openWordbankLemma}
        onOpenWordbankLemmaRaw={openWordbankLemmaRaw}
        onOpenWordbankMeaning={openWordbankMeaning}
        onOpenSentence={openSentence}
        onAddSentenceToSentencebank={addSentenceToSentencebank}
        onAddWordFromSearch={addWordFromSearch}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger className="size-10 [&_svg:not([class*='size-'])]:size-5" />
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col px-[var(--danote-shell-gutter-x)] pt-[var(--danote-shell-gutter-y)] pb-[var(--danote-shell-gutter-y-compact)]">
          <span className="sr-only" aria-label="backend-connection-status">{status}</span>
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
            <SectionContent
              activeSection={activeSection}
              wordbankProps={sectionProps.wordbankSectionProps}
              sentencebankProps={sectionProps.sentencebankSectionProps}
              developerProps={sectionProps.developerSectionProps}
            />
            <GeneratedExampleDialog
              preview={generatedExamplePreview}
              isSaving={isSavingGeneratedExample}
              isRegenerating={isGeneratingExample}
              onSave={() => {
                void saveGeneratedExample()
              }}
              onRegenerate={() => {
                void regenerateExample()
              }}
              onDiscard={discardGeneratedExample}
            />
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

function App({ requiresAuth = false }: AppProps) {
  if (requiresAuth) {
    return <AuthenticatedApp />
  }
  return <AppShell />
}

export default App
