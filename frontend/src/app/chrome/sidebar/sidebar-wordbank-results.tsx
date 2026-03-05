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
  normalizeSearchWord,
  posBadgeClass,
  type CORSearchGroup,
  type CORSearchVariant,
  type SearchFeedbackContext,
  type WordbankLemma,
} from "@/app/core"

type WordbankResult = {
  lemma: WordbankLemma
  matchSurface: string | null
}

type SidebarWordbankResultsProps = {
  orderedWordbankResults: WordbankResult[]
  displayVariantBySavedLemma: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  addVariationBySavedLemma: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  exactSavedVariationLemmaKeySet: Set<string>
  normalizedQuery: string
  wordbankItemValue: (lemma: WordbankLemma) => string
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ) => Promise<string | null>
  onOpenWordbankLemma: (lemma: string) => void
  onCloseSearch: () => void
}

export function SidebarWordbankResults({
  orderedWordbankResults,
  displayVariantBySavedLemma,
  addVariationBySavedLemma,
  exactSavedVariationLemmaKeySet,
  normalizedQuery,
  wordbankItemValue,
  onAddWordFromSearch,
  onOpenWordbankLemma,
  onCloseSearch,
}: SidebarWordbankResultsProps) {
  return (
    <>
      {orderedWordbankResults.map(({ lemma }) => (
        <CommandItem
          key={`search-lemma-${lemma.lemma}`}
          value={wordbankItemValue(lemma)}
          onSelect={() => {
            const lemmaKey = normalizeSearchWord(lemma.lemma)
            const addVariation = addVariationBySavedLemma.get(lemmaKey)
            const isExactSavedVariation = exactSavedVariationLemmaKeySet.has(lemmaKey)
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
                  },
                )
                if (addedLemma) {
                  onCloseSearch()
                }
              })()
              return
            }
            onOpenWordbankLemma(lemma.lemma)
            onCloseSearch()
          }}
          className="flex items-center justify-between gap-3"
        >
          <div className="flex min-w-0 flex-col items-start gap-0.5">
            {(() => {
              const displayVariant = displayVariantBySavedLemma.get(normalizeSearchWord(lemma.lemma))?.variant ?? null
              const displayTitle = displayVariant?.form?.trim() || lemma.display_lemma?.trim() || lemma.lemma
              const displayVariantFormKey = normalizeSearchWord(displayVariant?.form ?? "")
              const displayVariantLemmaKey = normalizeSearchWord(displayVariant?.lemma ?? "")
              const showLinkedLemma = Boolean(
                displayVariant && displayVariantLemmaKey && displayVariantFormKey && displayVariantLemmaKey !== displayVariantFormKey,
              )
              const linkedLemmaDisplay = showLinkedLemma && displayVariant ? lemmaDisplayForVariant(displayVariant) : null
              const linkedLemmaTranslation = showLinkedLemma && displayVariant
                ? lemmaTranslationForVariant(displayVariant)
                : null
              const detailLine = displayVariant
                ? (glossDisplayForVariant(displayVariant) ?? (lemma.english_translation?.trim() || "No translation available."))
                : (lemma.english_translation?.trim() || "No translation available.")
              const badges = displayVariant
                ? badgesFromGramRaw(displayVariant.gram_raw)
                : badgesForSavedForm({
                  pos_tag: lemma.pos_tag ?? null,
                  morphology: lemma.morphology ?? null,
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
                  <span className="text-muted-foreground text-xs">{detailLine}</span>
                  {badges.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {badges.map((badge) => (
                        <Badge
                          key={`search-wordbank-${lemma.lemma}-badge-${badge.label}`}
                          variant={badge.tone === "primary" ? "default" : "secondary"}
                          className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(displayVariant?.pos_tag ?? lemma.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
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
            const lemmaKey = normalizeSearchWord(lemma.lemma)
            const linkedVariation = addVariationBySavedLemma.get(lemmaKey)
            const isExactSavedVariation = exactSavedVariationLemmaKeySet.has(lemmaKey)
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
      ))}
    </>
  )
}
