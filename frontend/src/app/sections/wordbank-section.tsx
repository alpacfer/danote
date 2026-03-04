import { Info, RefreshCw, Volume2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Card, CardContent } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  glossDisplayForSavedForm,
  lemmaDisplayForSavedForm,
  normalizeSearchWord,
  posBadgeClass,
  type LemmaDetailsResponse,
  type VerificationErrorDetail,
  type WordbankLemma,
} from "@/app/core"

export type WordbankSectionProps = {
  selectedLemma: string | null
  wordbankError: string | null
  isWordbankLoading: boolean
  lemmas: WordbankLemma[]
  groupedWordbankLemmas: Array<{ letter: string; items: WordbankLemma[] }>
  onSelectLemma: (lemma: string) => void
  lemmaDetails: LemmaDetailsResponse | null
  lemmaDetailsError: string | null
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRegeneratingLemmaPronunciation: boolean
  onRegenerateSelectedLemmaPronunciation: () => void
  selectedLemmaVerificationError: VerificationErrorDetail | null
  hasSuggestedVerificationChanges: (detail: VerificationErrorDetail | null) => boolean
  isApplyingVerificationChanges: boolean
  onApplySelectedLemmaVerificationChanges: () => void
}

export function WordbankSection({
  selectedLemma,
  wordbankError,
  isWordbankLoading,
  lemmas,
  groupedWordbankLemmas,
  onSelectLemma,
  lemmaDetails,
  lemmaDetailsError,
  isLemmaDetailsLoading,
  showLemmaDetailsLoadingSkeleton,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  isRegeneratingLemmaPronunciation,
  onRegenerateSelectedLemmaPronunciation,
  selectedLemmaVerificationError,
  hasSuggestedVerificationChanges,
  isApplyingVerificationChanges,
  onApplySelectedLemmaVerificationChanges,
}: WordbankSectionProps) {
  if (!selectedLemma) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4">
        {wordbankError && (
          <p className="text-destructive text-sm" role="alert">
            {wordbankError}
          </p>
        )}
        {isWordbankLoading && lemmas.length === 0 ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-3 w-4" />
              <div className="flex flex-wrap gap-2">
                <Skeleton className="h-8 w-16 rounded-md" />
                <Skeleton className="h-8 w-20 rounded-md" />
                <Skeleton className="h-8 w-14 rounded-md" />
                <Skeleton className="h-8 w-24 rounded-md" />
              </div>
            </div>
            <div className="space-y-2">
              <Skeleton className="h-3 w-4" />
              <div className="flex flex-wrap gap-2">
                <Skeleton className="h-8 w-[4.5rem] rounded-md" />
                <Skeleton className="h-8 w-12 rounded-md" />
                <Skeleton className="h-8 w-[5.5rem] rounded-md" />
              </div>
            </div>
            <div className="space-y-2">
              <Skeleton className="h-3 w-4" />
              <div className="flex flex-wrap gap-2">
                <Skeleton className="h-8 w-[3.75rem] rounded-md" />
                <Skeleton className="h-8 w-[4.75rem] rounded-md" />
                <Skeleton className="h-8 w-[2.75rem] rounded-md" />
                <Skeleton className="h-8 w-[4.25rem] rounded-md" />
              </div>
            </div>
          </div>
        ) : lemmas.length === 0 ? (
          <p className="text-muted-foreground text-sm">No saved lemmas yet.</p>
        ) : (
          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-4">
              {groupedWordbankLemmas.map((group) => (
                <section key={group.letter} className="space-y-2">
                  <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{group.letter}</h3>
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((lemma) => (
                      <Button
                        key={lemma.lemma}
                        type="button"
                        variant="outline"
                        size="sm"
                        className="w-auto"
                        onClick={() => onSelectLemma(lemma.lemma)}
                      >
                        {lemma.display_lemma?.trim() || lemma.lemma}
                      </Button>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    )
  }

  const normalizedSelectedLemma = (lemmaDetails?.lemma ?? selectedLemma).trim().toLocaleLowerCase("da-DK")
  const lemmaPronunciationForm = (() => {
    if (!lemmaDetails) {
      return null
    }
    const exactMatch = lemmaDetails.surface_forms.find(
      (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma && form.has_pronunciation,
    )
    if (exactMatch) {
      return exactMatch.form
    }
    const firstAvailable = lemmaDetails.surface_forms.find((form) => form.has_pronunciation)
    return firstAvailable?.form ?? null
  })()
  const variationForms = lemmaDetails?.surface_forms.filter(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") !== normalizedSelectedLemma,
  ) ?? []
  const lemmaSurfaceDetails = lemmaDetails?.surface_forms.find(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma,
  ) ?? null
  const lemmaBadges = badgesForSavedForm({
    pos_tag: lemmaDetails?.pos_tag ?? null,
    morphology: lemmaDetails?.morphology ?? null,
    gram_raw: lemmaSurfaceDetails?.gram_raw ?? null,
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {lemmaDetailsError && (
        <p className="text-destructive text-sm" role="alert">
          {lemmaDetailsError}
        </p>
      )}
      {isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton ? (
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Skeleton className="h-10 w-40" />
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-5 w-32" />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Card>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <Skeleton className="h-6 w-24" />
                </div>
                <Skeleton className="h-4 w-28" />
                <div className="flex flex-wrap gap-1.5">
                  <Skeleton className="h-5 w-12 rounded-full" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <Skeleton className="h-6 w-20" />
                  <Skeleton className="h-4 w-14" />
                </div>
                <Skeleton className="h-4 w-24" />
                <div className="flex flex-wrap gap-1.5">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-10 rounded-full" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : !lemmaDetails ? (
        isLemmaDetailsLoading ? null : (
          <p className="text-muted-foreground text-sm">No details found for this lemma.</p>
        )
      ) : (
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-3 pr-1">
            <div>
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <h2 className="mr-3 text-4xl font-bold leading-tight">{lemmaDetails.lemma}</h2>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          aria-label={`Listen to ${lemmaDetails.lemma}`}
                          disabled={
                            !lemmaPronunciationForm
                            || Boolean(pronunciationLoadingByForm[normalizeSearchWord(lemmaPronunciationForm)])
                          }
                          onClick={(event) => {
                            event.currentTarget.blur()
                            if (!lemmaPronunciationForm) {
                              return
                            }
                            onPlayPronunciation(lemmaPronunciationForm)
                          }}
                        >
                          <Volume2 />
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="right" sideOffset={6}>
                      <p>Listen</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <ButtonGroup className="shrink-0">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={isRegeneratingLemmaPronunciation}
                    onClick={onRegenerateSelectedLemmaPronunciation}
                  >
                    <RefreshCw className={isRegeneratingLemmaPronunciation ? "animate-spin" : ""} />
                    Regenerate Audio
                  </Button>
                  <Popover>
                    <PopoverTrigger asChild>
                      <span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          aria-label="Show verification error info"
                          disabled={!selectedLemmaVerificationError}
                        >
                          <Info className="size-4" />
                        </Button>
                      </span>
                    </PopoverTrigger>
                    <PopoverContent align="end" className="w-96 space-y-3">
                      {!selectedLemmaVerificationError ? (
                        <p className="text-muted-foreground text-sm">No verification errors for this word.</p>
                      ) : (
                        <>
                          <div>
                            <p className="text-sm font-semibold">Verification Error</p>
                            <p className="text-muted-foreground text-xs">
                              Provider: {selectedLemmaVerificationError.provider}
                            </p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                              Problem
                            </p>
                            <p className="text-sm">{selectedLemmaVerificationError.problem}</p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                              Change to implement
                            </p>
                            <p className="text-sm">{selectedLemmaVerificationError.changeToImplement}</p>
                          </div>
                          {selectedLemmaVerificationError.suggestedChanges
                            && Object.values(selectedLemmaVerificationError.suggestedChanges).some(Boolean) ? (
                              <div className="space-y-1">
                                <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
                                  Specific fields to change
                                </p>
                                <ul className="space-y-1 text-sm">
                                  {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag ? (
                                    <li>Lemma POS: {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag}</li>
                                  ) : null}
                                  {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology ? (
                                    <li>Lemma morphology: {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology}</li>
                                  ) : null}
                                  {selectedLemmaVerificationError.suggestedChanges.surfacePosTag ? (
                                    <li>Surface POS: {selectedLemmaVerificationError.suggestedChanges.surfacePosTag}</li>
                                  ) : null}
                                  {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology ? (
                                    <li>Surface morphology: {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology}</li>
                                  ) : null}
                                  {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation ? (
                                    <li>Lemma translation: {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation}</li>
                                  ) : null}
                                  {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation ? (
                                    <li>Surface translation: {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation}</li>
                                  ) : null}
                                </ul>
                              </div>
                            ) : null}
                          <Button
                            type="button"
                            size="sm"
                            className="w-full"
                            disabled={!hasSuggestedVerificationChanges(selectedLemmaVerificationError) || isApplyingVerificationChanges}
                            onClick={onApplySelectedLemmaVerificationChanges}
                          >
                            {isApplyingVerificationChanges ? "Applying..." : "Apply Gemini Changes"}
                          </Button>
                        </>
                      )}
                    </PopoverContent>
                  </Popover>
                </ButtonGroup>
              </div>
              <p className="text-muted-foreground mt-1 text-base">
                {lemmaDetails.english_translation ?? "No translation available."}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {lemmaBadges.map((badge) => (
                  <Badge
                    key={`lemma-badge-${badge.label}`}
                    variant={badge.tone === "primary" ? "default" : "secondary"}
                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(lemmaDetails.pos_tag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                  >
                    {badge.label}
                  </Badge>
                ))}
              </div>
            </div>

            {variationForms.length === 0 ? (
              <p className="text-muted-foreground text-sm">No saved variations for this lemma.</p>
            ) : (
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
                                  disabled={
                                    !form.has_pronunciation
                                    || Boolean(pronunciationLoadingByForm[normalizeSearchWord(form.form)])
                                  }
                                  onClick={(event) => {
                                    event.currentTarget.blur()
                                    onPlayPronunciation(form.form)
                                  }}
                                >
                                  <Volume2 />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="right" sideOffset={6}>
                              <p>Listen</p>
                            </TooltipContent>
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
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
