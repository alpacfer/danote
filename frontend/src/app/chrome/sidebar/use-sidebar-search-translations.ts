import { useEffect, useMemo, useRef, useState } from "react"

import {
  BACKEND_URL,
  createApiClient,
  normalizeSearchWord,
  type CORSearchGroup,
  type CORSearchVariant,
  type GenerateTranslationResponse,
  type WordbankLemma,
} from "@/app/core"

type WordbankResult = {
  lemma: WordbankLemma
  matchSurface: string | null
}

type GroupedVariant = {
  group: CORSearchGroup
  variant: CORSearchVariant
}

type UseSidebarSearchTranslationsParams = {
  orderedWordbankResults: WordbankResult[]
  displayVariantBySavedLemma: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  corSearchVariantsToRender: GroupedVariant[]
}

function normalizeTranslationValue(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

function buildTranslationKey(surfaceToken: string, lemmaCandidate: string | null): string {
  return [
    normalizeSearchWord(surfaceToken),
    normalizeSearchWord(lemmaCandidate ?? ""),
  ].join("::")
}

function translationRequestForWordbankResult(
  lemma: WordbankLemma,
  displayVariant: CORSearchVariant | null,
): { key: string; surfaceToken: string; lemmaCandidate: string | null; initialTranslation: string | null } | null {
  const existingTranslation = normalizeTranslationValue(displayVariant?.gloss)
    ?? normalizeTranslationValue(lemma.english_translation)
  if (existingTranslation) {
    const requestSurface = displayVariant?.form?.trim() || lemma.lemma
    const requestLemma = displayVariant?.lemma?.trim() || lemma.lemma
    return {
      key: buildTranslationKey(requestSurface, requestLemma),
      surfaceToken: requestSurface,
      lemmaCandidate: requestLemma,
      initialTranslation: existingTranslation,
    }
  }

  const requestSurface = displayVariant?.form?.trim() || lemma.lemma
  const requestLemma = displayVariant?.lemma?.trim() || lemma.lemma
  if (!requestSurface.trim()) {
    return null
  }
  return {
    key: buildTranslationKey(requestSurface, requestLemma),
    surfaceToken: requestSurface,
    lemmaCandidate: requestLemma,
    initialTranslation: null,
  }
}

function translationRequestForCorVariant(
  variant: CORSearchVariant,
): { key: string; surfaceToken: string; lemmaCandidate: string | null; initialTranslation: string | null } | null {
  const existingTranslation = normalizeTranslationValue(variant.gloss)
  if (existingTranslation) {
    return {
      key: buildTranslationKey(variant.form, variant.lemma),
      surfaceToken: variant.form,
      lemmaCandidate: variant.lemma,
      initialTranslation: existingTranslation,
    }
  }

  const requestSurface = variant.form.trim()
  if (!requestSurface) {
    return null
  }
  return {
    key: buildTranslationKey(requestSurface, variant.lemma),
    surfaceToken: requestSurface,
    lemmaCandidate: variant.lemma?.trim() || null,
    initialTranslation: null,
  }
}

export function useSidebarSearchTranslations({
  orderedWordbankResults,
  displayVariantBySavedLemma,
  corSearchVariantsToRender,
}: UseSidebarSearchTranslationsParams) {
  const [translationsByKey, setTranslationsByKey] = useState<Record<string, string | null>>({})
  const apiClient = useMemo(() => createApiClient({ backendUrl: BACKEND_URL }), [])
  const pendingTranslationKeysRef = useRef<Set<string>>(new Set())

  const translationRequests = useMemo(() => {
    const requests = new Map<string, { surfaceToken: string; lemmaCandidate: string | null; initialTranslation: string | null }>()

    for (const { lemma } of orderedWordbankResults) {
      const displayVariant = displayVariantBySavedLemma.get(normalizeSearchWord(lemma.lemma))?.variant ?? null
      const request = translationRequestForWordbankResult(lemma, displayVariant)
      if (!request) {
        continue
      }
      requests.set(request.key, {
        surfaceToken: request.surfaceToken,
        lemmaCandidate: request.lemmaCandidate,
        initialTranslation: request.initialTranslation,
      })
    }

    for (const { variant } of corSearchVariantsToRender) {
      const request = translationRequestForCorVariant(variant)
      if (!request) {
        continue
      }
      requests.set(request.key, {
        surfaceToken: request.surfaceToken,
        lemmaCandidate: request.lemmaCandidate,
        initialTranslation: request.initialTranslation,
      })
    }

    return requests
  }, [corSearchVariantsToRender, displayVariantBySavedLemma, orderedWordbankResults])

  useEffect(() => {
    const initialTranslations = [...translationRequests.entries()]
      .filter(([, request]) => request.initialTranslation !== null)
      .map(([key, request]) => [key, request.initialTranslation] as const)

    if (initialTranslations.length === 0) {
      return
    }

    setTranslationsByKey((current) => {
      const next = { ...current }
      let changed = false
      for (const [key, translation] of initialTranslations) {
        if (next[key] === translation) {
          continue
        }
        next[key] = translation
        changed = true
      }
      return changed ? next : current
    })
  }, [translationRequests])

  useEffect(() => {
    for (const [key, request] of translationRequests.entries()) {
      if (request.initialTranslation !== null || Object.hasOwn(translationsByKey, key) || pendingTranslationKeysRef.current.has(key)) {
        continue
      }

      pendingTranslationKeysRef.current.add(key)
      void (async () => {
        try {
          const payload = await apiClient.postJson<GenerateTranslationResponse>(
            "/api/wordbank/translation",
            {
              surface_token: request.surfaceToken,
              lemma_candidate: request.lemmaCandidate,
            },
            "Could not generate translation.",
          )
          setTranslationsByKey((current) => ({
            ...current,
            [key]: normalizeTranslationValue(payload.english_translation),
          }))
        } catch {
          setTranslationsByKey((current) => ({
            ...current,
            [key]: null,
          }))
        } finally {
          pendingTranslationKeysRef.current.delete(key)
        }
      })()
    }
  }, [apiClient, translationRequests, translationsByKey])

  function getWordbankTranslation(lemma: WordbankLemma, displayVariant: CORSearchVariant | null): string | null {
    const request = translationRequestForWordbankResult(lemma, displayVariant)
    if (!request) {
      return null
    }
    return translationsByKey[request.key] ?? null
  }

  function isWordbankTranslationLoading(lemma: WordbankLemma, displayVariant: CORSearchVariant | null): boolean {
    const request = translationRequestForWordbankResult(lemma, displayVariant)
    if (!request || request.initialTranslation !== null) {
      return false
    }
    return !Object.hasOwn(translationsByKey, request.key)
  }

  function getCorVariantTranslation(variant: CORSearchVariant): string | null {
    const request = translationRequestForCorVariant(variant)
    if (!request) {
      return null
    }
    return translationsByKey[request.key] ?? null
  }

  function isCorVariantTranslationLoading(variant: CORSearchVariant): boolean {
    const request = translationRequestForCorVariant(variant)
    if (!request || request.initialTranslation !== null) {
      return false
    }
    return !Object.hasOwn(translationsByKey, request.key)
  }

  return {
    getWordbankTranslation,
    isWordbankTranslationLoading,
    getCorVariantTranslation,
    isCorVariantTranslationLoading,
  }
}
