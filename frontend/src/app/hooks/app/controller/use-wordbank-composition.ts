import { useWordbankWorkflows } from "@/app/hooks/use-wordbank-workflows"

import type { useAppFoundation } from "@/app/hooks/app/controller/use-app-foundation"
import { extractErrorMessage, postTokenFeedback } from "@/app/hooks/app/controller/runtime-utils"

type AppFoundation = ReturnType<typeof useAppFoundation>

type UseWordbankCompositionArgs = {
  foundation: AppFoundation
  onSentenceSaved: () => void
}

export function useWordbankComposition({ foundation, onSentenceSaved }: UseWordbankCompositionArgs) {
  const { backendUrl, navigation, lexiconData, analysis, notifications } = foundation

  return useWordbankWorkflows({
    backendUrl,
    extractErrorMessage,
    activeSection: navigation.activeSection,
    selectedLemma: navigation.selectedLemma,
    lemmaDetails: lexiconData.lemmaDetails,
    setLemmaDetails: lexiconData.setLemmaDetails,
    setLemmaDetailsError: lexiconData.setLemmaDetailsError,
    setIsLemmaDetailsLoading: lexiconData.setIsLemmaDetailsLoading,
    setShowLemmaDetailsLoadingSkeleton: lexiconData.setShowLemmaDetailsLoadingSkeleton,
    sentences: lexiconData.sentences,
    setSentences: lexiconData.setSentences,
    setAnalysisRefreshTick: analysis.setAnalysisRefreshTick,
    setWordbankRefreshTick: foundation.setWordbankRefreshTick,
    setSentencebankRefreshTick: foundation.setSentencebankRefreshTick,
    openPendingSentence: navigation.openPendingSentence,
    openSentence: navigation.openSentence,
    replaceCurrentSentence: navigation.replaceCurrentSentence,
    openWordbankTarget: navigation.openWordbankTarget,
    goBack: navigation.goBack,
    trackQueuedPronunciationForms: lexiconData.trackQueuedPronunciationForms,
    postTokenFeedback: async (payload) => {
      await postTokenFeedback(backendUrl, payload)
    },
    onSentenceSaved,
    pushNotification: notifications.pushNotification,
    markWordVerificationNotificationsAsRead: notifications.markWordVerificationNotificationsAsRead,
    clearWordVerificationNotification: notifications.clearWordVerificationNotification,
  })
}
