import { useCallback, useEffect, useRef } from "react"

import {
  createApiClient,
  normalizeSearchWord,
  type AppSection,
  type LemmaDetailsResponse,
} from "@/app/core"

const POST_VERIFICATION_DETAIL_REFRESH_DELAYS_MS = [750, 2_000] as const

type UsePostVerificationDetailRefreshParams = {
  activeSection: AppSection
  apiClient: ReturnType<typeof createApiClient>
  onOpenLemmaVerificationCompleted?: (payload: LemmaDetailsResponse) => void
  selectedLemma: string | null
}

export function usePostVerificationDetailRefresh({
  activeSection,
  apiClient,
  onOpenLemmaVerificationCompleted,
  selectedLemma,
}: UsePostVerificationDetailRefreshParams) {
  const openLemmaKeyRef = useRef("")
  const refreshTimeoutsRef = useRef<number[]>([])
  const onOpenLemmaVerificationCompletedRef = useRef(onOpenLemmaVerificationCompleted)

  useEffect(() => {
    openLemmaKeyRef.current = activeSection === "wordbank" ? normalizeSearchWord(selectedLemma ?? "") : ""
  }, [activeSection, selectedLemma])

  useEffect(() => {
    onOpenLemmaVerificationCompletedRef.current = onOpenLemmaVerificationCompleted
  }, [onOpenLemmaVerificationCompleted])

  useEffect(() => () => {
    for (const timeoutId of refreshTimeoutsRef.current) {
      window.clearTimeout(timeoutId)
    }
    refreshTimeoutsRef.current = []
  }, [])

  return useCallback((lemma: string) => {
    const lemmaKey = normalizeSearchWord(lemma)
    if (!lemmaKey) {
      return
    }
    for (const delay of POST_VERIFICATION_DETAIL_REFRESH_DELAYS_MS) {
      const timeoutId = window.setTimeout(() => {
        void (async () => {
          try {
            const payload = await apiClient.getJson<LemmaDetailsResponse>(
              `/api/wordbank/lemmas/${encodeURIComponent(lemmaKey)}`,
              "Could not load lemma details.",
            )
            if (openLemmaKeyRef.current === lemmaKey) {
              onOpenLemmaVerificationCompletedRef.current?.(payload)
            }
          } catch {
            // A post-completion refresh is best-effort; normal navigation can fetch again.
          }
        })()
      }, delay)
      refreshTimeoutsRef.current.push(timeoutId)
    }
  }, [apiClient])
}
