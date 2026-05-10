import { useState } from "react"

import { type DeveloperServiceProbeResponse } from "@/app/core"
import { useApiStatusItems, useGroupedWordbankLemmas } from "@/app/hooks/app/use-app-derived-data"
import { useSyncDiscoveredTokenMemory } from "@/app/hooks/use-sync-discovered-token-memory"
import { useAppFoundation } from "@/app/hooks/app/controller/use-app-foundation"
import { useDeveloperComposition } from "@/app/hooks/app/controller/use-developer-composition"
import { useWordbankComposition } from "@/app/hooks/app/controller/use-wordbank-composition"
import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
import { buildSentencebankSectionProps } from "@/app/sections/sentencebank-section-props"
import { buildWordbankSectionProps } from "@/app/sections/wordbank-section-props"

export function useAppController() {
  const [apiProbeStatuses, setApiProbeStatuses] = useState<Record<string, DeveloperServiceProbeResponse | null>>({})
  const foundation = useAppFoundation()
  const { navigation, health, analysis, discoveredTokenMetadataState, lexiconData, notifications } = foundation
  const { unreadWordbankLemmaCounts, unreadWordbankNotificationCount } = notifications

  const wordbank = useWordbankComposition({
    foundation,
    onSentenceSaved: () => {},
  })

  const developerSettings = useDeveloperComposition({
    foundation,
    clearVerificationErrors: wordbank.clearVerificationErrors,
    setApiProbeStatuses,
  })

  useSyncDiscoveredTokenMemory({
    tokens: analysis.tokens,
    setDiscoveredTokenMetadata: discoveredTokenMetadataState.setDiscoveredTokenMetadata,
  })

  const groupedWordbankLemmas = useGroupedWordbankLemmas(lexiconData.lemmas)
  const apiStatusItems = useApiStatusItems(health.healthPayload, health.status, apiProbeStatuses)

  const sectionProps = {
    wordbankSectionProps: buildWordbankSectionProps({
      selectedLemma: navigation.selectedLemma,
      selectedMeaningId: navigation.selectedMeaningId,
      wordbankError: lexiconData.wordbankError,
      isWordbankLoading: lexiconData.isWordbankLoading,
      lemmas: lexiconData.lemmas,
      groupedWordbankLemmas,
      unreadWordbankLemmaCounts,
      setSelectedLemma: navigation.setSelectedLemma,
      openWordbankLemmaRaw: navigation.openWordbankLemmaRaw,
      openWordbankPinnedTab: navigation.openWordbankPinnedTab,
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
      generatingExampleByMeaningId: wordbank.generatingExampleByMeaningId,
      generateExampleForMeaning: wordbank.generateExampleForMeaning,
      generatingStaticExampleByLemma: wordbank.generatingStaticExampleByLemma,
      generateStaticExampleForLemma: wordbank.generateStaticExampleForLemma,
      sentences: lexiconData.sentences,
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
      saveSentenceTokenToWordbank: wordbank.saveSentenceTokenToWordbank,
    }),
    developerSectionProps: buildDeveloperSectionProps({
      status: health.status,
      backendUrl: foundation.backendUrl,
      apiStatusItems,
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
      isSeedingNumbersAudio: developerSettings.isSeedingNumbersAudio,
      isSeedingPresavedWordsAudio: developerSettings.isSeedingPresavedWordsAudio,
      isRegeneratingPresavedWordsAudio: developerSettings.isRegeneratingPresavedWordsAudio,
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
      seedPresavedWordsAudio: developerSettings.seedPresavedWordsAudio,
      regeneratePresavedWordsAudio: developerSettings.regeneratePresavedWordsAudio,
    }),
  }

  return {
    activeSection: navigation.activeSection,
    selectedLemma: navigation.selectedLemma,
    selectedMeaningId: navigation.selectedMeaningId,
    status: health.status,
    lemmas: lexiconData.lemmas,
    wordbankRefreshTick: foundation.wordbankRefreshTick,
    searchTranslationConfigVersion: foundation.searchTranslationConfigVersion,
    isVerifyingWords: wordbank.isVerifyingWords,
    notifications: notifications.notifications,
    isNotificationsOpen: notifications.isNotificationsOpen,
    setIsNotificationsOpen: notifications.setIsNotificationsOpen,
    hasUnreadNotifications: notifications.hasUnreadNotifications,
    unreadNotifications: notifications.unreadNotifications,
    unreadWordbankNotificationCount,
    unreadWordbankLemmaCounts,
    markAllNotificationsAsRead: notifications.markAllNotificationsAsRead,
    selectWordbank: navigation.selectWordbank,
    selectSentencebank: navigation.selectSentencebank,
    selectDeveloper: navigation.selectDeveloper,
    openWordbankLemma: navigation.openWordbankLemma,
    openWordbankLemmaRaw: navigation.openWordbankLemmaRaw,
    openWordbankMeaning: navigation.openWordbankMeaning,
    openWordbankRoot: navigation.openWordbankRoot,
    sentences: lexiconData.sentences,
    openSentence: navigation.openSentence,
    addSentenceToSentencebank: wordbank.addSentenceToSentencebank,
    addWordFromSearch: wordbank.addWordFromSearch,
    sectionProps,
    generatedExamplePreview: wordbank.generatedExamplePreview,
    isGeneratingExample: wordbank.generatedExamplePreview
      ? (
        wordbank.generatedExamplePreview.target.kind === "wordbank"
          ? Boolean(wordbank.generatingExampleByMeaningId[wordbank.generatedExamplePreview.target.meaning_id])
          : Boolean(wordbank.generatingStaticExampleByLemma[wordbank.generatedExamplePreview.target.stored_lemma])
      )
      : false,
    isSavingGeneratedExample: wordbank.isSavingSentence,
    saveGeneratedExample: wordbank.saveGeneratedExample,
    regenerateExample: wordbank.regenerateExample,
    discardGeneratedExample: wordbank.discardGeneratedExample,
  }
}
