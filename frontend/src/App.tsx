import { SignInButton, UserButton, useAuth } from "@clerk/react"
import { useEffect } from "react"

import { ApiKeysGate } from "@/app/auth/api-keys-gate"
import { AppSidebar } from "@/app/chrome"
import { setAuthTokenProvider } from "@/app/core"
import { useAppController } from "@/app/hooks/app/use-app-controller"
import { SectionContent } from "@/app/layout/section-content"
import { GeneratedExampleDialog } from "@/app/sections/sentencebank/generated-example-dialog"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

type AppProps = {
  requiresAuth?: boolean
}

function AuthenticatedApp() {
  const { getToken, isLoaded, isSignedIn } = useAuth()

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setAuthTokenProvider(null)
      return
    }
    setAuthTokenProvider(() => getToken())
    return () => {
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
