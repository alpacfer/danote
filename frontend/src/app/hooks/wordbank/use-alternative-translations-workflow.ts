import { type Dispatch, type SetStateAction, useCallback, useMemo, useState } from "react"

import {
  createApiClient,
  normalizeSearchWord,
  type FindAlternativeTranslationsResponse,
} from "@/app/core"
import { toast } from "sonner"

type UseAlternativeTranslationsWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
}

export function useAlternativeTranslationsWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
}: UseAlternativeTranslationsWorkflowParams) {
  const [isFindingAlternativeTranslations, setIsFindingAlternativeTranslations] = useState(false)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const findAlternativeTranslations = useCallback(async (meaningId: number | null) => {
    const lemma = normalizeSearchWord(selectedLemma ?? "")
    if (!lemma) {
      return
    }

    setIsFindingAlternativeTranslations(true)
    try {
      const payload = await apiClient.postJson<FindAlternativeTranslationsResponse>(
        "/api/wordbank/lexemes/find-alternative-translations",
        {
          stored_lemma: lemma,
          meaning_id: meaningId,
        },
        "Could not find alternative translations.",
      )
      if (payload.status === "error") {
        toast.error(payload.message)
        return
      }
      if (payload.status === "skipped") {
        toast.info(payload.message)
        return
      }
      toast.success(payload.message)
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not find alternative translations."
      toast.error(message)
    } finally {
      setIsFindingAlternativeTranslations(false)
    }
  }, [apiClient, selectedLemma, setWordbankRefreshTick])

  return {
    isFindingAlternativeTranslations,
    findAlternativeTranslations,
  }
}
