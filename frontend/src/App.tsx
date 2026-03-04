import { useMemo, useState } from "react"

import { AppBreadcrumb, AppSidebar } from "@/app/chrome"
import {
  PlaygroundHeaderActions,
} from "@/app/sections"
import { SectionContent } from "@/app/layout/section-content"
import {
  useAnalysis,
  useBackendHealth,
  useDiscoveredTokenMetadata,
  useLexiconData,
  useNoteAutosave,
  useNoteWorkspace,
  useNotificationCenter,
  useNotesPersistence,
  usePlaygroundPopovers,
  useSyncDiscoveredTokenMemory,
  useWordbankWorkflows,
} from "@/app/hooks"
import {
  BACKEND_URL,
  NLP_MODEL_OPTIONS,
  humanizeApiName,
  normalizeApiRuntimeStatus,
  type ApiStatusItem,
  type AppSection,
  type DeveloperApiKeysUpdateResponse,
  type HealthPayload,
  type NlpModelOption,
  type ResetDatabaseResponse,
  type TokenFeedbackPayload,
  type WordbankLemma,
} from "@/app/core"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
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
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [noteText, setNoteText] = useState("")
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)
  const [sentencebankRefreshTick, setSentencebankRefreshTick] = useState(0)

  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [isResettingDatabase, setIsResettingDatabase] = useState(false)
  const [selectedNlpModel, setSelectedNlpModel] = useState<NlpModelOption>(
    NLP_MODEL_OPTIONS[0],
  )
  const [developerTranslationAzureApiKey, setDeveloperTranslationAzureApiKey] = useState("")
  const [developerTranslationAzureRegion, setDeveloperTranslationAzureRegion] = useState("")
  const [developerTranslationAzureEndpoint, setDeveloperTranslationAzureEndpoint] = useState("")
  const [developerTtsAzureApiKey, setDeveloperTtsAzureApiKey] = useState("")
  const [developerTtsAzureRegion, setDeveloperTtsAzureRegion] = useState("")
  const [developerTtsAzureEndpoint, setDeveloperTtsAzureEndpoint] = useState("")
  const [developerVerificationGeminiApiKey, setDeveloperVerificationGeminiApiKey] = useState("")
  const [isSavingDeveloperApiKeys, setIsSavingDeveloperApiKeys] = useState(false)

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
  const {
    discoveredTokenMetadata,
    setDiscoveredTokenMetadata,
  } = useDiscoveredTokenMetadata()
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

  const groupedWordbankLemmas = useMemo(() => {
    const collator = new Intl.Collator("da", { sensitivity: "base" })
    const sortedLemmas = [...lemmas].sort((left, right) => collator.compare(left.lemma, right.lemma))
    const groups = new Map<string, WordbankLemma[]>()

    for (const lemma of sortedLemmas) {
      const normalizedLemma = lemma.lemma.trim()
      if (!normalizedLemma) {
        continue
      }
      const groupLetter = normalizedLemma[0].toLocaleUpperCase("da-DK")
      if (!groups.has(groupLetter)) {
        groups.set(groupLetter, [])
      }
      groups.get(groupLetter)?.push(lemma)
    }

    return Array.from(groups.entries())
      .sort(([left], [right]) => collator.compare(left, right))
      .map(([letter, items]) => ({ letter, items }))
  }, [lemmas])
  const apiStatusItems = useMemo(() => {
    const apis = healthPayload?.apis ?? {}
    const priorityOrder = ["backend", "azure_translator", "azure_speech"]
    const orderedNames = [
      ...priorityOrder.filter((name) => Object.hasOwn(apis, name)),
      ...Object.keys(apis).filter((name) => !priorityOrder.includes(name)).sort(),
    ]

    if (orderedNames.length === 0) {
      return [
        {
          name: "backend",
          label: "Backend API",
          status: status === "connected" ? "ok" : status === "degraded" ? "degraded" : "unknown",
          message: null,
        },
      ] satisfies ApiStatusItem[]
    }

    return orderedNames.map((name) => {
      const entry = apis[name] ?? {}
      return {
        name,
        label: humanizeApiName(name),
        status: normalizeApiRuntimeStatus(entry.status),
        message: entry.message ?? null,
      }
    }) satisfies ApiStatusItem[]
  }, [healthPayload, status])

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
  useSyncDiscoveredTokenMemory({
    tokens,
    setDiscoveredTokenMetadata,
  })

  const badgeVariant =
    status === "connected"
      ? "secondary"
      : status === "degraded"
        ? "outline"
        : status === "offline"
          ? "destructive"
          : "outline"
  const autosaveStatusLabel =
    autosaveStatus === "saving"
      ? "Autosaving..."
      : autosaveStatus === "saved"
        ? "Autosaved"
        : "Autosave off"

  const playgroundSectionProps = {
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
      setActiveSection("wordbank")
      setSelectedLemma(popoverPrimaryAction.lemma)
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
  }
  const notesSectionProps = {
    savedNotes,
    onOpenSavedNote: openSavedNoteInPlayground,
  }
  const wordbankSectionProps = {
    selectedLemma,
    wordbankError,
    isWordbankLoading,
    lemmas,
    groupedWordbankLemmas,
    onSelectLemma: setSelectedLemma,
    lemmaDetails,
    lemmaDetailsError,
    isLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton,
    pronunciationLoadingByForm,
    onPlayPronunciation: (form: string) => {
      void playPronunciation(form)
    },
    isRegeneratingLemmaPronunciation,
    onRegenerateSelectedLemmaPronunciation: () => {
      void regenerateSelectedLemmaPronunciation()
    },
    selectedLemmaVerificationError,
    hasSuggestedVerificationChanges,
    isApplyingVerificationChanges,
    onApplySelectedLemmaVerificationChanges: () => {
      void applySelectedLemmaVerificationChanges()
    },
  }
  const sentencebankSectionProps = {
    sentencebankError,
    isSentencebankLoading,
    sentences,
  }
  const developerSectionProps = {
    badgeVariant,
    status,
    backendUrl: BACKEND_URL,
    apiStatusItems,
    selectedNlpModel,
    nlpModelOptions: NLP_MODEL_OPTIONS,
    developerTranslationAzureApiKey,
    developerTranslationAzureRegion,
    developerTranslationAzureEndpoint,
    developerTtsAzureApiKey,
    developerTtsAzureRegion,
    developerTtsAzureEndpoint,
    developerVerificationGeminiApiKey,
    isSavingDeveloperApiKeys,
    isResettingDatabase,
    onSelectedNlpModelChange: setSelectedNlpModel,
    onDeveloperTranslationAzureApiKeyChange: setDeveloperTranslationAzureApiKey,
    onDeveloperTranslationAzureRegionChange: setDeveloperTranslationAzureRegion,
    onDeveloperTranslationAzureEndpointChange: setDeveloperTranslationAzureEndpoint,
    onDeveloperTtsAzureApiKeyChange: setDeveloperTtsAzureApiKey,
    onDeveloperTtsAzureRegionChange: setDeveloperTtsAzureRegion,
    onDeveloperTtsAzureEndpointChange: setDeveloperTtsAzureEndpoint,
    onDeveloperVerificationGeminiApiKeyChange: setDeveloperVerificationGeminiApiKey,
    onSaveDeveloperApiKeys: () => {
      void saveDeveloperApiKeys()
    },
    onResetDatabase: () => {
      void resetDatabase()
    },
  }
  async function postTokenFeedback(payload: TokenFeedbackPayload) {
    try {
      await fetch(`${BACKEND_URL}/api/tokens/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
    } catch {
      // Feedback logging is best-effort in v1.
    }
  }

  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the complete database and cannot be undone. Continue?",
    )
    if (!shouldReset) {
      return
    }

    setIsResettingDatabase(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/wordbank/database`, {
        method: "DELETE",
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Reset database request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ResetDatabaseResponse
      toast.success(payload.message)

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
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not reset database."
      toast.error(message)
      void error
    } finally {
      setIsResettingDatabase(false)
    }
  }

  async function saveDeveloperApiKeys() {
    setIsSavingDeveloperApiKeys(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/developer/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          translation_azure_api_key: developerTranslationAzureApiKey,
          translation_azure_region: developerTranslationAzureRegion,
          translation_azure_endpoint: developerTranslationAzureEndpoint,
          tts_azure_api_key: developerTtsAzureApiKey,
          tts_azure_region: developerTtsAzureRegion,
          tts_azure_endpoint: developerTtsAzureEndpoint,
          word_verification_gemini_api_key: developerVerificationGeminiApiKey,
        }),
      })

      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Save API keys request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as DeveloperApiKeysUpdateResponse
      toast.success(payload.message || "Runtime API keys updated.")

      const healthResponse = await fetch(`${BACKEND_URL}/api/health`)
      if (healthResponse.ok) {
        const payload = (await healthResponse.json()) as HealthPayload
        setHealthPayload(payload)
        setStatus(payload.status === "ok" ? "connected" : payload.status === "degraded" ? "degraded" : "offline")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save API keys."
      toast.error(message)
    } finally {
      setIsSavingDeveloperApiKeys(false)
    }
  }

  return (
    <SidebarProvider>
      <AppSidebar
        activeSection={activeSection}
        lemmas={lemmas}
        wordbankCacheVersion={wordbankRefreshTick}
        savedNotes={savedNotes}
        onSelectPlayground={() => {
          setActiveSection("playground")
        }}
        onSelectNotes={() => {
          setActiveSection("notes")
          setSelectedLemma(null)
        }}
        onSelectWordbank={() => {
          setActiveSection("wordbank")
          setSelectedLemma(null)
        }}
        onSelectSentencebank={() => {
          setActiveSection("sentencebank")
          setSelectedLemma(null)
        }}
        onSelectDeveloper={() => {
          setActiveSection("developer")
          setSelectedLemma(null)
        }}
        onOpenWordbankLemma={(lemma) => {
          setActiveSection("wordbank")
          setSelectedLemma(lemma)
        }}
        onOpenSavedNote={openSavedNoteById}
        onAddWordFromSearch={addWordFromSearch}
      />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 px-4 md:hidden">
          <SidebarTrigger />
          <span className="text-sm font-medium">Danote</span>
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col px-1 pt-3 pb-2 md:px-2 md:pt-8 md:pb-4">
          <span className="sr-only" aria-label="backend-connection-status">
            {status}
          </span>
          <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col">
            <div className="mb-6 md:mb-8 flex items-center justify-between gap-3">
              <AppBreadcrumb
                activeSection={activeSection}
                selectedLemma={selectedLemma}
                activeNoteName={activeSavedNote?.name ?? null}
                onSelectWordbank={() => {
                  setActiveSection("wordbank")
                  setSelectedLemma(null)
                }}
              />
              {activeSection === "playground" ? (
                <PlaygroundHeaderActions
                  autosaveStatusLabel={autosaveStatusLabel}
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
              playgroundProps={playgroundSectionProps}
              notesProps={notesSectionProps}
              wordbankProps={wordbankSectionProps}
              sentencebankProps={sentencebankSectionProps}
              developerProps={developerSectionProps}
            />
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
