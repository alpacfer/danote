import type { LemmaDetailsResponse } from "@/app/core"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  englishGlossForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  posBorderLeftClass,
} from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type WordbankVariationGridProps = {
  variationForms: LemmaDetailsResponse["surface_forms"]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
}

export function WordbankVariationGrid({
  variationForms,
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: WordbankVariationGridProps) {
  if (variationForms.length === 0) {
    return null
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {variationForms.map((form) => {
        const formLemmaDisplay = lemmaDisplayForSavedForm(form)
        const formLemmaTranslation = lemmaTranslationWithGloss(
          form.lemma_translation ?? null,
          englishGlossForSavedForm(form),
        )
        const formBadges = badgesForSavedForm(form)
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
