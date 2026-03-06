import { toast } from "sonner"

import { runAppDatabaseResetWorkflow } from "@/app/core/app-reset-workflow"
import { useDeveloperSettings } from "@/app/hooks/app/use-developer-settings"

import type { useAppFoundation } from "@/app/hooks/app/controller/use-app-foundation"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

type AppFoundation = ReturnType<typeof useAppFoundation>

type UseDeveloperCompositionArgs = {
  foundation: AppFoundation
  clearVerificationErrors: () => void
}

export function useDeveloperComposition({ foundation, clearVerificationErrors }: UseDeveloperCompositionArgs) {
  const { backendUrl, health, navigation, lexiconData, analysis, setNoteText, setWordbankRefreshTick, setSentencebankRefreshTick } = foundation

  return useDeveloperSettings({
    backendUrl,
    extractErrorMessage,
    setStatus: health.setStatus,
    setHealthPayload: health.setHealthPayload,
    onNotifySuccess: (message) => {
      toast.success(message)
    },
    onNotifyError: (message) => {
      toast.error(message)
    },
    onDatabaseReset: () => {
      runAppDatabaseResetWorkflow({
        resetEditorState: () => {
          setNoteText("")
          analysis.setTokens([])
          analysis.setAnalysisError(null)
        },
        resetLexiconState: () => {
          navigation.setSelectedLemma(null)
          lexiconData.setLemmas([])
          lexiconData.setSentences([])
          lexiconData.setLemmaDetails(null)
          lexiconData.setLemmaDetailsError(null)
        },
        clearVerificationErrors,
        bumpWordbankRefresh: () => {
          setWordbankRefreshTick((current) => current + 1)
        },
        bumpSentencebankRefresh: () => {
          setSentencebankRefreshTick((current) => current + 1)
        },
      })
    },
  })
}
