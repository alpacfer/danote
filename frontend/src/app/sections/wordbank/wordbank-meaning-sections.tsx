import type { LemmaDetailsResponse } from "@/app/core"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  lemmaTranslationWithGloss,
  normalizeSearchWord,
  posBadgeClass,
  posBorderLeftClass,
} from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Volume2 } from "lucide-react"

type WordbankMeaningSectionsProps = {
  lemma: string
  meaningSections: LemmaDetailsResponse["meaning_sections"]
  selectedMeaningId: number | null
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
}

export function WordbankMeaningSections({
  lemma,
  meaningSections,
  selectedMeaningId,
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: WordbankMeaningSectionsProps) {
  if (!meaningSections || meaningSections.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved meanings for this lemma.</p>
  }

  return (
    <div className="space-y-3">
      {meaningSections.map((section, index) => {
        const sectionBadges = badgesForSavedForm({
          pos_tag: section.pos_tag ?? null,
          morphology: section.morphology ?? null,
        })
        const sectionTranslation = lemmaTranslationWithGloss(
          section.english_translation ?? null,
          section.gloss ?? null,
        )
        const isSelected = selectedMeaningId === section.id
        return (
          <Card
            key={`meaning-section-${section.id}-${section.meaning_key}`}
            id={`wordbank-meaning-${section.id}`}
            data-meaning-id={section.id}
            data-selected={isSelected ? "true" : "false"}
            className={isSelected ? "ring-primary/30 border-primary/50 ring-2" : undefined}
          >
            <CardContent className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs tabular-nums">{index + 1}</Badge>
                    <p className="text-lg leading-tight font-bold">{lemma}</p>
                  </div>
                  {sectionTranslation ? (
                    <p className="text-muted-foreground text-sm">{sectionTranslation}</p>
                  ) : null}
                </div>
                <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                  {sectionBadges.map((badge) => (
                    <Badge
                      key={`meaning-section-${section.id}-badge-${badge.label}`}
                      variant={badge.tone === "primary" ? "default" : "secondary"}
                      className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(section.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                    >
                      {badge.label}
                    </Badge>
                  ))}
                </div>
              </div>
              {section.surface_forms.length > 0 ? (
                <div className="space-y-2">
                  {section.surface_forms.map((form) => {
                    const formBadges = badgesForSavedForm(form)

                    return (
                      <div
                        key={`${section.id}-${form.form}`}
                        className={`rounded-md border border-border/70 border-l-2 p-3 ${posBorderLeftClass(form.pos_tag ?? section.pos_tag ?? null)}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <p className="text-base font-semibold leading-tight">{form.form}</p>
                            {formBadges.length > 0 ? (
                              <div className="flex flex-wrap gap-1.5">
                                {formBadges.map((badge) => (
                                  <Badge
                                    key={`${section.id}-${form.form}-badge-${badge.label}`}
                                    variant={badge.tone === "primary" ? "default" : "secondary"}
                                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(form.pos_tag ?? section.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                                  >
                                    {badge.label}
                                  </Badge>
                                ))}
                              </div>
                            ) : null}
                          </div>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="icon-sm"
                                  aria-label={`Listen to ${form.form}`}
                                  disabled={!form.has_pronunciation || Boolean(pronunciationLoadingByForm[normalizeSearchWord(form.form)])}
                                  onClick={(event) => {
                                    event.currentTarget.blur()
                                    onPlayPronunciation(form.form)
                                  }}
                                >
                                  <Volume2 />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="right" sideOffset={6}><p>Listen</p></TooltipContent>
                          </Tooltip>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : null}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
