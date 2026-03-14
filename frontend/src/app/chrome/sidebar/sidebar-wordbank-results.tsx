import { Eye, Plus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import {
  badgesForSavedForm,
  badgesFromGramRaw,
  corSecondaryBadgeClass,
  glossDisplayForVariant,
  lemmaDisplayForVariant,
  lemmaTranslationForVariant,
  lemmaTranslationWithGloss,
  normalizeSearchWord,
  posBadgeClass,
  type SearchSaveSeed,
  type CORSearchGroup,
  type CORSearchVariant,
  type SearchFeedbackContext,
  type WordbankSearchItem,
} from "@/app/core"
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"

type SidebarWordbankResultsProps = {
  orderedWordbankResults: WordbankSearchItem[]
  displayVariantBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  addVariationBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  exactSavedVariationKeySet: Set<string>
  normalizedQuery: string
  wordbankItemValue: (item: WordbankSearchItem) => string
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onCloseSearch: () => void
}

export function SidebarWordbankResults({
  orderedWordbankResults,
  displayVariantBySavedResult,
  addVariationBySavedResult,
  exactSavedVariationKeySet,
  normalizedQuery,
  wordbankItemValue,
  onAddWordFromSearch,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onCloseSearch,
}: SidebarWordbankResultsProps) {
  return (
    <>
      {orderedWordbankResults.map((result) => {
        const resultKey = savedWordbankResultKey(result)
        return (
          <CommandItem
            key={`search-lemma-${resultKey}`}
            value={wordbankItemValue(result)}
            onSelect={() => {
              const addVariation = addVariationBySavedResult.get(resultKey)
              const isExactSavedVariation = exactSavedVariationKeySet.has(resultKey)
              if (addVariation && !isExactSavedVariation) {
                void (async () => {
                  const addedLemma = await onAddWordFromSearch(
                    addVariation.variant.form,
                    addVariation.variant.lemma,
                    {
                      rawToken: normalizedQuery,
                      predictedStatus: "variation",
                      suggestionsShown: [`${addVariation.variant.lemma}:${addVariation.variant.gram_raw}`],
                    },
                    {
                      posTag: addVariation.variant.pos_tag ?? null,
                      morphology: addVariation.variant.morphology ?? null,
                      corId: addVariation.variant.cor_id,
                    },
                    {
                      lemma: addVariation.variant.lemma,
                      surface: addVariation.variant.form,
                      cor_id: addVariation.variant.cor_id,
                      cor_lemma_idx: addVariation.variant.lemma_idx,
                      meaning_key: result.meaning_key ?? result.lemma,
                      gloss: result.gloss ?? null,
                      english_translation: result.english_translation ?? null,
                      pos_tag: addVariation.variant.pos_tag ?? result.pos_tag ?? null,
                      morphology: addVariation.variant.morphology ?? result.morphology ?? null,
                      target_meaning_id: result.meaning_id ?? null,
                    },
                  )
                  if (addedLemma) {
                    onCloseSearch()
                  }
                })()
                return
              }
              if (typeof result.meaning_id === "number") {
                onOpenWordbankMeaning(result.lemma, result.meaning_id)
              } else {
                onOpenWordbankLemma(result.lemma)
              }
              onCloseSearch()
            }}
            className="flex items-center justify-between gap-3"
          >
            <div className="flex min-w-0 flex-col items-start gap-0.5">
              {(() => {
                const displayVariant = displayVariantBySavedResult.get(resultKey)?.variant ?? null
                const lemmaKey = normalizeSearchWord(result.lemma)
                const matchedSurface = result.match_surface?.trim() || ""
                const matchedSurfaceKey = normalizeSearchWord(matchedSurface)
                const showMatchedSurface = Boolean(
                  matchedSurface
                  && matchedSurfaceKey === normalizedQuery
                  && matchedSurfaceKey !== lemmaKey,
                )
                const showExactSavedLink = Boolean(
                  !displayVariant
                  && matchedSurface
                  && matchedSurfaceKey === normalizedQuery,
                )
                const displayTitle = displayVariant?.form?.trim()
                  || (showMatchedSurface ? matchedSurface : "")
                  || result.display_lemma?.trim()
                  || result.lemma
                const linkedLemmaDisplay = displayVariant
                  ? (lemmaDisplayForVariant(displayVariant) ?? result.display_lemma?.trim() ?? result.lemma)
                  : (showMatchedSurface || showExactSavedLink)
                    ? (result.display_lemma?.trim() || result.lemma)
                    : null
                const savedTranslationLine = lemmaTranslationWithGloss(
                  result.english_translation ?? null,
                  result.gloss_translation ?? null,
                )
                const linkedLemmaTranslation = displayVariant
                  ? (lemmaTranslationForVariant(displayVariant) ?? savedTranslationLine)
                  : (showMatchedSurface || showExactSavedLink)
                    ? savedTranslationLine
                    : null
                const detailLine = displayVariant
                  ? glossDisplayForVariant(displayVariant)
                  : (showMatchedSurface || showExactSavedLink)
                    ? null
                    : savedTranslationLine
                const badges = displayVariant
                  ? badgesFromGramRaw(displayVariant.gram_raw)
                  : badgesForSavedForm({
                    pos_tag: result.pos_tag ?? null,
                    morphology: result.morphology ?? null,
                  })

                return (
                  <>
                    <span>
                      <strong className="font-semibold">{displayTitle}</strong>
                      {linkedLemmaDisplay ? (
                        <span className="text-muted-foreground text-xs">
                          {" "}from <em>{linkedLemmaDisplay}</em>
                          {linkedLemmaTranslation ? ` (${linkedLemmaTranslation})` : ""}
                        </span>
                      ) : null}
                    </span>
                    {detailLine ? (
                      <span className="text-muted-foreground text-xs leading-4">{detailLine}</span>
                    ) : null}
                    {badges.length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {badges.map((badge) => (
                          <Badge
                            key={`search-wordbank-${resultKey}-badge-${badge.label}`}
                            variant={badge.tone === "primary" ? "default" : "secondary"}
                            className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(displayVariant?.pos_tag ?? result.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                            data-testid="search-metadata-badge"
                          >
                            {badge.label}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </>
                )
              })()}
            </div>
            {(() => {
              const linkedVariation = addVariationBySavedResult.get(resultKey)
              const isExactSavedVariation = exactSavedVariationKeySet.has(resultKey)
              if (linkedVariation && !isExactSavedVariation) {
                return (
                  <span className="text-muted-foreground flex items-center gap-1 text-xs font-semibold">
                    <span data-testid="search-add-variation-label">variation</span>
                    <Plus data-testid="search-add-icon" className="size-4 shrink-0" />
                  </span>
                )
              }
              return <Eye data-testid="search-open-icon" className="text-muted-foreground size-4 shrink-0" />
            })()}
          </CommandItem>
        )
      })}
    </>
  )
}
