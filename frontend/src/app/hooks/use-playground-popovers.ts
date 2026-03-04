import { useMemo, useState } from "react"

import {
  hasMultipleWords,
  preferredPopoverSide,
  type AnalyzedToken,
  type DiscoveredTokenMemory,
  type HighlightPopoverState,
  type PhrasePopoverState,
  type SentencebankSentence,
} from "@/app/core"

import { usePopoverDisplayData } from "./playground/use-popover-display-data"
import { usePopoverEnrichment } from "./playground/use-popover-enrichment"
import { usePlaygroundTranslations } from "./playground/use-playground-translations"

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
  const {
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
  } = usePlaygroundTranslations({
    backendUrl,
    extractErrorMessage,
  })

  const resolvedHighlightPopover = useMemo(() => {
    if (!highlightPopover.open) {
      return highlightPopover
    }
    if (highlightPopover.tokenIndex === null || !tokens[highlightPopover.tokenIndex]) {
      return { ...highlightPopover, open: false, tokenIndex: null }
    }
    return highlightPopover
  }, [highlightPopover, tokens])

  const provisionalDisplayToken =
    resolvedHighlightPopover.tokenIndex !== null ? (tokens[resolvedHighlightPopover.tokenIndex] ?? null) : null

  const { popoverEnrichment } = usePopoverEnrichment({
    backendUrl,
    isHighlightPopoverOpen: resolvedHighlightPopover.open,
    popoverDisplayToken: provisionalDisplayToken,
    rememberTranslation,
  })

  const {
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
  } = usePopoverDisplayData({
    highlightPopover: resolvedHighlightPopover,
    phrasePopover,
    tokens,
    discoveredTokenMetadata,
    generatedTranslationMap,
    popoverEnrichment,
    isGeneratingTranslation,
    generateTranslationError,
    sentences,
  })

  function closeHighlightPopover() {
    setHighlightPopover((current) => ({ ...current, open: false, tokenIndex: null }))
  }

  function closePhrasePopover() {
    setPhrasePopover((current) => ({ ...current, open: false, selectedText: "" }))
  }

  function clearTransientState() {
    clearTransientTranslationState()
    closeHighlightPopover()
    closePhrasePopover()
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
      closePhrasePopover()
      resetPhraseTranslationProgress()
      return
    }

    const normalizedSelection = payload.selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      closePhrasePopover()
      resetPhraseTranslationProgress()
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
      resetPhraseTranslationProgress()
    }
  }

  function handleHighlightPopoverOpenChange(open: boolean) {
    setHighlightPopover((current) => ({
      ...current,
      open,
      tokenIndex: open ? current.tokenIndex : null,
    }))
  }

  return {
    highlightPopover: resolvedHighlightPopover,
    phrasePopover,
    generatedTranslationMap,
    setGeneratedTranslationMap,
    isGeneratingPhraseTranslation,
    generatePhraseTranslationError,
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
  }
}
