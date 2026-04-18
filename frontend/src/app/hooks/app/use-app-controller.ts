import { useState } from "react"

import { type DeveloperServiceProbeResponse } from "@/app/core"
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
  const [apiProbeStatuses, setApiProbeStatuses] = useState<Record<string, DeveloperServiceProbeResponse | null>>({})
  const foundation = useAppFoundation()
  const { navigation, health, analysis, discoveredTokenMetadataState, notesPersistence, lexiconData, notifications } = foundation
  const { unreadWordbankLemmaCounts, unreadWordbankNotificationCount } = notifications

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
    setApiProbeStatuses,
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
  const apiStatusItems = useApiStatusItems(health.healthPayload, health.status, apiProbeStatuses)

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
      selectedMeaningId: navigation.selectedMeaningId,
      wordbankError: lexiconData.wordbankError,
      isWordbankLoading: lexiconData.isWordbankLoading,
      lemmas: lexiconData.lemmas,
      groupedWordbankLemmas,
      unreadWordbankLemmaCounts,
      setSelectedLemma: navigation.setSelectedLemma,
      lemmaDetails: lexiconData.lemmaDetails,
      lemmaDetailsError: lexiconData.lemmaDetailsError,
      isLemmaDetailsLoading: lexiconData.isLemmaDetailsLoading,
      showLemmaDetailsLoadingSkeleton: lexiconData.showLemmaDetailsLoadingSkeleton,
      pronunciationLoadingByForm: wordbank.pronunciationLoadingByForm,
      regeneratingPronunciationByForm: wordbank.regeneratingPronunciationByForm,
      playPronunciation: wordbank.playPronunciation,
      regeneratePronunciation: wordbank.regeneratePronunciation,
      isFindingAlternativeTranslations: wordbank.isFindingAlternativeTranslations,
      findAlternativeTranslations: wordbank.findAlternativeTranslations,
      isRethinkingCategories: wordbank.isRethinkingCategories,
      rethinkCategories: wordbank.rethinkCategories,
      isCompletingMeaningVariations: wordbank.isCompletingMeaningVariations,
      completeMeaningVariations: wordbank.completeMeaningVariations,
      verificationOverview: wordbank.verificationOverview,
      verificationChanges: wordbank.verificationChanges,
      isLoadingVerificationChanges: wordbank.isLoadingVerificationChanges,
      isApplyingVerificationChanges: wordbank.isApplyingVerificationChanges,
      isRetryingVerification: wordbank.isRetryingVerification,
      isRevertingVerificationChange: wordbank.isRevertingVerificationChange,
      rerunningMeaningVerificationById: wordbank.rerunningMeaningVerificationById,
      markVisibleVerificationNotificationsAsRead: wordbank.markVisibleVerificationNotificationsAsRead,
      applyVerificationAction: wordbank.applyVerificationAction,
      retryVerificationTarget: wordbank.retryVerificationTarget,
      rerunMeaningVerification: wordbank.rerunMeaningVerification,
      revertVerificationChange: wordbank.revertVerificationChange,
      saveRelatedWordFromSearchSeed: wordbank.saveRelatedWordFromSearchSeed,
      openRelatedWordTarget: wordbank.openRelatedWordTarget,
      openSentence: navigation.openSentence,
    }),
    sentencebankSectionProps: buildSentencebankSectionProps({
      sentencebankError: lexiconData.sentencebankError,
      isSentencebankLoading: lexiconData.isSentencebankLoading,
      sentences: lexiconData.sentences,
      selectedSentenceId: navigation.selectedSentenceId,
      pendingSentence: navigation.pendingSentence,
      pronunciationLoadingBySentenceId: wordbank.pronunciationLoadingBySentenceId,
      regeneratingPronunciationBySentenceId: wordbank.regeneratingPronunciationBySentenceId,
      openSentence: navigation.openSentence,
      openWordbankLemma: navigation.openWordbankLemma,
      openWordbankMeaning: navigation.openWordbankMeaning,
      playPronunciation: wordbank.playSentencePronunciation,
      playPronunciationSlowly: wordbank.playSentencePronunciationSlowly,
      regeneratePronunciation: wordbank.regenerateSentencePronunciation,
    }),
    developerSectionProps: buildDeveloperSectionProps({
      status: health.status,
      backendUrl: foundation.backendUrl,
      apiStatusItems,
      selectedNlpModel: developerSettings.selectedNlpModel,
      translationProvider: developerSettings.translationProvider,
      developerTranslationAzureApiKey: developerSettings.developerTranslationAzureApiKey,
      developerTranslationAzureRegion: developerSettings.developerTranslationAzureRegion,
      developerTranslationAzureEndpoint: developerSettings.developerTranslationAzureEndpoint,
      developerTranslationDeeplApiKey: developerSettings.developerTranslationDeeplApiKey,
      developerTranslationDeeplEndpoint: developerSettings.developerTranslationDeeplEndpoint,
      developerTtsAzureApiKey: developerSettings.developerTtsAzureApiKey,
      developerTtsAzureRegion: developerSettings.developerTtsAzureRegion,
      developerTtsAzureEndpoint: developerSettings.developerTtsAzureEndpoint,
      developerGeminiApiKey: developerSettings.developerGeminiApiKey,
      isSavingDeveloperApiKeys: developerSettings.isSavingDeveloperApiKeys,
      isTestingTranslation: developerSettings.isTestingTranslation,
      translationProbeResult: developerSettings.translationProbeResult,
      isTestingSpeech: developerSettings.isTestingSpeech,
      speechProbeResult: developerSettings.speechProbeResult,
      isTestingGemini: developerSettings.isTestingGemini,
      geminiProbeResult: developerSettings.geminiProbeResult,
      isResettingDatabase: developerSettings.isResettingDatabase,
      setSelectedNlpModel: developerSettings.setSelectedNlpModel,
      setTranslationProvider: developerSettings.setTranslationProvider,
      setDeveloperTranslationAzureApiKey: developerSettings.setDeveloperTranslationAzureApiKey,
      setDeveloperTranslationAzureRegion: developerSettings.setDeveloperTranslationAzureRegion,
      setDeveloperTranslationAzureEndpoint: developerSettings.setDeveloperTranslationAzureEndpoint,
      setDeveloperTranslationDeeplApiKey: developerSettings.setDeveloperTranslationDeeplApiKey,
      setDeveloperTranslationDeeplEndpoint: developerSettings.setDeveloperTranslationDeeplEndpoint,
      setDeveloperTtsAzureApiKey: developerSettings.setDeveloperTtsAzureApiKey,
      setDeveloperTtsAzureRegion: developerSettings.setDeveloperTtsAzureRegion,
      setDeveloperTtsAzureEndpoint: developerSettings.setDeveloperTtsAzureEndpoint,
      setDeveloperGeminiApiKey: developerSettings.setDeveloperGeminiApiKey,
      saveDeveloperApiKeys: developerSettings.saveDeveloperApiKeys,
      runTranslationProbe: developerSettings.runTranslationProbe,
      runSpeechProbe: developerSettings.runSpeechProbe,
      runGeminiProbe: developerSettings.runGeminiProbe,
      resetDatabase: developerSettings.resetDatabase,
    }),
  }

  return {
    activeSection: navigation.activeSection,
    selectedLemma: navigation.selectedLemma,
    selectedMeaningId: navigation.selectedMeaningId,
    status: health.status,
    lemmas: lexiconData.lemmas,
    savedNotes: notesPersistence.savedNotes,
    wordbankRefreshTick: foundation.wordbankRefreshTick,
    searchTranslationConfigVersion: foundation.searchTranslationConfigVersion,
    activeSavedNote: notesPersistence.activeSavedNote,
    isVerifyingWords: wordbank.isVerifyingWords,
    notifications: notifications.notifications,
    isNotificationsOpen: notifications.isNotificationsOpen,
    setIsNotificationsOpen: notifications.setIsNotificationsOpen,
    hasUnreadNotifications: notifications.hasUnreadNotifications,
    unreadNotifications: notifications.unreadNotifications,
    unreadWordbankNotificationCount,
    unreadWordbankLemmaCounts,
    markAllNotificationsAsRead: notifications.markAllNotificationsAsRead,
    selectPlayground: navigation.selectPlayground,
    selectNotes: navigation.selectNotes,
    selectWordbank: navigation.selectWordbank,
    selectSentencebank: navigation.selectSentencebank,
    selectDeveloper: navigation.selectDeveloper,
    openWordbankLemma: navigation.openWordbankLemma,
    openWordbankMeaning: navigation.openWordbankMeaning,
    openWordbankRoot: navigation.openWordbankRoot,
    openSentence: navigation.openSentence,
    openSavedNoteById: workspace.openSavedNoteById,
    addSentenceToSentencebank: wordbank.addSentenceToSentencebank,
    addWordFromSearch: wordbank.addWordFromSearch,
    openSaveDialog: workspace.openSaveDialog,
    sectionProps,
  }
}
