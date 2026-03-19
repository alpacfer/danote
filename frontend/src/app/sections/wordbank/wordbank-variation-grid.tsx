import type { LemmaDetailsResponse } from "@/app/core"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  englishGlossForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  normalizeSearchWord,
  posBadgeClass,
  posBorderLeftClass,
} from "@/app/core"
import { WordbankFormList } from "@/app/sections/wordbank/wordbank-form-list"
import { WordbankParadigmTable } from "@/app/sections/wordbank/wordbank-paradigm-table"
import {
  buildAdjectiveDegreeGroups,
  buildAdjectiveParadigm,
  buildNounParadigm,
  buildVerbParadigm,
} from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type WordbankVariationGridProps = {
  allSurfaceForms: LemmaDetailsResponse["surface_forms"]
  variationForms: LemmaDetailsResponse["surface_forms"]
  posTag: string | null
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}

export function WordbankVariationGrid({
  allSurfaceForms,
  variationForms,
  posTag,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: WordbankVariationGridProps) {
  const upperPosTag = (posTag ?? "").toUpperCase()
  const isNoun = upperPosTag === "NOUN"
  const nounParadigm = isNoun ? buildNounParadigm(allSurfaceForms) : null
  const adjectiveParadigm = upperPosTag === "ADJ" ? buildAdjectiveParadigm(allSurfaceForms) : null
  const verbParadigm = upperPosTag === "VERB" ? buildVerbParadigm(allSurfaceForms) : null

  if (nounParadigm || adjectiveParadigm || verbParadigm) {
    return (
      <WordbankParadigmTable
        paradigm={nounParadigm ?? adjectiveParadigm ?? verbParadigm!}
        pronunciationLoadingByForm={pronunciationLoadingByForm}
        regeneratingPronunciationByForm={regeneratingPronunciationByForm}
        onPlayPronunciation={onPlayPronunciation}
        onRegeneratePronunciation={onRegeneratePronunciation}
      />
    )
  }

  if (variationForms.length === 0) {
    return null
  }

  const formGroups = upperPosTag === "VERB"
    ? []
    : upperPosTag === "ADJ"
      ? buildAdjectiveDegreeGroups(variationForms)
      : []
  const hasGroups = formGroups.length > 0 && formGroups.some((g) => g.label !== "Other")

  if (hasGroups) {
    return (
      <WordbankFormList
        groups={formGroups}
        fallbackForms={[]}
        parentPosTag={posTag}
        parentBadgeLabels={new Set()}
        pronunciationLoadingByForm={pronunciationLoadingByForm}
        regeneratingPronunciationByForm={regeneratingPronunciationByForm}
        onPlayPronunciation={onPlayPronunciation}
        onRegeneratePronunciation={onRegeneratePronunciation}
      />
    )
  }

  // Fallback: 2-column grid
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {variationForms.map((form) => {
        const formLemmaDisplay = lemmaDisplayForSavedForm(form)
        const formLemmaTranslation = lemmaTranslationWithGloss(
          form.lemma_translation ?? null,
          englishGlossForSavedForm(form),
        )
        const formBadges = badgesForSavedForm(form)
        const normalizedForm = normalizeSearchWord(form.form)
        const isRegenerating = Boolean(regeneratingPronunciationByForm[normalizedForm])
        return (
          <div
            key={form.form}
            className={cn(
              "rounded-md border-l-2 bg-muted/30 p-3 dark:bg-muted/15",
              posBorderLeftClass(form.pos_tag),
            )}
          >
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <WordbankPronunciationWord
                form={form.form}
                hasPronunciation={form.has_pronunciation ?? false}
                pronunciationLoadingByForm={pronunciationLoadingByForm}
                onPlayPronunciation={onPlayPronunciation}
                contextMenuItems={[
                  {
                    label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
                    disabled: isRegenerating,
                    onSelect: () => onRegeneratePronunciation(form.form),
                  },
                ]}
                className="text-base font-bold"
                iconClassName="size-3"
              />
              {formBadges.map((badge) => (
                <Badge
                  key={`${form.form}-${badge.label}`}
                  variant={badge.tone === "primary" ? "default" : "secondary"}
                  className={`text-[11px] ${badge.tone === "primary" ? `border ${posBadgeClass(form.pos_tag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                >
                  {badge.label}
                </Badge>
              ))}
            </div>
            {formLemmaDisplay ? (
              <p className="text-muted-foreground mt-0.5 pl-1 text-xs">
                from <em>{formLemmaDisplay}</em>
                {formLemmaTranslation ? <span> ({formLemmaTranslation})</span> : null}
              </p>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
