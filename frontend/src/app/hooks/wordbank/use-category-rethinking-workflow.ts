import { type Dispatch, type SetStateAction, useCallback, useMemo, useState } from "react"

import { createApiClient, normalizeSearchWord, type RethinkCategoriesResponse } from "@/app/core"
import { toast } from "sonner"

type UseCategoryRethinkingWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
}

export function useCategoryRethinkingWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
}: UseCategoryRethinkingWorkflowParams) {
  const [isRethinkingCategories, setIsRethinkingCategories] = useState(false)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const rethinkCategories = useCallback(async (meaningId: number | null) => {
    const lemma = normalizeSearchWord(selectedLemma ?? "")
    if (!lemma) {
      return
    }

    setIsRethinkingCategories(true)
    try {
      const payload = await apiClient.postJson<RethinkCategoriesResponse>(
        "/api/wordbank/lexemes/rethink-categories",
        {
          stored_lemma: lemma,
          stored_surface_form: null,
          meaning_id: meaningId,
        },
        "Could not rethink categories.",
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
      const message = error instanceof Error ? error.message : "Could not rethink categories."
      toast.error(message)
    } finally {
      setIsRethinkingCategories(false)
    }
  }, [apiClient, selectedLemma, setWordbankRefreshTick])

  return {
    isRethinkingCategories,
    rethinkCategories,
  }
}
