import { AppBreadcrumb, AppSidebar } from "@/app/chrome"
import { useAppController } from "@/app/hooks/app/use-app-controller"
import { SectionContent } from "@/app/layout/section-content"
import { PlaygroundHeaderActions } from "@/app/sections"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

function App() {
  const {
    activeSection,
    selectedLemma,
    status,
    lemmas,
    savedNotes,
    wordbankRefreshTick,
    searchTranslationConfigVersion,
    activeSavedNote,
    isVerifyingWords,
    notifications,
    isNotificationsOpen,
    setIsNotificationsOpen,
    hasUnreadNotifications,
    unreadNotifications,
    unreadWordbankNotificationCount,
    selectPlayground,
    selectNotes,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    openWordbankLemma,
    openWordbankMeaning,
    openWordbankRoot,
    openSavedNoteById,
    addSentenceToSentencebank,
    addWordFromSearch,
    openSaveDialog,
    sectionProps,
  } = useAppController()

  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        wordbankCacheVersion={wordbankRefreshTick}
        searchTranslationConfigVersion={searchTranslationConfigVersion}
        savedNotes={savedNotes}
        unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        onSelectPlayground={selectPlayground}
        onSelectNotes={selectNotes}
        onSelectWordbank={selectWordbank}
        onSelectSentencebank={selectSentencebank}
        onSelectDeveloper={selectDeveloper}
        onOpenWordbankLemma={openWordbankLemma}
        onOpenWordbankMeaning={openWordbankMeaning}
        onOpenSavedNote={openSavedNoteById}
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
                activeNoteName={activeSavedNote?.name ?? null}
                onSelectWordbank={openWordbankRoot}
              />
              {activeSection === "playground" ? (
                <PlaygroundHeaderActions
                  autosaveStatusLabel={sectionProps.autosaveStatusLabel}
                  hasActiveSavedNote={Boolean(activeSavedNote)}
                  isNotificationsOpen={isNotificationsOpen}
                  isVerifyingWords={isVerifyingWords}
                  hasUnreadNotifications={hasUnreadNotifications}
                  unreadCount={unreadNotifications.length}
                  notifications={notifications}
                  onOpenSaveDialog={openSaveDialog}
                  onNotificationsOpenChange={(open) => {
                    setIsNotificationsOpen(open)
                  }}
                />
              ) : null}
            </div>
            <SectionContent
              activeSection={activeSection}
              playgroundProps={sectionProps.playgroundSectionProps}
              notesProps={sectionProps.notesSectionProps}
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
