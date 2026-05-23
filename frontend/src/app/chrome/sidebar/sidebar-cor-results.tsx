import { Plus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import {
  badgesFromGramRaw,
  badgesForSavedForm,
  corSecondaryBadgeClass,
  glossDisplayForVariant,
  isMultiWordLemma,
  lemmaDisplayForVariant,
  lemmaTranslationForVariant,
  lemmaTranslationWithGlossComma,
  saveableTranslationForVariant,
  posBadgeClass,
  primaryPosLabelForLemma,
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
  sourceLabel?: string
  showTranslationLine?: boolean
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
  sourceLabel,
  showTranslationLine = true,
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
              const itemValue = corVariantItemValue(variant)
              const isVariationAdd = variationCandidateCorIdSet.has(variant.cor_id)
              const glossLine = glossDisplayForVariant(variant)
              const sourceDescriptionLine = variant.english_source_description?.trim() || null
              const lemmaDisplay = lemmaDisplayForVariant(variant)
              const lemmaTranslation = lemmaTranslationForVariant(variant)
              const translationLine = lemmaTranslationWithGlossComma(lemmaTranslation, glossLine)
              const translationLineCoversGloss = showTranslationLine && Boolean(translationLine)
              const detailLine = sourceDescriptionLine
                || (translationLineCoversGloss ? null : glossLine)
              const saveableTranslation = saveableTranslationForVariant(variant)
              const sourceDisplay = sourceLabel?.trim() || lemmaDisplay
              const shouldShowSource = !!sourceDisplay
                && sourceDisplay.trim().toLowerCase() !== variant.form.trim().toLowerCase()
              const hasGloss = Boolean(variant.gloss?.trim())
              const isGeneratedNonCor = variant.dictionary_status === "generated_non_cor"
              // MWE detection: the backend normalizes phrasal-verb / idiom pos_tag → UD
              // ("VERB" for verbal MWEs, "NOUN" for nominal idioms), so the distinction
              // is carried by the lemma being multi-word.
              const isMweType = isMultiWordLemma(variant.lemma)
              let metadataBadges = isGeneratedNonCor
                ? badgesForSavedForm({ pos_tag: variant.pos_tag, morphology: variant.morphology, lemma: variant.lemma })
                : badgesFromGramRaw(variant.gram_raw)

              if (isMweType) {
                const mweLabel = primaryPosLabelForLemma(variant.pos_tag ?? null, variant.lemma)
                if (mweLabel && !metadataBadges.some(b => b.label === mweLabel)) {
                  const filtered = metadataBadges.filter(b => b.tone !== "primary")
                  metadataBadges = [{ label: mweLabel, tone: "primary" }, ...filtered]
                }
              }
              const isSaveBlocked = isTranslationsLoading || !saveableTranslation
              const saveBlockedReason = !isTranslationsLoading && !saveableTranslation
                ? "Translation required before saving."
                : null
              return (
                <CommandItem
                  key={itemValue}
                  value={itemValue}
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
                          corId: isGeneratedNonCor ? null : variant.cor_id,
                        },
                        {
                          lemma: variant.lemma,
                          surface: variant.form,
                          dictionary_status: isGeneratedNonCor ? "generated_non_cor" : "cor",
                          cor_id: isGeneratedNonCor ? null : variant.cor_id,
                          cor_lemma_idx: isGeneratedNonCor ? null : variant.lemma_idx,
                          // Each variant represents a distinct sense (especially for
                          // polysemous MWEs like "tage på"). Use the variant's own
                          // gloss as the meaning_key so two cards land in two meaning
                          // rows. Falling back to group.gloss would collide.
                          meaning_key: variant.gloss ?? group.gloss ?? variant.lemma,
                          gloss: variant.gloss ?? group.gloss ?? null,
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
                      {shouldShowSource ? (
                        <span className="text-muted-foreground text-xs">
                          {" "}from <em>{sourceDisplay}</em>
                        </span>
                      ) : null}
                    </span>
                    {showTranslationLine && translationLine ? (
                      <span className="text-muted-foreground text-xs leading-4">{translationLine}</span>
                    ) : null}
                    {isTranslationsLoading && hasGloss ? (
                      <span className="text-muted-foreground text-xs leading-4">
                        <Skeleton
                          data-testid="search-translation-skeleton"
                          className={`inline-block h-4 w-28 align-middle ${searchTranslationSkeletonClassName}`}
                        />
                      </span>
                    ) : detailLine ? (
                      <span className="text-muted-foreground text-xs leading-4">{detailLine}</span>
                    ) : null}
                    {saveBlockedReason ? (
                      <span className="text-muted-foreground text-xs leading-4">{saveBlockedReason}</span>
                    ) : null}
                    {metadataBadges.length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {metadataBadges.map((badge) => (
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
