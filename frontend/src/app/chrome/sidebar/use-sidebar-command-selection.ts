import { useEffect, useMemo } from "react"

import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import type {
  CORSearchGroup,
  CORSearchVariant,
  SentenceSearchPreviewResponse,
  WordbankSearchItem,
} from "@/app/core"
import type { EnTranslatedCorResults } from "@/app/chrome/sidebar/sidebar-search-types"
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
      return ["sentence-translation-result"]
    }
    if (!wordbankDidYouMean) {
      for (const item of orderedWordbankResults) {
        values.push(`wordbank-${savedWordbankResultKey(item)}`)
      }
    }
    if (!corDidYouMean && !hasEnCommandResults) {
      for (const variant of orderedCorVariantsToRender) {
        values.push(`cor-variant-${variant.cor_id}`)
      }
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
        values.push(`cor-variant-${variant.cor_id}`)
      }
    }
    for (const variant of activeEnTranslatedCorResults.corSearchVariantsToRender) {
      values.push(`en-cor-${variant.group.lemma.toLowerCase()}-${variant.variant.cor_id}`)
    }
    for (const group of activeEnTranslatedCorResults.fallbackEnPosGroups) {
      if (group.danish_translation) {
        values.push(`en-${group.danish_translation.toLowerCase()}-${group.lemma.toLowerCase()}-${group.pos_ud}`)
      }
    }
    for (const page of matchingPageItems) {
      values.push(page.key)
    }
    return values
  }, [
    activeEnTranslatedCorResults,
    corDidYouMean,
    isSentenceMode,
    matchingPageItems,
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

    if (!commandSelectionOverride || !orderedCommandItemValues.includes(commandSelectionOverride)) {
      setCommandSelectionOverride(nextValue)
    }
  }, [commandSelectionOverride, isSearchOpen, isSentenceMode, orderedCommandItemValues, setCommandSelectionOverride])

  return { commandSelectionValue }
}
