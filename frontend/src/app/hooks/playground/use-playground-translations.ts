import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  PHRASE_TRANSLATION_DELAY_MS,
  createApiClient,
  normalizePhraseKey,
  normalizeSearchWord,
  normalizeWordKey,
  translationKeysForToken,
  type AnalyzedToken,
  type GeneratePhraseTranslationResponse,
  type GenerateTranslationResponse,
} from "@/app/core"

type UsePlaygroundTranslationsParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
}

export function usePlaygroundTranslations({
  backendUrl,
  extractErrorMessage,
}: UsePlaygroundTranslationsParams) {
  const [generatedTranslationMap, setGeneratedTranslationMap] = useState<Record<string, string | null>>({})
  const [isGeneratingTranslation, setIsGeneratingTranslation] = useState(false)
  const [generateTranslationError, setGenerateTranslationError] = useState<string | null>(null)
  const [isGeneratingPhraseTranslation, setIsGeneratingPhraseTranslation] = useState(false)
  const [generatePhraseTranslationError, setGeneratePhraseTranslationError] = useState<string | null>(null)

  const phraseTranslationRequestKeyRef = useRef<string | null>(null)
  const phraseTranslationDelayTimeoutRef = useRef<number | null>(null)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const clearPhraseTranslationDelay = useCallback(() => {
    if (phraseTranslationDelayTimeoutRef.current !== null) {
      window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
      phraseTranslationDelayTimeoutRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      clearPhraseTranslationDelay()
    }
  }, [clearPhraseTranslationDelay])

  const rememberTranslation = useCallback((key: string, translation: string | null) => {
    if (!key) {
      return
    }
    setGeneratedTranslationMap((current) => ({ ...current, [key]: translation }))
  }, [])

  async function generateTranslationForToken(token: AnalyzedToken) {
    const sourceWord = normalizeSearchWord(token.normalized_token || token.surface_token)
    const requestSurface = normalizeSearchWord(token.normalized_token || token.surface_token)
    const requestLemma = normalizeSearchWord(token.matched_lemma ?? token.lemma_candidate ?? "") || null
    const tokenKeys = translationKeysForToken(token)
    const hasResolvedTranslation = tokenKeys.some((key) => {
      if (!Object.hasOwn(generatedTranslationMap, key)) {
        return false
      }
      return generatedTranslationMap[key] !== null
    })
    if (hasResolvedTranslation) {
      return
    }

    setIsGeneratingTranslation(true)
    setGenerateTranslationError(null)
    try {
      const payload = await apiClient.postJson<GenerateTranslationResponse>(
        "/api/wordbank/translation",
        {
          surface_token: requestSurface,
          lemma_candidate: requestLemma,
        },
        "Could not generate translation.",
      )
      const translation = payload.english_translation?.trim() || null

      const responseKey = normalizeWordKey(payload.source_word || sourceWord)

      setGeneratedTranslationMap((current) => {
        const next = { ...current }
        for (const key of [...tokenKeys, responseKey]) {
          if (!key) {
            continue
          }
          if (next[key] === undefined || (next[key] === null && translation !== null)) {
            next[key] = translation
          }
        }
        return next
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate translation."
      setGenerateTranslationError(message)
      void error
    } finally {
      setIsGeneratingTranslation(false)
    }
  }

  async function generateTranslationForPhrase(selectedText: string) {
    const phraseKey = normalizePhraseKey(selectedText)
    if (!phraseKey || Object.hasOwn(generatedTranslationMap, phraseKey)) {
      setIsGeneratingPhraseTranslation(false)
      return
    }

    clearPhraseTranslationDelay()

    phraseTranslationRequestKeyRef.current = phraseKey
    setIsGeneratingPhraseTranslation(true)
    setGeneratePhraseTranslationError(null)
    phraseTranslationDelayTimeoutRef.current = window.setTimeout(() => {
      phraseTranslationDelayTimeoutRef.current = null
      void (async () => {
        try {
          const payload = await apiClient.postJson<GeneratePhraseTranslationResponse>(
            "/api/wordbank/phrase-translation",
            {
              source_text: selectedText,
            },
            "Could not generate phrase translation.",
          )
          const responseKey = normalizePhraseKey(payload.source_text || selectedText)
          const translation = payload.english_translation?.trim() || null

          setGeneratedTranslationMap((current) => {
            const next = { ...current }
            if (responseKey) {
              next[responseKey] = translation
            }
            if (phraseKey) {
              next[phraseKey] = translation
            }
            return next
          })
        } catch (error) {
          if (phraseTranslationRequestKeyRef.current === phraseKey) {
            const message = error instanceof Error ? error.message : "Could not generate phrase translation."
            setGeneratePhraseTranslationError(message)
          }
          void error
        } finally {
          if (phraseTranslationRequestKeyRef.current === phraseKey) {
            setIsGeneratingPhraseTranslation(false)
          }
        }
      })()
    }, PHRASE_TRANSLATION_DELAY_MS)
  }

  function clearTransientTranslationState() {
    resetPhraseTranslationProgress()
    setGeneratePhraseTranslationError(null)
    setGenerateTranslationError(null)
  }

  function resetPhraseTranslationProgress() {
    clearPhraseTranslationDelay()
    setGeneratePhraseTranslationError(null)
    setIsGeneratingPhraseTranslation(false)
  }

  return {
    generatedTranslationMap,
    setGeneratedTranslationMap,
    isGeneratingTranslation,
    generateTranslationError,
    isGeneratingPhraseTranslation,
    generatePhraseTranslationError,
    rememberTranslation,
    generateTranslationForToken,
    generateTranslationForPhrase,
    clearTransientTranslationState,
    resetPhraseTranslationProgress,
  }
}
