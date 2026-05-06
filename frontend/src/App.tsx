import { AppSidebar } from "@/app/chrome"
import { useAppController } from "@/app/hooks/app/use-app-controller"
import { SectionContent } from "@/app/layout/section-content"
import { GeneratedExampleDialog } from "@/app/sections/sentencebank/generated-example-dialog"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

function App() {
  const {
    activeSection,
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

export default App
