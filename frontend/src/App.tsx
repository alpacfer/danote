import { SignInButton, SignOutButton, UserButton, useAuth } from "@clerk/react"
import { useEffect, useState } from "react"

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

function AuthenticatedApp() {
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const [tokenState, setTokenState] = useState<"loading" | "ready" | "error">("loading")

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setAuthTokenProvider(null)
      return
    }

    let cancelled = false
    const loadingStateId = window.setTimeout(() => {
      if (!cancelled) {
        setTokenState("loading")
      }
    }, 0)

    async function waitForToken() {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        try {
          const token = await getToken()
          if (cancelled) {
            return
          }
          if (token) {
            setAuthTokenProvider(() => getToken())
            setTokenState("ready")
            return
          }
        } catch {
          if (!cancelled) {
            setTokenState("error")
          }
          return
        }
        await new Promise((resolve) => window.setTimeout(resolve, 150))
      }
      if (!cancelled) {
        setAuthTokenProvider(null)
        setTokenState("error")
      }
    }

    void waitForToken()

    return () => {
      cancelled = true
      window.clearTimeout(loadingStateId)
      setAuthTokenProvider(null)
    }
  }, [getToken, isLoaded, isSignedIn])

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

  if (tokenState === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (tokenState === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="flex w-full max-w-sm flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-semibold tracking-normal">Session unavailable</h1>
          <p className="text-sm text-muted-foreground">danote could not get a sign-in token from Clerk.</p>
          <SignOutButton>
            <Button type="button">Sign out</Button>
          </SignOutButton>
        </div>
      </main>
    )
  }

  return (
    <ApiKeysGate enabled>
      <AppShell showUserButton />
    </ApiKeysGate>
  )
}

function AppShell({ showUserButton = false }: { showUserButton?: boolean }) {
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
          <SidebarTrigger />
          {showUserButton ? <div className="ml-auto"><UserButton /></div> : null}
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
