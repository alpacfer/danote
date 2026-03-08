import { Plus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import {
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
} from "@/app/core"

type GroupedVariant = {
  group: CORSearchGroup
  variant: CORSearchVariant
}

type SidebarCorResultsProps = {
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: GroupedVariant[]
  savedLemmaKeySet: Set<string>
  normalizedQuery: string
  corVariantItemValue: (variant: CORSearchVariant) => string
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ) => Promise<string | null>
  onCloseSearch: () => void
}

export function SidebarCorResults({
  orderedCorSearchGroups,
  corSearchVariantsToRender,
  savedLemmaKeySet,
  normalizedQuery,
  corVariantItemValue,
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
              const isVariationCandidate = normalizeSearchWord(variant.form) !== normalizeSearchWord(variant.lemma)
              const isVariationAdd = isVariationCandidate && savedLemmaKeySet.has(normalizeSearchWord(variant.lemma))
              const detailLine = glossDisplayForVariant(variant)
              return (
                <CommandItem
                  key={`cor-variant-${variant.cor_id}`}
                  value={corVariantItemValue(variant)}
                  onSelect={() => {
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
                      {lemmaDisplayForVariant(variant) ? (
                        <span className="text-muted-foreground text-xs">
                          {" "}from <em>{lemmaDisplayForVariant(variant)}</em>
                          {lemmaTranslationForVariant(variant) ? ` (${lemmaTranslationForVariant(variant)})` : ""}
                        </span>
                      ) : null}
                    </span>
                    {detailLine ? <span className="text-muted-foreground text-xs leading-4">{detailLine}</span> : null}
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
