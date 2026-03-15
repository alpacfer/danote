import { type Dispatch, type SetStateAction, useCallback, useMemo, useState } from "react"

import { createApiClient, normalizeSearchWord, type CompleteVariationsResponse } from "@/app/core"
import { toast } from "sonner"

type UseCompleteVariationsWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  trackQueuedVerificationTargets: (
    storedLemma: string,
    queuedTargets: Array<{ meaning_id: number | null; stored_surface_form: string | null }>,
  ) => void
}

export function useCompleteVariationsWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
  trackQueuedVerificationTargets,
}: UseCompleteVariationsWorkflowParams) {
  const [isCompletingMeaningVariations, setIsCompletingMeaningVariations] = useState(false)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const completeMeaningVariations = useCallback(async (meaningId: number | null) => {
    const lemma = normalizeSearchWord(selectedLemma ?? "")
    if (!lemma || meaningId === null) {
      return
    }

    setIsCompletingMeaningVariations(true)
    try {
      const payload = await apiClient.postJson<CompleteVariationsResponse>(
        "/api/wordbank/lexemes/complete-variations",
        {
          stored_lemma: lemma,
          meaning_id: meaningId,
        },
        "Could not complete noun variations.",
      )
      if (payload.status === "skipped") {
        toast.info(payload.message)
        return
      }
      trackQueuedVerificationTargets(lemma, payload.queued_verification_targets ?? [])
      toast.success(payload.message)
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not complete noun variations."
      toast.error(message)
    } finally {
      setIsCompletingMeaningVariations(false)
    }
  }, [apiClient, selectedLemma, setWordbankRefreshTick, trackQueuedVerificationTargets])

  return {
    isCompletingMeaningVariations,
    completeMeaningVariations,
  }
}
