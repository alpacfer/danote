import { type Dispatch, type SetStateAction } from "react"

import { createApiClient, normalizeSearchWord, type DeleteLemmaResponse, type DeleteMeaningResponse } from "@/app/core"
import { toast } from "sonner"

type ApiClient = ReturnType<typeof createApiClient>

type UseWordbankDeletionWorkflowParams = {
  apiClient: ApiClient
  selectedLemma: string | null
  goBack: () => void
  setLemmaDetails: Dispatch<SetStateAction<import("@/app/core").LemmaDetailsResponse | null>>
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
}

export function useWordbankDeletionWorkflow({
  apiClient,
  selectedLemma,
  goBack,
  setLemmaDetails,
  setWordbankRefreshTick,
  setSentencebankRefreshTick,
}: UseWordbankDeletionWorkflowParams) {
  async function deleteMeaning(meaningId: number): Promise<void> {
    try {
      const payload = await apiClient.deleteJson<DeleteMeaningResponse>(
        `/api/wordbank/meanings/${meaningId}`,
        "Could not delete meaning.",
      )
      toast.success(payload.message)
      setWordbankRefreshTick((current) => current + 1)
      setSentencebankRefreshTick((current) => current + 1)
      if (payload.was_lemma_deleted) {
        setLemmaDetails(null)
        goBack()
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not delete meaning. Try again."
      toast.error(message)
    }
  }

  async function deleteLemma(lemma: string = selectedLemma ?? ""): Promise<void> {
    const normalizedLemma = normalizeSearchWord(lemma)
    if (!normalizedLemma) {
      return
    }
    try {
      const payload = await apiClient.deleteJson<DeleteLemmaResponse>(
        `/api/wordbank/lemmas/${encodeURIComponent(normalizedLemma)}`,
        "Could not delete lemma.",
      )
      toast.success(payload.message)
      setLemmaDetails(null)
      setWordbankRefreshTick((current) => current + 1)
      setSentencebankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not delete lemma. Try again."
      toast.error(message)
    }
  }

  return {
    deleteMeaning,
    deleteLemma,
  }
}
