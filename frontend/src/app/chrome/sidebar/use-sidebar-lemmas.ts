import { useEffect, useMemo, useState } from "react"

import { BACKEND_URL, createApiClient, type WordbankLemma } from "@/app/core"

export function useSidebarLemmas(lemmas: WordbankLemma[], isSearchOpen: boolean): WordbankLemma[] {
  const [searchSidebarLemmas, setSearchSidebarLemmas] = useState<WordbankLemma[]>([])
  const apiClient = useMemo(() => createApiClient({ backendUrl: BACKEND_URL }), [])

  useEffect(() => {
    if (lemmas.length > 0 || !isSearchOpen || searchSidebarLemmas.length > 0) {
      return
    }

    let cancelled = false
    void (async () => {
      try {
        const payload = await apiClient.tryGetJson<{ items?: WordbankLemma[] }>("/api/wordbank/lemmas")
        if (!cancelled) {
          setSearchSidebarLemmas(payload?.items ?? [])
        }
      } catch {
        if (!cancelled) {
          setSearchSidebarLemmas([])
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [apiClient, isSearchOpen, lemmas.length, searchSidebarLemmas.length])

  return lemmas.length > 0 ? lemmas : searchSidebarLemmas
}
