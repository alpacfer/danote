import { useEffect, useMemo, useState } from "react"

import { AppBreadcrumb, AppSidebar } from "@/app/chrome"
import {
  DeveloperSection,
  NotesSection,
  PlaygroundHeaderActions,
  PlaygroundSection,
  SentencebankSection,
  WordbankSection,
} from "@/app/sections"
import {
  useAnalysis,
  useBackendHealth,
  useDiscoveredTokenMetadata,
  useLexiconData,
  useNoteWorkspace,
  useNotificationCenter,
  useNotesPersistence,
  usePlaygroundPopovers,
  useWordbankWorkflows,
} from "@/app/hooks"
import {
  BACKEND_URL,
  NLP_MODEL_OPTIONS,
  NOTE_AUTOSAVE_DEBOUNCE_MS,
  humanizeApiName,
  isLowConfidencePosTag,
  normalizeApiRuntimeStatus,
  normalizeWordKey,
  type ApiStatusItem,
  type AppSection,
  type DeveloperApiKeysUpdateResponse,
  type HealthPayload,
  type NlpModelOption,
  type ResetDatabaseResponse,
  type SavedNote,
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

  useEffect(() => {
    if (!activeSavedNoteId || !activeSavedNoteName) {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
      setAutosaveStatus("off")
      return
    }

    setAutosaveStatus("saving")
    if (noteAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(noteAutosaveTimeoutRef.current)
    }
    noteAutosaveTimeoutRef.current = window.setTimeout(() => {
      noteAutosaveTimeoutRef.current = null
      const savedAt = new Date().toISOString()
      const nextNote: SavedNote = {
        id: activeSavedNoteId,
        name: activeSavedNoteName,
        text: noteText,
        tokens: [...tokens],
        discoveredTokenMetadata: { ...discoveredTokenMetadata },
        generatedTranslationMap: { ...generatedTranslationMap },
        savedAt,
      }

      setSavedNotes((current) => {
        const existingIndex = current.findIndex((note) => note.id === activeSavedNoteId)
        if (existingIndex === -1) {
          return [nextNote, ...current]
        }
        const next = [...current]
        next[existingIndex] = nextNote
        return next
      })
      setAutosaveStatus("saved")
    }, NOTE_AUTOSAVE_DEBOUNCE_MS)

    return () => {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
    }
  }, [
    activeSavedNoteId,
    activeSavedNoteName,
    discoveredTokenMetadata,
    generatedTranslationMap,
    noteText,
    noteAutosaveTimeoutRef,
    setAutosaveStatus,
    setSavedNotes,
    tokens,
  ])

  useEffect(() => {
    if (tokens.length === 0) {
      return
    }

    setDiscoveredTokenMetadata((current) => {
      let changed = false
      const next = { ...current }
      for (const token of tokens) {
        if (isLowConfidencePosTag(token.pos_tag)) {
          continue
        }
        const tokenPos = token.pos_tag
        if (!tokenPos) {
          continue
        }
        const key = normalizeWordKey(token.normalized_token || token.surface_token)
        const lemma = token.matched_lemma ?? token.lemma_candidate ?? null
        const candidate = {
          pos_tag: tokenPos,
          morphology: token.morphology,
          lemma,
        }
        const existing = next[key]
        const existingForPos = existing?.byPos[candidate.pos_tag]

        if (
          !existing ||
          !existingForPos ||
          existingForPos.morphology !== candidate.morphology ||
          existingForPos.lemma !== candidate.lemma ||
          existing.latest.pos_tag !== candidate.pos_tag ||
          existing.latest.morphology !== candidate.morphology ||
          existing.latest.lemma !== candidate.lemma
        ) {
          next[key] = {
            latest: candidate,
            byPos: {
              ...(existing?.byPos ?? {}),
              [candidate.pos_tag]: candidate,
            },
          }
          changed = true
        }
      }
      return changed ? next : current
    })
  }, [setDiscoveredTokenMetadata, tokens])

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
            {activeSection === "playground"
              ? (
	                <PlaygroundSection
	                  isSaveDialogOpen={isSaveDialogOpen}
	                  saveDialogMode={saveDialogMode}
	                  noteNameDraft={noteNameDraft}
	                  duplicateNameConflictNoteId={duplicateNameConflictNoteId}
	                  onSaveDialogOpenChange={handleSaveDialogOpenChange}
	                  onNoteNameDraftChange={handleNoteNameDraftChange}
	                  onSaveDialogSubmit={handleSaveDialogSubmit}
	                  onResolveDuplicateName={resolveDuplicateNameConflict}
	                  phrasePopover={phrasePopover}
	                  onPhrasePopoverOpenChange={handlePhrasePopoverOpenChange}
	                  isGeneratingPhraseTranslation={isGeneratingPhraseTranslation}
	                  phraseTranslation={phraseTranslation}
	                  generatePhraseTranslationError={generatePhraseTranslationError}
                  isSavingSentence={isSavingSentence}
                  isSelectedPhraseSaved={isSelectedPhraseSaved}
	                  onAddSentenceFromPhrase={() => {
	                    void addSentenceToSentencebank(phrasePopover.selectedText)
	                  }}
	                  highlightPopover={highlightPopover}
	                  onHighlightPopoverOpenChange={handleHighlightPopoverOpenChange}
                  popoverDisplayToken={popoverDisplayToken}
                  showPopoverLemma={showPopoverLemma}
                  popoverLemmaText={popoverLemmaText}
                  popoverMetadataBadges={popoverMetadataBadges}
                  showTranslationSkeleton={showTranslationSkeleton}
                  popoverIsNoun={popoverIsNoun}
                  popoverIsVerbLike={popoverIsVerbLike}
                  generateTranslationError={generateTranslationError}
                  popoverTranslation={popoverTranslation}
                  popoverPrimaryAction={popoverPrimaryAction}
                  addingTokens={addingTokens}
	                  onOpenWordbankFromPopover={() => {
	                    if (!popoverPrimaryAction?.lemma) {
	                      return
	                    }
	                    closeHighlightPopover()
	                    setActiveSection("wordbank")
	                    setSelectedLemma(popoverPrimaryAction.lemma)
	                  }}
                  onAddTokenFromPopover={() => {
	                    if (!popoverDisplayToken || !popoverPrimaryAction) {
	                      return
	                    }
	                    void addTokenToWordbank(popoverDisplayToken, popoverPrimaryAction)
	                    closeHighlightPopover()
	                  }}
                  noteText={noteText}
                  noteHighlights={noteHighlights}
                  analysisError={analysisError}
	                  onNoteTextChange={(nextText) => {
	                    setNoteText(nextText)
	                    clearPlaygroundTransientState()
	                  }}
                  onHighlightClick={({ tokenIndex, left, lineTop, lineBottom }) => {
                    openHighlightPopover(tokenIndex, left, lineTop, lineBottom)
                  }}
                  onTextSelectionSettled={handleEditorSelection}
                />
              )
              : activeSection === "notes"
                ? (
                  <NotesSection
                    savedNotes={savedNotes}
                    onOpenSavedNote={openSavedNoteInPlayground}
                  />
                )
              : activeSection === "wordbank"
                ? (
                  <WordbankSection
                    selectedLemma={selectedLemma}
                    wordbankError={wordbankError}
                    isWordbankLoading={isWordbankLoading}
                    lemmas={lemmas}
                    groupedWordbankLemmas={groupedWordbankLemmas}
                    onSelectLemma={setSelectedLemma}
                    lemmaDetails={lemmaDetails}
                    lemmaDetailsError={lemmaDetailsError}
                    isLemmaDetailsLoading={isLemmaDetailsLoading}
                    showLemmaDetailsLoadingSkeleton={showLemmaDetailsLoadingSkeleton}
                    pronunciationLoadingByForm={pronunciationLoadingByForm}
                    onPlayPronunciation={(form) => {
                      void playPronunciation(form)
                    }}
                    isRegeneratingLemmaPronunciation={isRegeneratingLemmaPronunciation}
                    onRegenerateSelectedLemmaPronunciation={() => {
                      void regenerateSelectedLemmaPronunciation()
                    }}
                    selectedLemmaVerificationError={selectedLemmaVerificationError}
                    hasSuggestedVerificationChanges={hasSuggestedVerificationChanges}
                    isApplyingVerificationChanges={isApplyingVerificationChanges}
                    onApplySelectedLemmaVerificationChanges={() => {
                      void applySelectedLemmaVerificationChanges()
                    }}
                  />
                )
                : activeSection === "sentencebank"
                  ? (
                    <SentencebankSection
                      sentencebankError={sentencebankError}
                      isSentencebankLoading={isSentencebankLoading}
                      sentences={sentences}
                    />
                  )
                  : (
                    <DeveloperSection
                      badgeVariant={badgeVariant}
                      status={status}
                      backendUrl={BACKEND_URL}
                      apiStatusItems={apiStatusItems}
                      selectedNlpModel={selectedNlpModel}
                      nlpModelOptions={NLP_MODEL_OPTIONS}
                      developerTranslationAzureApiKey={developerTranslationAzureApiKey}
                      developerTranslationAzureRegion={developerTranslationAzureRegion}
                      developerTranslationAzureEndpoint={developerTranslationAzureEndpoint}
                      developerTtsAzureApiKey={developerTtsAzureApiKey}
                      developerTtsAzureRegion={developerTtsAzureRegion}
                      developerTtsAzureEndpoint={developerTtsAzureEndpoint}
                      developerVerificationGeminiApiKey={developerVerificationGeminiApiKey}
                      isSavingDeveloperApiKeys={isSavingDeveloperApiKeys}
                      isResettingDatabase={isResettingDatabase}
                      onSelectedNlpModelChange={setSelectedNlpModel}
                      onDeveloperTranslationAzureApiKeyChange={setDeveloperTranslationAzureApiKey}
                      onDeveloperTranslationAzureRegionChange={setDeveloperTranslationAzureRegion}
                      onDeveloperTranslationAzureEndpointChange={setDeveloperTranslationAzureEndpoint}
                      onDeveloperTtsAzureApiKeyChange={setDeveloperTtsAzureApiKey}
                      onDeveloperTtsAzureRegionChange={setDeveloperTtsAzureRegion}
                      onDeveloperTtsAzureEndpointChange={setDeveloperTtsAzureEndpoint}
                      onDeveloperVerificationGeminiApiKeyChange={setDeveloperVerificationGeminiApiKey}
                      onSaveDeveloperApiKeys={() => {
                        void saveDeveloperApiKeys()
                      }}
                      onResetDatabase={() => {
                        void resetDatabase()
                      }}
                    />
                  )}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
