import { useMemo } from "react"

import {
  isLowConfidencePosTag,
  normalizePhraseKey,
  normalizeWordKey,
  posBadgeClass,
  secondaryTagsForPos,
  translationKeysForToken,
  type AnalyzedToken,
  type DiscoveredTokenMemory,
  type HighlightPopoverState,
  type PhrasePopoverState,
  type ResolveQueryResponse,
  type SentencebankSentence,
} from "@/app/core"

type UsePopoverDisplayDataParams = {
  highlightPopover: HighlightPopoverState
  phrasePopover: PhrasePopoverState
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  popoverEnrichment: ResolveQueryResponse | null
  isGeneratingTranslation: boolean
  generateTranslationError: string | null
  sentences: SentencebankSentence[]
}

export function usePopoverDisplayData({
  highlightPopover,
  phrasePopover,
  tokens,
  discoveredTokenMetadata,
  generatedTranslationMap,
  popoverEnrichment,
  isGeneratingTranslation,
  generateTranslationError,
  sentences,
}: UsePopoverDisplayDataParams) {
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

  const popoverLemmaText = useMemo(() => {
    if (!popoverDisplayToken) {
      return null
    }
    return (popoverDisplayToken.matched_lemma ?? popoverDisplayToken.lemma_candidate ?? "").trim() || null
  }, [popoverDisplayToken])

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

  const popoverIsNoun = popoverDisplayToken?.pos_tag === "NOUN"
  const popoverIsVerbLike = popoverDisplayToken?.pos_tag === "VERB" || popoverDisplayToken?.pos_tag === "AUX"
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

  return {
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
  }
}
