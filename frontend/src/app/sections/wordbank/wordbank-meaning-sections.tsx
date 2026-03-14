import type { LemmaDetailsResponse } from "@/app/core"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  lemmaTranslationWithGloss,
  posBadgeClass,
  posBorderLeftClass,
  semanticCategoryBadgeClass,
} from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { WordbankScopeContextMenu } from "@/app/sections/wordbank/wordbank-scope-context-menu"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

type WordbankMeaningSectionsProps = {
  lemma: string
  meaningSections: LemmaDetailsResponse["meaning_sections"]
  selectedMeaningId: number | null
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
}

export function WordbankMeaningSections({
  lemma,
  meaningSections,
  selectedMeaningId,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  isRethinkingCategories,
  onRethinkCategories,
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
          section.gloss_translation ?? null,
        )
        const isSelected = selectedMeaningId === section.id
        return (
          <WordbankScopeContextMenu
            key={`meaning-section-${section.id}-${section.meaning_key}`}
            isBusy={isRethinkingCategories}
            onRethinkCategories={() => onRethinkCategories(section.id)}
          >
            <Card
              id={`wordbank-meaning-${section.id}`}
              data-testid={`wordbank-meaning-card-${section.id}`}
              data-meaning-id={section.id}
              data-selected={isSelected ? "true" : "false"}
              className={`border-l-2 ${posBorderLeftClass(section.pos_tag ?? null)} ${isSelected ? "ring-primary/30 border-primary/50 ring-2" : ""}`.trim()}
            >
              <CardContent className="space-y-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
                      <Badge variant="secondary" className="text-xs tabular-nums">{index + 1}</Badge>
                      <span className="text-lg leading-tight font-bold">{lemma}</span>
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
                    {sectionTranslation ? (
                      <p className="text-muted-foreground ml-9 text-sm italic">{sectionTranslation}</p>
                    ) : null}
                  </div>
                  {section.categories && section.categories.length > 0 ? (
                    <div
                      data-testid={`wordbank-meaning-category-badges-${section.id}`}
                      className="flex flex-wrap justify-end gap-1.5 sm:max-w-[45%]"
                    >
                      {section.categories.map((category) => (
                        <Badge
                          key={`meaning-section-${section.id}-category-${category}`}
                          variant="outline"
                          className={`text-xs ${semanticCategoryBadgeClass(category)}`.trim()}
                        >
                          {category}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
                {section.surface_forms.length > 0 ? (
                  <div className="ml-4 mt-3 divide-y divide-border/50">
                    {section.surface_forms.map((form) => {
                      const sectionBadgeLabels = new Set(sectionBadges.map((b) => b.label))
                      const formBadges = badgesForSavedForm(form).filter((b) => !sectionBadgeLabels.has(b.label))
                      return (
                        <div
                          key={`${section.id}-${form.form}`}
                          className="flex flex-wrap items-center gap-x-2 gap-y-1 py-2 first:pt-0"
                        >
                          <WordbankPronunciationWord
                            form={form.form}
                            hasPronunciation={form.has_pronunciation ?? false}
                            pronunciationLoadingByForm={pronunciationLoadingByForm}
                            onPlayPronunciation={onPlayPronunciation}
                            className="text-sm font-semibold"
                            iconClassName="size-3"
                          />
                          {formBadges.map((badge) => (
                            <Badge
                              key={`${section.id}-${form.form}-badge-${badge.label}`}
                              variant={badge.tone === "primary" ? "default" : "secondary"}
                              className={`text-[11px] ${badge.tone === "primary" ? `border ${posBadgeClass(form.pos_tag ?? section.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                            >
                              {badge.label}
                            </Badge>
                          ))}
                        </div>
                      )
                    })}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </WordbankScopeContextMenu>
        )
      })}
    </div>
  )
}
