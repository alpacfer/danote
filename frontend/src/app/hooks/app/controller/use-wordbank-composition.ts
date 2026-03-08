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
    selectedLemma: navigation.selectedLemma,
    selectedMeaningId: navigation.selectedMeaningId,
    lemmaDetails: lexiconData.lemmaDetails,
    sentences: lexiconData.sentences,
    setAnalysisRefreshTick: analysis.setAnalysisRefreshTick,
    setWordbankRefreshTick: foundation.setWordbankRefreshTick,
    setSentencebankRefreshTick: foundation.setSentencebankRefreshTick,
    setActiveSection: navigation.setActiveSection,
    setSelectedLemma: navigation.setSelectedLemma,
    setSelectedMeaningId: navigation.setSelectedMeaningId,
    postTokenFeedback: async (payload) => {
      await postTokenFeedback(backendUrl, payload)
    },
    onSentenceSaved,
    pushNotification: notifications.pushNotification,
  })
}
