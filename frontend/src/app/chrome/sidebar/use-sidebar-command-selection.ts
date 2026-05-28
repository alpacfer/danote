import { useEffect, useMemo } from "react"

import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import type {
  CORSearchGroup,
  CORSearchVariant,
  SentenceSearchPreviewResponse,
  WordbankSearchItem,
} from "@/app/core"
import type { EnTranslatedCorResults, SearchModeSwitchSuggestion } from "@/app/chrome/sidebar/sidebar-search-types"
import type { SidebarPageItem } from "@/app/chrome/sidebar/sidebar-page-items"

function orderedCorVariants(
  orderedCorSearchGroups: CORSearchGroup[],
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>,
): CORSearchVariant[] {
  const variants: CORSearchVariant[] = []
  for (const group of orderedCorSearchGroups) {
    for (const item of corSearchVariantsToRender) {
      if (item.group === group) {
        variants.push(item.variant)
      }
    }
  }
  return variants
}

// Keep these two helpers byte-for-byte aligned with the corVariantItemValue
// / translatedEnCorVariantItemValue lambdas in app-sidebar.tsx so the cmdk
// `value` attribute on each rendered <CommandItem> matches the keyboard
// navigation list built here. Sense-fan-out variants get a `-sense-<key>`
// suffix; legacy variants stay on the original shape so existing tests still
// match.
export function corVariantSelectionValue(variant: CORSearchVariant): string {
  return variant.meaning_key
    ? `cor-variant-${variant.cor_id}-sense-${variant.meaning_key}`
    : `cor-variant-${variant.cor_id}`
}

export function translatedEnCorVariantSelectionValue(variant: CORSearchVariant): string {
  return variant.meaning_key
    ? `en-cor-${variant.lemma.toLowerCase()}-${variant.cor_id}-sense-${variant.meaning_key}`
    : `en-cor-${variant.lemma.toLowerCase()}-${variant.cor_id}`
}

export function useSidebarCommandSelection({
  activeEnTranslatedCorResults,
  commandSelectionOverride,
  corDidYouMean,
  corSearchVariantsToRender,
  isSearchOpen,
  isSentenceMode,
  matchingPageItems,
  orderedCorSearchGroups,
  orderedWordbankResults,
  sentenceSearchPreview,
  setCommandSelectionOverride,
  modeSwitchSuggestion,
  wordbankDidYouMean,
}: {
  activeEnTranslatedCorResults: EnTranslatedCorResults
  commandSelectionOverride: string
  corDidYouMean: string | null
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  isSearchOpen: boolean
  isSentenceMode: boolean
  matchingPageItems: SidebarPageItem[]
  orderedCorSearchGroups: CORSearchGroup[]
  orderedWordbankResults: WordbankSearchItem[]
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  setCommandSelectionOverride: (value: string) => void
  modeSwitchSuggestion: SearchModeSwitchSuggestion | null
  wordbankDidYouMean: string | null
}) {
  const orderedCorVariantsToRender = useMemo(() => {
    return orderedCorVariants(orderedCorSearchGroups, corSearchVariantsToRender)
  }, [corSearchVariantsToRender, orderedCorSearchGroups])

  const orderedCommandItemValues = useMemo(() => {
    const values: string[] = []
    const hasEnCommandResults = activeEnTranslatedCorResults.corSearchVariantsToRender.length > 0
      || activeEnTranslatedCorResults.fallbackEnPosGroups.length > 0
    if (isSentenceMode && sentenceSearchPreview) {
      const sentenceValues: string[] = []
      if (sentenceSearchPreview.is_multi_word_expression && sentenceSearchPreview.mwe_cor_match) {
        sentenceValues.push(`cor-variant-${sentenceSearchPreview.mwe_cor_match.cor_id}`)
      } else {
        sentenceValues.push("sentence-translation-result")
      }
      if (modeSwitchSuggestion) {
        sentenceValues.push(modeSwitchSuggestion.value)
      }
      return sentenceValues
    }
    if (isSentenceMode && modeSwitchSuggestion) {
      return [modeSwitchSuggestion.value]
    }
    const numericPage = matchingPageItems.find((page) => page.key === "page-numbers")
    if (numericPage) {
      values.push(numericPage.key)
    }
    if (!wordbankDidYouMean) {
      for (const item of orderedWordbankResults) {
        values.push(`wordbank-${savedWordbankResultKey(item)}`)
      }
    }
    if (!corDidYouMean && !hasEnCommandResults) {
      for (const variant of orderedCorVariantsToRender) {
        values.push(corVariantSelectionValue(variant))
      }
    }
    if (modeSwitchSuggestion) {
      values.push(modeSwitchSuggestion.value)
    }
    if (wordbankDidYouMean || corDidYouMean) {
      values.push("did-you-mean-suggestion")
    }
    if (wordbankDidYouMean) {
      for (const item of orderedWordbankResults) {
        values.push(`wordbank-${savedWordbankResultKey(item)}`)
      }
    }
    if (corDidYouMean) {
      for (const variant of orderedCorVariantsToRender) {
        values.push(corVariantSelectionValue(variant))
      }
    }
    for (const variant of activeEnTranslatedCorResults.corSearchVariantsToRender) {
      values.push(translatedEnCorVariantSelectionValue(variant.variant))
    }
    for (const group of activeEnTranslatedCorResults.fallbackEnPosGroups) {
      if (group.danish_translation) {
        values.push(`en-${group.danish_translation.toLowerCase()}-${group.lemma.toLowerCase()}-${group.pos_ud}`)
      }
    }
    for (const page of matchingPageItems) {
      if (page.key === "page-numbers") {
        continue
      }
      values.push(page.key)
    }
    return values
  }, [
    activeEnTranslatedCorResults,
    corDidYouMean,
    isSentenceMode,
    matchingPageItems,
    modeSwitchSuggestion,
    orderedCorVariantsToRender,
    orderedWordbankResults,
    sentenceSearchPreview,
    wordbankDidYouMean,
  ])

  const commandSelectionValue = useMemo(() => {
    if (commandSelectionOverride && orderedCommandItemValues.includes(commandSelectionOverride)) {
      return commandSelectionOverride
    }
    return orderedCommandItemValues[0] ?? ""
  }, [commandSelectionOverride, orderedCommandItemValues])

  useEffect(() => {
    if (!isSearchOpen) {
      return
    }

    const nextValue = orderedCommandItemValues[0] ?? ""
    if (!nextValue) {
      if (commandSelectionOverride) {
        setCommandSelectionOverride("")
      }
      return
    }

    if (isSentenceMode) {
      if (commandSelectionOverride !== nextValue) {
        setCommandSelectionOverride(nextValue)
      }
      return
    }

    const selectedModeSwitch = commandSelectionOverride.startsWith("switch-search-mode-")
    if (
      !commandSelectionOverride
      || !orderedCommandItemValues.includes(commandSelectionOverride)
      || (selectedModeSwitch && commandSelectionOverride !== nextValue)
    ) {
      setCommandSelectionOverride(nextValue)
    }
  }, [commandSelectionOverride, isSearchOpen, isSentenceMode, orderedCommandItemValues, setCommandSelectionOverride])

  return { commandSelectionValue }
}
