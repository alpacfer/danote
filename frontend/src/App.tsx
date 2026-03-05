import { useState } from "react"
import { AppBreadcrumb, AppSidebar } from "@/app/chrome"
import {
  useAnalysis,
  useApiStatusItems,
  useAppSectionProps,
  useBackendHealth,
  useDeveloperSettings,
  useDiscoveredTokenMetadata,
  useGroupedWordbankLemmas,
  useLexiconData,
  useNoteAutosave,
  useNotesPersistence,
  useNotificationCenter,
  usePlaygroundPopovers,
  useSectionNavigation,
  useSyncDiscoveredTokenMemory,
  useWordbankWorkflows,
  useNoteWorkspace,
} from "@/app/hooks"
import { SectionContent } from "@/app/layout/section-content"
import { PlaygroundHeaderActions } from "@/app/sections"
import { BACKEND_URL, type TokenFeedbackPayload } from "@/app/core"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { toast } from "sonner"
async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // Fall through to default message.
  }
  return fallback
}
function App() {
  const [noteText, setNoteText] = useState("")
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)
  const [sentencebankRefreshTick, setSentencebankRefreshTick] = useState(0)
  const {
    activeSection,
    selectedLemma,
    setActiveSection,
    setSelectedLemma,
    selectPlayground,
    selectNotes,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    openWordbankLemma,
    openWordbankRoot,
  } = useSectionNavigation()
  const { status, setStatus, healthPayload, setHealthPayload } = useBackendHealth({
    backendUrl: BACKEND_URL,
  })
  const {
    tokens,
    setTokens,
    analysisError,
    setAnalysisError,
    setAnalysisRefreshTick,
    noteHighlights,
  } = useAnalysis({
    noteText,
    backendUrl: BACKEND_URL,
    extractErrorMessage,
  })
  const { discoveredTokenMetadata, setDiscoveredTokenMetadata } = useDiscoveredTokenMetadata()
  const {
    savedNotes,
    setSavedNotes,
    setActiveNoteId,
    autosaveStatus,
    setAutosaveStatus,
    noteAutosaveTimeoutRef,
    activeSavedNote,
    activeSavedNoteId,
    activeSavedNoteName,
  } = useNotesPersistence()
  const {
    lemmas,
    setLemmas,
    sentences,
    setSentences,
    wordbankError,
    sentencebankError,
    isWordbankLoading,
    isSentencebankLoading,
    lemmaDetails,
    setLemmaDetails,
    lemmaDetailsError,
    setLemmaDetailsError,
    isLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton,
  } = useLexiconData({
    backendUrl: BACKEND_URL,
    extractErrorMessage,
    activeSection,
    selectedLemma,
    wordbankRefreshTick,
    sentencebankRefreshTick,
  })
  const {
    notifications,
    isNotificationsOpen,
    setIsNotificationsOpen,
    unreadNotifications,
    hasUnreadNotifications,
    pushNotification,
    markAllNotificationsAsRead,
  } = useNotificationCenter()
  const {
    highlightPopover,
    phrasePopover,
    generatedTranslationMap,
    setGeneratedTranslationMap,
    isGeneratingPhraseTranslation,
    generatePhraseTranslationError,
    generateTranslationError,
    popoverDisplayToken,
    popoverPrimaryAction,
    popoverTranslation,
    popoverLemmaText,
    showPopoverLemma,
    popoverMetadataBadges,
    popoverIsNoun,
    popoverIsVerbLike,
    showTranslationSkeleton,
    phraseTranslation,
    isSelectedPhraseSaved,
    clearTransientState: clearPlaygroundTransientState,
    closeHighlightPopover,
    handlePhrasePopoverOpenChange,
    handleHighlightPopoverOpenChange,
    openHighlightPopover,
    handleEditorSelection,
  } = usePlaygroundPopovers({
    backendUrl: BACKEND_URL,
    extractErrorMessage,
    tokens,
    discoveredTokenMetadata,
    sentences,
  })
  const {
    isSaveDialogOpen,
    saveDialogMode,
    noteNameDraft,
    duplicateNameConflictNoteId,
    openSaveDialog,
    handleSaveDialogOpenChange,
    handleNoteNameDraftChange,
    handleSaveDialogSubmit,
    resolveDuplicateNameConflict,
    openSavedNoteInPlayground,
    openSavedNoteById,
  } = useNoteWorkspace({
    noteText,
    tokens,
    discoveredTokenMetadata,
    generatedTranslationMap,
    savedNotes,
    setSavedNotes,
    activeSavedNote,
    setActiveNoteId,
    setAutosaveStatus,
    noteAutosaveTimeoutRef,
    setNoteText,
    setTokens,
    setDiscoveredTokenMetadata,
    setGeneratedTranslationMap,
    setAnalysisError,
    clearPlaygroundTransientState,
    setActiveSection,
    pushNotification,
  })
  async function postTokenFeedback(payload: TokenFeedbackPayload) {
    try {
      await fetch(`${BACKEND_URL}/api/tokens/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    } catch {
      // Feedback logging is best-effort in v1.
    }
  }
  const {
    addingTokens,
    isSavingSentence,
    pronunciationLoadingByForm,
    isRegeneratingLemmaPronunciation,
    isApplyingVerificationChanges,
    selectedLemmaVerificationError,
    hasSuggestedVerificationChanges,
    addTokenToWordbank,
    addWordFromSearch,
    addSentenceToSentencebank,
    playPronunciation,
    regenerateSelectedLemmaPronunciation,
    applySelectedLemmaVerificationChanges,
    clearVerificationErrors,
  } = useWordbankWorkflows({
    backendUrl: BACKEND_URL,
    extractErrorMessage,
    selectedLemma,
    lemmaDetails,
    sentences,
    setAnalysisRefreshTick,
    setWordbankRefreshTick,
    setSentencebankRefreshTick,
    setActiveSection,
    setSelectedLemma,
    postTokenFeedback,
    onSentenceSaved: () => {
      handlePhrasePopoverOpenChange(false)
    },
    pushNotification,
  })
  const groupedWordbankLemmas = useGroupedWordbankLemmas(lemmas)
  const apiStatusItems = useApiStatusItems(healthPayload, status)
  const developerSettings = useDeveloperSettings({
    backendUrl: BACKEND_URL,
    extractErrorMessage,
    setStatus,
    setHealthPayload,
    onNotifySuccess: (message) => {
      toast.success(message)
    },
    onNotifyError: (message) => {
      toast.error(message)
    },
    onDatabaseReset: () => {
      setNoteText("")
      setTokens([])
      setAnalysisError(null)
      setSelectedLemma(null)
      setLemmas([])
      setSentences([])
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      clearVerificationErrors()
      setWordbankRefreshTick((current) => current + 1)
      setSentencebankRefreshTick((current) => current + 1)
    },
  })
  useNoteAutosave({
    activeSavedNoteId,
    activeSavedNoteName,
    noteText,
    tokens,
    discoveredTokenMetadata,
    generatedTranslationMap,
    noteAutosaveTimeoutRef,
    setAutosaveStatus,
    setSavedNotes,
  })
  useSyncDiscoveredTokenMemory({ tokens, setDiscoveredTokenMetadata })
  const sectionProps = useAppSectionProps({
    autosaveStatus,
    playgroundProps: {
      isSaveDialogOpen,
      saveDialogMode,
      noteNameDraft,
      duplicateNameConflictNoteId,
      onSaveDialogOpenChange: handleSaveDialogOpenChange,
      onNoteNameDraftChange: handleNoteNameDraftChange,
      onSaveDialogSubmit: handleSaveDialogSubmit,
      onResolveDuplicateName: resolveDuplicateNameConflict,
      phrasePopover,
      onPhrasePopoverOpenChange: handlePhrasePopoverOpenChange,
      isGeneratingPhraseTranslation,
      phraseTranslation,
      generatePhraseTranslationError,
      isSavingSentence,
      isSelectedPhraseSaved,
      onAddSentenceFromPhrase: () => {
        void addSentenceToSentencebank(phrasePopover.selectedText)
      },
      highlightPopover,
      onHighlightPopoverOpenChange: handleHighlightPopoverOpenChange,
      popoverDisplayToken,
      showPopoverLemma,
      popoverLemmaText,
      popoverMetadataBadges,
      showTranslationSkeleton,
      popoverIsNoun,
      popoverIsVerbLike,
      generateTranslationError,
      popoverTranslation,
      popoverPrimaryAction,
      addingTokens,
      onOpenWordbankFromPopover: () => {
        if (!popoverPrimaryAction?.lemma) {
          return
        }
        closeHighlightPopover()
        openWordbankLemma(popoverPrimaryAction.lemma)
      },
      onAddTokenFromPopover: () => {
        if (!popoverDisplayToken || !popoverPrimaryAction) {
          return
        }
        void addTokenToWordbank(popoverDisplayToken, popoverPrimaryAction)
        closeHighlightPopover()
      },
      noteText,
      noteHighlights,
      analysisError,
      onNoteTextChange: (nextText: string) => {
        setNoteText(nextText)
        clearPlaygroundTransientState()
      },
      onHighlightClick: ({ tokenIndex, left, lineTop, lineBottom }: {
        tokenIndex: number
        left: number
        lineTop: number
        lineBottom: number
      }) => {
        openHighlightPopover(tokenIndex, left, lineTop, lineBottom)
      },
      onTextSelectionSettled: handleEditorSelection,
    },
    savedNotes,
    openSavedNoteInPlayground,
    selectedLemma,
    wordbankError,
    isWordbankLoading,
    lemmas,
    groupedWordbankLemmas,
    setSelectedLemma,
    lemmaDetails,
    lemmaDetailsError,
    isLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton,
    pronunciationLoadingByForm,
    playPronunciation: async (form: string) => {
      await playPronunciation(form)
    },
    isRegeneratingLemmaPronunciation,
    regenerateSelectedLemmaPronunciation: async () => {
      await regenerateSelectedLemmaPronunciation()
    },
    selectedLemmaVerificationError,
    hasSuggestedVerificationChanges,
    isApplyingVerificationChanges,
    applySelectedLemmaVerificationChanges: async () => {
      await applySelectedLemmaVerificationChanges()
    },
    sentencebankError,
    isSentencebankLoading,
    sentences,
    status,
    backendUrl: BACKEND_URL,
    apiStatusItems,
    selectedNlpModel: developerSettings.selectedNlpModel,
    developerTranslationAzureApiKey: developerSettings.developerTranslationAzureApiKey,
    developerTranslationAzureRegion: developerSettings.developerTranslationAzureRegion,
    developerTranslationAzureEndpoint: developerSettings.developerTranslationAzureEndpoint,
    developerTtsAzureApiKey: developerSettings.developerTtsAzureApiKey,
    developerTtsAzureRegion: developerSettings.developerTtsAzureRegion,
    developerTtsAzureEndpoint: developerSettings.developerTtsAzureEndpoint,
    developerVerificationGeminiApiKey: developerSettings.developerVerificationGeminiApiKey,
    isSavingDeveloperApiKeys: developerSettings.isSavingDeveloperApiKeys,
    isResettingDatabase: developerSettings.isResettingDatabase,
    setSelectedNlpModel: developerSettings.setSelectedNlpModel,
    setDeveloperTranslationAzureApiKey: developerSettings.setDeveloperTranslationAzureApiKey,
    setDeveloperTranslationAzureRegion: developerSettings.setDeveloperTranslationAzureRegion,
    setDeveloperTranslationAzureEndpoint: developerSettings.setDeveloperTranslationAzureEndpoint,
    setDeveloperTtsAzureApiKey: developerSettings.setDeveloperTtsAzureApiKey,
    setDeveloperTtsAzureRegion: developerSettings.setDeveloperTtsAzureRegion,
    setDeveloperTtsAzureEndpoint: developerSettings.setDeveloperTtsAzureEndpoint,
    setDeveloperVerificationGeminiApiKey: developerSettings.setDeveloperVerificationGeminiApiKey,
    saveDeveloperApiKeys: developerSettings.saveDeveloperApiKeys,
    resetDatabase: developerSettings.resetDatabase,
  })
  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        wordbankCacheVersion={wordbankRefreshTick}
        savedNotes={savedNotes}
        onSelectPlayground={selectPlayground}
        onSelectNotes={selectNotes}
        onSelectWordbank={selectWordbank}
        onSelectSentencebank={selectSentencebank}
        onSelectDeveloper={selectDeveloper}
        onOpenWordbankLemma={openWordbankLemma}
        onOpenSavedNote={openSavedNoteById}
        onAddWordFromSearch={addWordFromSearch}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger />
          <span className="text-sm font-medium">Danote</span>
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col px-1 pt-3 pb-2 md:px-2 md:pt-8 md:pb-4">
          <span className="sr-only" aria-label="backend-connection-status">{status}</span>
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
            <div className="mb-6 md:mb-8 flex items-center justify-between gap-3">
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
                  hasUnreadNotifications={hasUnreadNotifications}
                  unreadCount={unreadNotifications.length}
                  notifications={notifications}
                  onOpenSaveDialog={openSaveDialog}
                  onNotificationsOpenChange={(open) => {
                    setIsNotificationsOpen(open)
                    if (open && hasUnreadNotifications) {
                      markAllNotificationsAsRead()
                    }
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
