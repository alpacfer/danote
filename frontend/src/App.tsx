import { AppBreadcrumb, AppSidebar } from "@/app/chrome"
import { useAppController } from "@/app/hooks/app/use-app-controller"
import { SectionContent } from "@/app/layout/section-content"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

function App() {
  const {
    activeSection,
    selectedLemma,
    status,
    lemmas,
    wordbankRefreshTick,
    searchTranslationConfigVersion,
    unreadWordbankNotificationCount,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    openWordbankLemma,
    openWordbankMeaning,
    openWordbankRoot,
    addSentenceToSentencebank,
    addWordFromSearch,
    sectionProps,
  } = useAppController()

  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        wordbankCacheVersion={wordbankRefreshTick}
        searchTranslationConfigVersion={searchTranslationConfigVersion}
        unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        onSelectWordbank={selectWordbank}
        onSelectSentencebank={selectSentencebank}
        onSelectDeveloper={selectDeveloper}
        onOpenWordbankLemma={openWordbankLemma}
        onOpenWordbankMeaning={openWordbankMeaning}
        onAddSentenceToSentencebank={addSentenceToSentencebank}
        onAddWordFromSearch={addWordFromSearch}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger />
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col px-[var(--danote-shell-gutter-x)] pt-[var(--danote-shell-gutter-y)] pb-[var(--danote-shell-gutter-y-compact)]">
          <span className="sr-only" aria-label="backend-connection-status">{status}</span>
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
            <div className="mb-[var(--danote-shell-stack-gap)] flex items-center justify-between gap-3">
              <AppBreadcrumb
                activeSection={activeSection}
                selectedLemma={selectedLemma}
                onSelectWordbank={openWordbankRoot}
              />
            </div>
            <SectionContent
              activeSection={activeSection}
              wordbankProps={sectionProps.wordbankSectionProps}
              sentencebankProps={sectionProps.sentencebankSectionProps}
              developerProps={sectionProps.developerSectionProps}
            />
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
