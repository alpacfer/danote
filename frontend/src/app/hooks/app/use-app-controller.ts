import { useApiStatusItems, useGroupedWordbankLemmas } from "@/app/hooks/app/use-app-derived-data"
import { useNoteAutosave } from "@/app/hooks/use-note-autosave"
import { useSyncDiscoveredTokenMemory } from "@/app/hooks/use-sync-discovered-token-memory"
import { buildPlaygroundProps } from "@/app/hooks/app/controller/build-playground-props"
import { useAppFoundation } from "@/app/hooks/app/controller/use-app-foundation"
import { useDeveloperComposition } from "@/app/hooks/app/controller/use-developer-composition"
import { usePlaygroundComposition } from "@/app/hooks/app/controller/use-playground-composition"
import { useWordbankComposition } from "@/app/hooks/app/controller/use-wordbank-composition"
import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
import { buildNotesSectionProps } from "@/app/sections/notes-section-props"
import { buildPlaygroundSectionProps } from "@/app/sections/playground-section-props"
import { buildSentencebankSectionProps } from "@/app/sections/sentencebank-section-props"
import { buildWordbankSectionProps } from "@/app/sections/wordbank-section-props"

export function useAppController() {
  const foundation = useAppFoundation()
  const { navigation, health, analysis, discoveredTokenMetadataState, notesPersistence, lexiconData, notifications } = foundation

  const { popovers, workspace } = usePlaygroundComposition({ foundation })

  const wordbank = useWordbankComposition({
    foundation,
    onSentenceSaved: () => {
      popovers.handlePhrasePopoverOpenChange(false)
    },
  })

  const developerSettings = useDeveloperComposition({
    foundation,
    clearVerificationErrors: wordbank.clearVerificationErrors,
  })

  useNoteAutosave({
    activeSavedNoteId: notesPersistence.activeSavedNoteId,
    activeSavedNoteName: notesPersistence.activeSavedNoteName,
    noteText: foundation.noteText,
    tokens: analysis.tokens,
    discoveredTokenMetadata: discoveredTokenMetadataState.discoveredTokenMetadata,
    generatedTranslationMap: popovers.generatedTranslationMap,
    noteAutosaveTimeoutRef: notesPersistence.noteAutosaveTimeoutRef,
    setAutosaveStatus: notesPersistence.setAutosaveStatus,
    setSavedNotes: notesPersistence.setSavedNotes,
  })

  useSyncDiscoveredTokenMemory({
    tokens: analysis.tokens,
    setDiscoveredTokenMetadata: discoveredTokenMetadataState.setDiscoveredTokenMetadata,
  })

  const groupedWordbankLemmas = useGroupedWordbankLemmas(lexiconData.lemmas)
  const apiStatusItems = useApiStatusItems(health.healthPayload, health.status)

  const sectionProps = {
    autosaveStatusLabel: notesPersistence.autosaveStatus === "saving"
      ? "Autosaving..."
      : notesPersistence.autosaveStatus === "saved"
        ? "Autosaved"
        : "Autosave off",
    playgroundSectionProps: buildPlaygroundSectionProps({
      playgroundProps: buildPlaygroundProps({
        isSaveDialogOpen: workspace.isSaveDialogOpen,
        saveDialogMode: workspace.saveDialogMode,
        noteNameDraft: workspace.noteNameDraft,
        duplicateNameConflictNoteId: workspace.duplicateNameConflictNoteId,
        handleSaveDialogOpenChange: workspace.handleSaveDialogOpenChange,
        handleNoteNameDraftChange: workspace.handleNoteNameDraftChange,
        handleSaveDialogSubmit: workspace.handleSaveDialogSubmit,
        resolveDuplicateNameConflict: workspace.resolveDuplicateNameConflict,
        phrasePopover: popovers.phrasePopover,
        handlePhrasePopoverOpenChange: popovers.handlePhrasePopoverOpenChange,
        isGeneratingPhraseTranslation: popovers.isGeneratingPhraseTranslation,
        phraseTranslation: popovers.phraseTranslation,
        generatePhraseTranslationError: popovers.generatePhraseTranslationError,
        isSavingSentence: wordbank.isSavingSentence,
        isSelectedPhraseSaved: popovers.isSelectedPhraseSaved,
        addSentenceToSentencebank: wordbank.addSentenceToSentencebank,
        highlightPopover: popovers.highlightPopover,
        handleHighlightPopoverOpenChange: popovers.handleHighlightPopoverOpenChange,
        popoverDisplayToken: popovers.popoverDisplayToken,
        showPopoverLemma: popovers.showPopoverLemma,
        popoverLemmaText: popovers.popoverLemmaText,
        popoverMetadataBadges: popovers.popoverMetadataBadges,
        showTranslationSkeleton: popovers.showTranslationSkeleton,
        popoverIsNoun: popovers.popoverIsNoun,
        popoverIsVerbLike: popovers.popoverIsVerbLike,
        generateTranslationError: popovers.generateTranslationError,
        popoverTranslation: popovers.popoverTranslation,
        popoverPrimaryAction: popovers.popoverPrimaryAction,
        addingTokens: wordbank.addingTokens,
        closeHighlightPopover: popovers.closeHighlightPopover,
        openWordbankLemma: navigation.openWordbankLemma,
        addTokenToWordbank: wordbank.addTokenToWordbank,
        noteText: foundation.noteText,
        noteHighlights: analysis.noteHighlights,
        analysisError: analysis.analysisError,
        setNoteText: foundation.setNoteText,
        clearPlaygroundTransientState: popovers.clearTransientState,
        openHighlightPopover: popovers.openHighlightPopover,
        handleEditorSelection: popovers.handleEditorSelection,
      }),
    }),
    notesSectionProps: buildNotesSectionProps({
      savedNotes: notesPersistence.savedNotes,
      openSavedNoteInPlayground: workspace.openSavedNoteInPlayground,
    }),
    wordbankSectionProps: buildWordbankSectionProps({
      selectedLemma: navigation.selectedLemma,
      wordbankError: lexiconData.wordbankError,
      isWordbankLoading: lexiconData.isWordbankLoading,
      lemmas: lexiconData.lemmas,
      groupedWordbankLemmas,
      setSelectedLemma: navigation.setSelectedLemma,
      lemmaDetails: lexiconData.lemmaDetails,
      lemmaDetailsError: lexiconData.lemmaDetailsError,
      isLemmaDetailsLoading: lexiconData.isLemmaDetailsLoading,
      showLemmaDetailsLoadingSkeleton: lexiconData.showLemmaDetailsLoadingSkeleton,
      pronunciationLoadingByForm: wordbank.pronunciationLoadingByForm,
      playPronunciation: wordbank.playPronunciation,
      isRegeneratingLemmaPronunciation: wordbank.isRegeneratingLemmaPronunciation,
      regenerateSelectedLemmaPronunciation: wordbank.regenerateSelectedLemmaPronunciation,
      selectedLemmaVerificationError: wordbank.selectedLemmaVerificationError,
      hasSuggestedVerificationChanges: wordbank.hasSuggestedVerificationChanges,
      isApplyingVerificationChanges: wordbank.isApplyingVerificationChanges,
      applySelectedLemmaVerificationChanges: wordbank.applySelectedLemmaVerificationChanges,
    }),
    sentencebankSectionProps: buildSentencebankSectionProps({
      sentencebankError: lexiconData.sentencebankError,
      isSentencebankLoading: lexiconData.isSentencebankLoading,
      sentences: lexiconData.sentences,
    }),
    developerSectionProps: buildDeveloperSectionProps({
      status: health.status,
      backendUrl: foundation.backendUrl,
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
    }),
  }

  return {
    activeSection: navigation.activeSection,
    selectedLemma: navigation.selectedLemma,
    status: health.status,
    lemmas: lexiconData.lemmas,
    savedNotes: notesPersistence.savedNotes,
    wordbankRefreshTick: foundation.wordbankRefreshTick,
    activeSavedNote: notesPersistence.activeSavedNote,
    notifications: notifications.notifications,
    isNotificationsOpen: notifications.isNotificationsOpen,
    setIsNotificationsOpen: notifications.setIsNotificationsOpen,
    hasUnreadNotifications: notifications.hasUnreadNotifications,
    unreadNotifications: notifications.unreadNotifications,
    markAllNotificationsAsRead: notifications.markAllNotificationsAsRead,
    selectPlayground: navigation.selectPlayground,
    selectNotes: navigation.selectNotes,
    selectWordbank: navigation.selectWordbank,
    selectSentencebank: navigation.selectSentencebank,
    selectDeveloper: navigation.selectDeveloper,
    openWordbankLemma: navigation.openWordbankLemma,
    openWordbankRoot: navigation.openWordbankRoot,
    openSavedNoteById: workspace.openSavedNoteById,
    addWordFromSearch: wordbank.addWordFromSearch,
    openSaveDialog: workspace.openSaveDialog,
    sectionProps,
  }
}
