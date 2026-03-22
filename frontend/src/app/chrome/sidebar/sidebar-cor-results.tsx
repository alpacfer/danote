import { Plus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import {
  badgesFromGramRaw,
  corSecondaryBadgeClass,
  glossDisplayForVariant,
  lemmaDisplayForVariant,
  lemmaTranslationForVariant,
  saveableTranslationForVariant,
  posBadgeClass,
  type SearchSaveSeed,
  type CORSearchGroup,
  type CORSearchVariant,
  type SearchFeedbackContext,
} from "@/app/core"

type GroupedVariant = {
  group: CORSearchGroup
  variant: CORSearchVariant
}

type SidebarCorResultsProps = {
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: GroupedVariant[]
  variationCandidateCorIdSet: Set<string>
  normalizedQuery: string
  corVariantItemValue: (variant: CORSearchVariant) => string
  isTranslationsLoading: boolean
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
  onCloseSearch: () => void
}

const searchTranslationSkeletonClassName = "bg-accent group-data-[selected=true]/search-item:bg-accent-foreground/20"

export function SidebarCorResults({
  orderedCorSearchGroups,
  corSearchVariantsToRender,
  variationCandidateCorIdSet,
  normalizedQuery,
  corVariantItemValue,
  isTranslationsLoading,
  onAddWordFromSearch,
  onCloseSearch,
}: SidebarCorResultsProps) {
  return (
    <>
      {orderedCorSearchGroups.map((group, groupIndex) => (
        <div
          key={`cor-group-${group.lemma}-${group.gloss ?? ""}-${group.pos_tag ?? ""}-${groupIndex}`}
          className="mt-1 first:mt-0"
        >
          {corSearchVariantsToRender
            .filter((item) => item.group === group)
            .map(({ variant }) => {
              const isVariationAdd = variationCandidateCorIdSet.has(variant.cor_id)
              const detailLine = glossDisplayForVariant(variant)
              const lemmaDisplay = lemmaDisplayForVariant(variant)
              const lemmaTranslation = lemmaTranslationForVariant(variant)
              const saveableTranslation = saveableTranslationForVariant(variant)
              const hasGloss = Boolean(variant.gloss?.trim())
              const isSaveBlocked = isTranslationsLoading || !saveableTranslation
              const saveBlockedReason = !isTranslationsLoading && !saveableTranslation
                ? "Translation required before saving."
                : null
              return (
                <CommandItem
                  key={`cor-variant-${variant.cor_id}`}
                  value={corVariantItemValue(variant)}
                  disabled={isSaveBlocked}
                  onSelect={() => {
                    if (saveBlockedReason) {
                      return
                    }
                    void (async () => {
                      const addedLemma = await onAddWordFromSearch(
                        variant.form,
                        variant.lemma,
                        {
                          rawToken: normalizedQuery,
                          predictedStatus: isVariationAdd ? "variation" : "new",
                          suggestionsShown: [`${variant.lemma}:${variant.gram_raw}`],
                        },
                        {
                          posTag: variant.pos_tag ?? null,
                          morphology: variant.morphology ?? null,
                          corId: variant.cor_id,
                        },
                        {
                          lemma: variant.lemma,
                          surface: variant.form,
                          cor_id: variant.cor_id,
                          cor_lemma_idx: variant.lemma_idx,
                          meaning_key: group.gloss ?? variant.lemma,
                          gloss: group.gloss ?? variant.gloss ?? null,
                          english_translation: saveableTranslation,
                          pos_tag: variant.pos_tag ?? group.pos_tag ?? null,
                          morphology: variant.morphology ?? null,
                          target_meaning_id: null,
                        },
                      )
                      if (addedLemma) {
                        onCloseSearch()
                      }
                    })()
                  }}
                  className="flex items-center justify-between gap-3"
                >
                  <div className="flex min-w-0 flex-col items-start gap-0.5">
                    <span>
                      <strong className="font-semibold">{variant.form}</strong>
                      {lemmaDisplay ? (
                        <span className="text-muted-foreground text-xs">
                          {" "}from <em>{lemmaDisplay}</em>
                          {lemmaTranslation ? (
                            ` (${lemmaTranslation})`
                          ) : isTranslationsLoading ? (
                            <Skeleton
                              data-testid="search-translation-skeleton"
                              className={`ml-1 inline-block h-3 w-14 align-middle ${searchTranslationSkeletonClassName}`}
                            />
                          ) : null}
                        </span>
                      ) : null}
                    </span>
                    {isTranslationsLoading && hasGloss ? (
                      <span className="text-muted-foreground text-xs leading-4">
                        <Skeleton
                          data-testid="search-translation-skeleton"
                          className={`inline-block h-3 w-24 align-middle ${searchTranslationSkeletonClassName}`}
                        />
                      </span>
                    ) : detailLine ? (
                      <span className="text-muted-foreground text-xs leading-4">{detailLine}</span>
                    ) : null}
                    {saveBlockedReason ? (
                      <span className="text-muted-foreground text-xs leading-4">{saveBlockedReason}</span>
                    ) : null}
                    {badgesFromGramRaw(variant.gram_raw).length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {badgesFromGramRaw(variant.gram_raw).map((badge) => (
                          <Badge
                            key={`cor-variant-${variant.cor_id}-gram-${badge.label}`}
                            variant={badge.tone === "primary" ? "default" : "secondary"}
                            className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(variant.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                            data-testid="search-metadata-badge"
                          >
                            {badge.label}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  {isVariationAdd ? (
                    <span className="text-muted-foreground flex items-center gap-1 text-xs font-semibold">
                      <span data-testid="search-add-variation-label">variation</span>
                      <Plus data-testid="search-add-icon" className="size-4 shrink-0" />
                    </span>
                  ) : (
                    <Plus data-testid="search-add-icon" className="text-muted-foreground size-4 shrink-0" />
                  )}
                </CommandItem>
              )
            })}
        </div>
      ))}
    </>
  )
}
