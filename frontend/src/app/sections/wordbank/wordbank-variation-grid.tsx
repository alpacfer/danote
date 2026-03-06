import type { LemmaDetailsResponse } from "@/app/core"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  glossDisplayForSavedForm,
  lemmaDisplayForSavedForm,
  normalizeSearchWord,
  posBadgeClass,
} from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Volume2 } from "lucide-react"

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
    return <p className="text-muted-foreground text-sm">No saved variations for this lemma.</p>
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {variationForms.map((form) => {
        const formLemmaDisplay = lemmaDisplayForSavedForm(form)
        const formLemmaTranslation = form.lemma_translation?.trim() || null
        const formGlossDisplay = glossDisplayForSavedForm(form)
        const formBadges = badgesForSavedForm(form)
        return (
          <Card key={form.form}>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-lg leading-tight">
                  <strong className="font-bold">{form.form}</strong>
                  {formLemmaDisplay ? (
                    <span className="text-muted-foreground text-xs">
                      {" "}from <em>{formLemmaDisplay}</em>
                      {formLemmaTranslation ? ` (${formLemmaTranslation})` : ""}
                    </span>
                  ) : null}
                </p>
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
              <p className="text-muted-foreground text-sm">
                {formGlossDisplay ?? form.english_translation ?? "No translation available."}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {formBadges.map((badge) => (
                  <Badge
                    key={`${form.form}-${badge.label}`}
                    variant={badge.tone === "primary" ? "default" : "secondary"}
                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(form.pos_tag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                  >
                    {badge.label}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
