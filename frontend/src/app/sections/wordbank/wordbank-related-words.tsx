import { type Dispatch, type SetStateAction, useState } from "react"
import { Eye, Plus } from "lucide-react"

import {
  badgesFromGramRaw,
  corSecondaryBadgeClass,
  normalizeSearchWord,
  posBadgeClass,
  primaryPosLabel,
  type CORSearchVariant,
  type LemmaDetailsResponse,
  type SearchSaveSeed,
} from "@/app/core"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

type RelatedWordItem = NonNullable<LemmaDetailsResponse["related_words"]>["items"][number]

type WordbankRelatedWordsProps = {
  relatedWords: LemmaDetailsResponse["related_words"] | undefined
  onSaveRelatedWordFromSearchSeed: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
  onOpenRelatedWordTarget: (lemma: string, meaningId: number | null) => void
}

export function WordbankRelatedWords({
  relatedWords,
  onSaveRelatedWordFromSearchSeed,
  onOpenRelatedWordTarget,
}: WordbankRelatedWordsProps) {
  const [openCardIds, setOpenCardIds] = useState<Record<number, boolean>>({})
  const [savingByKey, setSavingByKey] = useState<Record<string, boolean>>({})

  // "Composition" only shows constituent components (compound_component). Reverse
  // links (`compound_host` — "this lemma is part of these other saved compounds")
  // are a related-words concept and are hidden until a real Related/Synonyms
  // feature exists. See bug fix discussion in the MWE feature review.
  const compositionItems = (relatedWords?.items ?? []).filter(
    (item) => item.relation_type === "compound_component",
  )
  if (!relatedWords || relatedWords.status !== "ready" || compositionItems.length === 0) {
    return null
  }

  return (
    <section
      className="flex flex-col gap-4 pt-2"
      aria-labelledby="wordbank-composition-heading"
      data-grid-anchor="unit"
    >
      <h2
        id="wordbank-composition-heading"
        className="font-section-title flex h-8 items-center text-xl leading-none font-normal tracking-normal"
      >
        Composition
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {compositionItems.map((item) => {
          const uniqueVariant = item.display_variant ?? null
          const candidateVariants = item.candidate_variants ?? []
          const isSaved = item.saved_match.status !== "unsaved"
          const isAmbiguous = !isSaved && !uniqueVariant && candidateVariants.length > 1
          const actionKey = uniqueVariant ? `${item.id}:${uniqueVariant.cor_id}` : `${item.id}:toggle`
          const isActionLoading = Boolean(savingByKey[actionKey])
          const isOpen = Boolean(openCardIds[item.id])
          return (
            <Collapsible
              key={`related-word-${item.id}`}
              open={isOpen}
              onOpenChange={(open) => {
                setOpenCardIds((current) => ({ ...current, [item.id]: open }))
              }}
            >
              <Card
                className="gap-0 overflow-hidden py-0"
                data-material="related"
                data-paper-stock
                data-grid-anchor="unit"
              >
                <CardContent className="space-y-3 p-0">
                  {isAmbiguous ? (
                    <CollapsibleTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        className="hover:bg-accent/60 h-auto w-full items-center justify-between rounded-none px-4 py-4 text-left"
                        aria-label={`Choose composition match for ${item.lemma}`}
                      >
                        <RelatedWordCardBody item={item} uniqueVariant={uniqueVariant} isAmbiguous={isAmbiguous} />
                        <Plus className="text-muted-foreground size-4 shrink-0 self-center" />
                      </Button>
                    </CollapsibleTrigger>
                  ) : isSaved ? (
                    <Button
                      type="button"
                      variant="ghost"
                      className="hover:bg-accent/60 h-auto w-full items-center justify-between rounded-none px-4 py-4 text-left"
                      aria-label={`Open ${item.lemma} in wordbank`}
                      onClick={() => onOpenRelatedWordTarget(normalizeSearchWord(item.saved_match.target_lemma ?? item.lemma), item.saved_match.target_meaning_id ?? null)}
                    >
                      <RelatedWordCardBody item={item} uniqueVariant={uniqueVariant} isAmbiguous={false} />
                      <Eye className="text-muted-foreground size-4 shrink-0 self-center" />
                    </Button>
                  ) : uniqueVariant ? (
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={isActionLoading}
                      className="hover:bg-accent/60 h-auto w-full items-center justify-between rounded-none px-4 py-4 text-left"
                      aria-label={`Add composition component ${item.lemma}`}
                      onClick={() => {
                        void saveVariant({
                          item,
                          variant: uniqueVariant,
                          key: actionKey,
                          setSavingByKey,
                          onSaveRelatedWordFromSearchSeed,
                        })
                      }}
                    >
                      <RelatedWordCardBody item={item} uniqueVariant={uniqueVariant} isAmbiguous={false} />
                      <Plus className="text-muted-foreground size-4 shrink-0 self-center" />
                    </Button>
                  ) : (
                    <div className="px-4 py-4">
                      <RelatedWordCardBody item={item} uniqueVariant={uniqueVariant} isAmbiguous={false} />
                    </div>
                  )}
                  {isAmbiguous ? (
                    <CollapsibleContent className="space-y-2 px-4 pb-4">
                      {candidateVariants.map((variant) => {
                        const variantKey = `${item.id}:${variant.cor_id}`
                        const isVariantSaving = Boolean(savingByKey[variantKey])
                        return (
                          <Button
                            key={`related-word-choice-${item.id}-${variant.cor_id}`}
                            type="button"
                            variant="ghost"
                            aria-label={`Add ${variant.lemma}`}
                            disabled={isVariantSaving}
                            className="bg-muted/35 hover:bg-accent/60 h-auto w-full items-start justify-between rounded-xl border px-3 py-2 text-left"
                            onClick={() => {
                              void saveVariant({
                                item,
                                variant,
                                key: variantKey,
                                setSavingByKey,
                                onSaveRelatedWordFromSearchSeed,
                              }).then((savedLemma) => {
                                if (savedLemma) {
                                  setOpenCardIds((current) => ({ ...current, [item.id]: false }))
                                }
                              })
                            }}
                          >
                            <div className="min-w-0 space-y-1">
                              {(variant.gloss_translation ?? variant.gloss) ? (
                                <p className="text-sm font-medium">{variant.gloss_translation ?? variant.gloss}</p>
                              ) : null}
                              <div className="flex flex-wrap gap-1.5">
                                {badgesFromGramRaw(variant.gram_raw).map((badge) => (
                                  <Badge
                                    key={`related-word-choice-${item.id}-${variant.cor_id}-${badge.label}`}
                                    variant={badge.tone === "primary" ? "outline" : "secondary"}
                                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(variant.pos_tag ?? item.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                                    title={badge.tone === "primary" ? badge.label : undefined}
                                    aria-label={badge.tone === "primary" ? badge.label : undefined}
                                  >
                                    {badge.label}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                            <Plus className="text-muted-foreground size-4 shrink-0 self-center" />
                          </Button>
                        )
                      })}
                    </CollapsibleContent>
                  ) : null}
                </CardContent>
              </Card>
            </Collapsible>
          )
        })}
      </div>
    </section>
  )
}

function RelatedWordCardBody({
  item,
  uniqueVariant,
  isAmbiguous,
}: {
  item: RelatedWordItem
  uniqueVariant: CORSearchVariant | null
  isAmbiguous: boolean
}) {
  return (
    <div className="min-w-0 flex-1">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-base font-semibold">{displayLemma(item.lemma, item.pos_tag ?? null)}</span>
        {item.english_translation ? (
          <span className="text-muted-foreground text-sm italic">{item.english_translation}</span>
        ) : null}
      </div>
      {uniqueVariant ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {wordPageBadgesForSavedForm({
            pos_tag: uniqueVariant.pos_tag ?? item.pos_tag ?? null,
            morphology: uniqueVariant.morphology ?? null,
            gram_raw: uniqueVariant.gram_raw,
          }).map((badge) => (
            <Badge
              key={`related-word-${item.id}-${uniqueVariant.cor_id}-${badge.label}`}
              variant={badge.tone === "primary" ? "outline" : "secondary"}
              className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(uniqueVariant.pos_tag ?? item.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
              title={badge.tone === "primary" ? badge.label : undefined}
              aria-label={badge.tone === "primary" ? badge.label : undefined}
            >
              {badge.label}
            </Badge>
          ))}
        </div>
      ) : isAmbiguous ? (
        <p className="text-muted-foreground mt-2 text-xs">Multiple COR matches. Choose one to save.</p>
      ) : item.pos_tag ? (
        <div className="mt-2">
          <Badge
            variant="outline"
            className={`text-xs ${posBadgeClass(item.pos_tag)}`.trim()}
            title={primaryPosLabel(item.pos_tag) ?? item.pos_tag}
            aria-label={primaryPosLabel(item.pos_tag) ?? item.pos_tag}
          >
            {primaryPosLabel(item.pos_tag) ?? item.pos_tag}
          </Badge>
        </div>
      ) : null}
    </div>
  )
}

function displayLemma(lemma: string, posTag: string | null): string {
  if (posTag === "VERB") {
    return `at ${lemma}`
  }
  return lemma
}

async function saveVariant(args: {
  item: RelatedWordItem
  variant: CORSearchVariant
  key: string
  setSavingByKey: Dispatch<SetStateAction<Record<string, boolean>>>
  onSaveRelatedWordFromSearchSeed: WordbankRelatedWordsProps["onSaveRelatedWordFromSearchSeed"]
}): Promise<string | null> {
  const { item, variant, key, setSavingByKey, onSaveRelatedWordFromSearchSeed } = args
  setSavingByKey((current) => ({ ...current, [key]: true }))
  try {
    return await onSaveRelatedWordFromSearchSeed(
      variant.form,
      variant.lemma,
      {
        posTag: variant.pos_tag ?? item.pos_tag ?? null,
        morphology: variant.morphology ?? null,
        corId: variant.cor_id,
      },
      buildSearchSeed(item, variant),
    )
  } finally {
    setSavingByKey((current) => {
      const next = { ...current }
      delete next[key]
      return next
    })
  }
}

function buildSearchSeed(item: RelatedWordItem, variant: CORSearchVariant): SearchSaveSeed {
  return {
    lemma: variant.lemma,
    surface: variant.form,
    cor_id: variant.cor_id,
    cor_lemma_idx: variant.lemma_idx,
    meaning_key: variant.gloss ?? variant.lemma,
    gloss: variant.gloss ?? null,
    english_translation: item.english_translation ?? variant.saveable_translation ?? variant.lemma_translation ?? null,
    pos_tag: variant.pos_tag ?? item.pos_tag ?? null,
    morphology: variant.morphology ?? null,
    target_meaning_id: null,
  }
}
