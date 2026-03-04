import { useEffect, useMemo, useRef, useState } from "react"

import {
  PHRASE_TRANSLATION_DELAY_MS,
  POPOVER_ENRICH_CACHE_TTL_MS,
  hasMultipleWords,
  isLowConfidencePosTag,
  normalizePhraseKey,
  normalizeSearchWord,
  normalizeWordKey,
  posBadgeClass,
  preferredPopoverSide,
  secondaryTagsForPos,
  translationKeysForToken,
  type AnalyzedToken,
  type DiscoveredTokenMemory,
  type GeneratePhraseTranslationResponse,
  type GenerateTranslationResponse,
  type HighlightPopoverState,
  type PhrasePopoverState,
  type ResolveQueryResponse,
  type SentencebankSentence,
} from "@/app/core"

type UsePlaygroundPopoversParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  sentences: SentencebankSentence[]
}

type EditorSelectionPayload = {
  selectedText: string
  left: number
  lineTop: number
  lineBottom: number
} | null

export function usePlaygroundPopovers({
  backendUrl,
  extractErrorMessage,
  tokens,
  discoveredTokenMetadata,
  sentences,
}: UsePlaygroundPopoversParams) {
  const [highlightPopover, setHighlightPopover] = useState<HighlightPopoverState>({
    open: false,
    left: 0,
    lineTop: 0,
    lineBottom: 0,
    side: "bottom",
    tokenIndex: null,
  })
  const [phrasePopover, setPhrasePopover] = useState<PhrasePopoverState>({
    open: false,
    left: 0,
    lineTop: 0,
    lineBottom: 0,
    side: "bottom",
    selectedText: "",
  })
  const [popoverEnrichment, setPopoverEnrichment] = useState<ResolveQueryResponse | null>(null)
  const [generatedTranslationMap, setGeneratedTranslationMap] = useState<Record<string, string | null>>({})
  const [isGeneratingTranslation, setIsGeneratingTranslation] = useState(false)
  const [generateTranslationError, setGenerateTranslationError] = useState<string | null>(null)
  const [isGeneratingPhraseTranslation, setIsGeneratingPhraseTranslation] = useState(false)
  const [generatePhraseTranslationError, setGeneratePhraseTranslationError] = useState<string | null>(null)

  const phraseTranslationRequestKeyRef = useRef<string | null>(null)
  const phraseTranslationDelayTimeoutRef = useRef<number | null>(null)
  const popoverEnrichmentCacheRef = useRef<Map<string, { payload: ResolveQueryResponse; cachedAt: number }>>(new Map())

  const popoverToken = useMemo(() => {
    if (highlightPopover.tokenIndex === null) {
      return null
    }
    return tokens[highlightPopover.tokenIndex] ?? null
  }, [highlightPopover.tokenIndex, tokens])

  const popoverDisplayToken = useMemo(() => {
    if (!popoverToken) {
      return null
    }
    const key = normalizeWordKey(popoverToken.normalized_token || popoverToken.surface_token)
    const remembered = discoveredTokenMetadata[key]
    if (!remembered) {
      return popoverToken
    }

    if (!isLowConfidencePosTag(popoverToken.pos_tag)) {
      const tokenPos = popoverToken.pos_tag
      if (!tokenPos) {
        return popoverToken
      }
      const rememberedForPos = remembered.byPos[tokenPos]
      if (!rememberedForPos) {
        return popoverToken
      }

      return {
        ...popoverToken,
        morphology: popoverToken.morphology ?? rememberedForPos.morphology,
        lemma_candidate: popoverToken.lemma_candidate ?? rememberedForPos.lemma,
        lemma: rememberedForPos.lemma,
      }
    }

    return {
      ...popoverToken,
      pos_tag: remembered.latest.pos_tag,
      morphology: popoverToken.morphology ?? remembered.latest.morphology,
      lemma_candidate: popoverToken.lemma_candidate ?? remembered.latest.lemma,
      lemma: remembered.latest.lemma,
    }
  }, [discoveredTokenMetadata, popoverToken])

  const popoverPrimaryAction = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    const tokenActions = popoverEnrichment?.word_actions ?? popoverDisplayToken.word_actions ?? []
    return tokenActions[0] ?? null
  }, [popoverDisplayToken, popoverEnrichment?.word_actions])

  const popoverTranslation = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    for (const key of translationKeysForToken(popoverDisplayToken)) {
      if (Object.hasOwn(generatedTranslationMap, key)) {
        return generatedTranslationMap[key] ?? null
      }
    }
    return null
  }, [generatedTranslationMap, popoverDisplayToken])

  const popoverLemma = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    return popoverDisplayToken.matched_lemma ?? popoverDisplayToken.lemma_candidate ?? null
  }, [popoverDisplayToken])

  const popoverIsNoun = popoverDisplayToken?.pos_tag === "NOUN"
  const popoverIsVerbLike = popoverDisplayToken?.pos_tag === "VERB" || popoverDisplayToken?.pos_tag === "AUX"
  const popoverLemmaText = popoverLemma?.trim() ?? null
  const popoverSurfaceText = popoverDisplayToken?.surface_token?.trim() ?? null
  const showPopoverLemma = Boolean(
    popoverLemmaText &&
    popoverSurfaceText &&
    popoverLemmaText.toLocaleLowerCase("da-DK") !== popoverSurfaceText.toLocaleLowerCase("da-DK"),
  )
  const popoverMetadataBadges = useMemo(() => {
    if (!popoverDisplayToken) {
      return []
    }
    return [
      popoverDisplayToken.pos_tag
        ? {
          key: `popover-meta-pos-${popoverDisplayToken.pos_tag}`,
          label: popoverDisplayToken.pos_tag,
          className: posBadgeClass(popoverDisplayToken.pos_tag),
        }
        : null,
      ...secondaryTagsForPos(popoverDisplayToken.pos_tag, popoverDisplayToken.morphology).map((value) => ({
        key: `popover-meta-tag-${value}`,
        label: value,
        className: "",
      })),
    ].filter((value): value is { key: string; label: string; className: string } => Boolean(value))
  }, [popoverDisplayToken])
  const showTranslationSkeleton = isGeneratingTranslation || (
    (popoverIsNoun || popoverIsVerbLike) &&
    (!popoverTranslation || Boolean(generateTranslationError))
  )
  const phraseTranslation = useMemo(() => {
    const phraseKey = normalizePhraseKey(phrasePopover.selectedText)
    if (!phraseKey || !Object.hasOwn(generatedTranslationMap, phraseKey)) {
      return null
    }
    return generatedTranslationMap[phraseKey] ?? null
  }, [generatedTranslationMap, phrasePopover.selectedText])
  const isSelectedPhraseSaved = useMemo(() => {
    const phraseKey = normalizePhraseKey(phrasePopover.selectedText)
    if (!phraseKey) {
      return false
    }
    return sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === phraseKey)
  }, [phrasePopover.selectedText, sentences])

  useEffect(() => {
    if (!highlightPopover.open) {
      return
    }
    if (highlightPopover.tokenIndex === null || !tokens[highlightPopover.tokenIndex]) {
      setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
    }
  }, [highlightPopover.open, highlightPopover.tokenIndex, tokens])

  useEffect(() => {
    if (!highlightPopover.open || !popoverDisplayToken) {
      setPopoverEnrichment(null)
      return
    }

    const tokenValue = normalizeSearchWord(popoverDisplayToken.normalized_token || popoverDisplayToken.surface_token)
    if (!tokenValue) {
      setPopoverEnrichment(null)
      return
    }

    const cacheKey = normalizeWordKey(tokenValue)
    const cached = popoverEnrichmentCacheRef.current.get(cacheKey)
    if (cached && Date.now() - cached.cachedAt < POPOVER_ENRICH_CACHE_TTL_MS) {
      setPopoverEnrichment(cached.payload)
      if (cached.payload.da_to_en_translation) {
        setGeneratedTranslationMap((current) => ({
          ...current,
          [cacheKey]: cached.payload.da_to_en_translation,
        }))
      }
      return
    }

    let cancelled = false
    const controller = new AbortController()

    void (async () => {
      try {
        const response = await fetch(`${backendUrl}/api/analyze/enrich-token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: tokenValue,
            include_translations: true,
            include_language_detection: true,
          }),
          signal: controller.signal,
        })
        if (!response.ok) {
          return
        }

        const payload = (await response.json()) as ResolveQueryResponse
        if (cancelled) {
          return
        }
        popoverEnrichmentCacheRef.current.set(cacheKey, {
          payload,
          cachedAt: Date.now(),
        })
        setPopoverEnrichment(payload)
        if (payload.da_to_en_translation) {
          setGeneratedTranslationMap((current) => ({
            ...current,
            [cacheKey]: payload.da_to_en_translation,
          }))
        }
      } catch {
        // ignore enrichment failures for popover fallback behavior
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [backendUrl, highlightPopover.open, popoverDisplayToken])

  useEffect(() => {
    return () => {
      if (phraseTranslationDelayTimeoutRef.current !== null) {
        window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
      }
    }
  }, [])

  function clearPhraseTranslationDelay() {
    if (phraseTranslationDelayTimeoutRef.current !== null) {
      window.clearTimeout(phraseTranslationDelayTimeoutRef.current)
      phraseTranslationDelayTimeoutRef.current = null
    }
  }

  function closeHighlightPopover() {
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
  }

  function closePhrasePopover() {
    setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
  }

  function clearTransientState() {
    setGeneratePhraseTranslationError(null)
    setGenerateTranslationError(null)
    closeHighlightPopover()
    closePhrasePopover()
    clearPhraseTranslationDelay()
    setIsGeneratingPhraseTranslation(false)
  }

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
      let payload: GenerateTranslationResponse | null = null
      let translation: string | null = null
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const response = await fetch(`${backendUrl}/api/wordbank/translation`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            surface_token: requestSurface,
            lemma_candidate: requestLemma,
          }),
        })
        if (!response.ok) {
          const message = await extractErrorMessage(
            response,
            `Translation request failed with status ${response.status}`,
          )
          throw new Error(message)
        }

        const nextPayload = (await response.json()) as GenerateTranslationResponse
        const nextTranslation = nextPayload.english_translation?.trim() || null
        payload = nextPayload
        translation = nextTranslation
        if (nextTranslation) {
          break
        }
      }

      if (!payload) {
        return
      }

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
          const response = await fetch(`${backendUrl}/api/wordbank/phrase-translation`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              source_text: selectedText,
            }),
          })
          if (!response.ok) {
            const message = await extractErrorMessage(
              response,
              `Phrase translation request failed with status ${response.status}`,
            )
            throw new Error(message)
          }

          const payload = (await response.json()) as GeneratePhraseTranslationResponse
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

  function openHighlightPopover(tokenIndex: number, left: number, lineTop: number, lineBottom: number) {
    const token = tokens[tokenIndex]
    if (!token || token.classification === "typo_likely" || token.pos_tag === "PROPN" || token.pos_tag === "NUM") {
      return
    }

    const side = preferredPopoverSide(lineTop, lineBottom)
    setHighlightPopover({ open: true, tokenIndex, left, lineTop, lineBottom, side })
    setPhrasePopover((current) => ({ ...current, open: false }))
    void generateTranslationForToken(token)
  }

  function handleEditorSelection(payload: EditorSelectionPayload) {
    if (!payload) {
      clearPhraseTranslationDelay()
      closePhrasePopover()
      setGeneratePhraseTranslationError(null)
      setIsGeneratingPhraseTranslation(false)
      return
    }

    const normalizedSelection = payload.selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      clearPhraseTranslationDelay()
      closePhrasePopover()
      setGeneratePhraseTranslationError(null)
      setIsGeneratingPhraseTranslation(false)
      return
    }

    const side = preferredPopoverSide(payload.lineTop, payload.lineBottom)
    setPhrasePopover({
      open: true,
      selectedText: normalizedSelection,
      left: payload.left,
      lineTop: payload.lineTop,
      lineBottom: payload.lineBottom,
      side,
    })
    closeHighlightPopover()
    void generateTranslationForPhrase(normalizedSelection)
  }

  function handlePhrasePopoverOpenChange(open: boolean) {
    setPhrasePopover((current) => ({
      ...current,
      open,
      selectedText: open ? current.selectedText : "",
    }))
    if (!open) {
      setGeneratePhraseTranslationError(null)
    }
  }

  function handleHighlightPopoverOpenChange(open: boolean) {
    setHighlightPopover((current) => ({
      ...current,
      open,
      tokenIndex: open ? current.tokenIndex : null,
    }))
  }

  function openWordbankFromPrimaryAction() {
    return popoverPrimaryAction?.lemma ?? null
  }

  return {
    highlightPopover,
    phrasePopover,
    generatedTranslationMap,
    setGeneratedTranslationMap,
    isGeneratingPhraseTranslation,
    generatePhraseTranslationError,
    isGeneratingTranslation,
    generateTranslationError,
    popoverDisplayToken,
    popoverPrimaryAction,
    popoverTranslation,
    popoverLemmaText,
    showPopoverLemma,
    popoverMetadataBadges,
    popoverIsNoun,
    popoverIsVerbLike,
    showTranslationSkeleton,
    phraseTranslation,
    isSelectedPhraseSaved,
    clearTransientState,
    closeHighlightPopover,
    handlePhrasePopoverOpenChange,
    handleHighlightPopoverOpenChange,
    openHighlightPopover,
    handleEditorSelection,
    openWordbankFromPrimaryAction,
  }
}
