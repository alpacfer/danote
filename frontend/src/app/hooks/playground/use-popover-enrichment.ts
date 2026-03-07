import { useEffect, useMemo, useState } from "react"

import {
  POPOVER_ENRICH_CACHE_TTL_MS,
  createApiClient,
  normalizeSearchWord,
  normalizeWordKey,
  type AnalyzedToken,
  type ResolveQueryResponse,
} from "@/app/core"

type UsePopoverEnrichmentParams = {
  backendUrl: string
  isHighlightPopoverOpen: boolean
  popoverDisplayToken: AnalyzedToken | null
  rememberTranslation: (key: string, translation: string | null) => void
}

export function usePopoverEnrichment({
  backendUrl,
  isHighlightPopoverOpen,
  popoverDisplayToken,
  rememberTranslation,
}: UsePopoverEnrichmentParams) {
  const [enrichmentCacheByKey, setEnrichmentCacheByKey] = useState<Record<string, { payload: ResolveQueryResponse; cachedAt: number }>>({})
  const apiClient = useMemo(() => createApiClient({ backendUrl }), [backendUrl])
  const tokenValue = useMemo(
    () => normalizeSearchWord(popoverDisplayToken?.normalized_token || popoverDisplayToken?.surface_token || ""),
    [popoverDisplayToken],
  )
  const cacheKey = tokenValue ? normalizeWordKey(tokenValue) : null
  const popoverEnrichment = useMemo(() => {
    if (!cacheKey) {
      return null
    }
    return enrichmentCacheByKey[cacheKey]?.payload ?? null
  }, [cacheKey, enrichmentCacheByKey])

  useEffect(() => {
    if (!isHighlightPopoverOpen || !cacheKey || !tokenValue) {
      return
    }
    const cached = enrichmentCacheByKey[cacheKey]
    if (cached && Date.now() - cached.cachedAt < POPOVER_ENRICH_CACHE_TTL_MS) {
      if (cached.payload.da_to_en_translation) {
        rememberTranslation(cacheKey, cached.payload.da_to_en_translation)
      }
      return
    }

    let cancelled = false
    const controller = new AbortController()

    void (async () => {
      try {
        const payload = await apiClient.postJson<ResolveQueryResponse>(
          "/api/analyze/enrich-token",
          {
            token: tokenValue,
            include_translations: true,
            include_language_detection: true,
          },
          "Could not enrich token.",
          { signal: controller.signal },
        )
        if (cancelled) {
          return
        }
        setEnrichmentCacheByKey((current) => {
          const existing = current[cacheKey]
          if (existing?.payload === payload) {
            return current
          }
          return {
            ...current,
            [cacheKey]: {
              payload,
              cachedAt: Date.now(),
            },
          }
        })
        if (payload.da_to_en_translation) {
          rememberTranslation(cacheKey, payload.da_to_en_translation)
        }
      } catch {
        // ignore enrichment failures for popover fallback behavior
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [apiClient, cacheKey, enrichmentCacheByKey, isHighlightPopoverOpen, rememberTranslation, tokenValue])

  return {
    popoverEnrichment,
  }
}
