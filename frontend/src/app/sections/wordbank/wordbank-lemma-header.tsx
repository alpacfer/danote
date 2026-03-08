import type { LemmaDetailsResponse, VerificationErrorDetail } from "@/app/core"
import { badgesForSavedForm, corSecondaryBadgeClass, normalizeSearchWord, posBadgeClass } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Info, RefreshCw, Volume2 } from "lucide-react"

type WordbankLemmaHeaderProps = {
  selectedLemma: string
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRegeneratingLemmaPronunciation: boolean
  onRegenerateSelectedLemmaPronunciation: () => void
  selectedLemmaVerificationError: VerificationErrorDetail | null
  hasSuggestedVerificationChanges: (detail: VerificationErrorDetail | null) => boolean
  isApplyingVerificationChanges: boolean
  onApplySelectedLemmaVerificationChanges: () => void
  showSupplementaryMetadata: boolean
}

export function WordbankLemmaHeader({
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  isRegeneratingLemmaPronunciation,
  onRegenerateSelectedLemmaPronunciation,
  selectedLemmaVerificationError,
  hasSuggestedVerificationChanges,
  isApplyingVerificationChanges,
  onApplySelectedLemmaVerificationChanges,
  showSupplementaryMetadata,
}: WordbankLemmaHeaderProps) {
  const normalizedSelectedLemma = (lemmaDetails.lemma ?? selectedLemma).trim().toLocaleLowerCase("da-DK")
  const selectedMeaningSection = (lemmaDetails.meaning_sections ?? []).find((section) => section.id === selectedMeaningId) ?? null
  const lemmaPronunciationForm = (() => {
    const selectedMeaningForms = selectedMeaningSection?.surface_forms ?? []
    const exactMatch = [...selectedMeaningForms, ...lemmaDetails.surface_forms].find(
      (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma && form.has_pronunciation,
    )
    if (exactMatch) {
      return exactMatch.form
    }
    const firstAvailable = [...selectedMeaningForms, ...lemmaDetails.surface_forms].find((form) => form.has_pronunciation)
    return firstAvailable?.form ?? null
  })()
  const lemmaSurfaceDetails = lemmaDetails.surface_forms.find(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma,
  ) ?? null
  const headerTranslation = selectedMeaningSection?.english_translation ?? lemmaDetails.english_translation
  const headerPosTag = selectedMeaningSection?.pos_tag ?? lemmaDetails.pos_tag
  const headerMorphology = selectedMeaningSection?.morphology ?? lemmaDetails.morphology
  const headerBadges = showSupplementaryMetadata || Boolean(selectedMeaningSection)
    ? badgesForSavedForm({
      pos_tag: headerPosTag ?? null,
      morphology: headerMorphology ?? null,
      gram_raw: lemmaSurfaceDetails?.gram_raw ?? null,
    })
    : []

  return (
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
                  disabled={!lemmaPronunciationForm || Boolean(pronunciationLoadingByForm[normalizeSearchWord(lemmaPronunciationForm)])}
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
            <TooltipContent side="right" sideOffset={6}><p>Listen</p></TooltipContent>
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
                    <p className="text-muted-foreground text-xs">Provider: {selectedLemmaVerificationError.provider}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Problem</p>
                    <p className="text-sm">{selectedLemmaVerificationError.problem}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Change to implement</p>
                    <p className="text-sm">{selectedLemmaVerificationError.changeToImplement}</p>
                  </div>
                  {selectedLemmaVerificationError.suggestedChanges && Object.values(selectedLemmaVerificationError.suggestedChanges).some(Boolean) ? (
                    <div className="space-y-1">
                      <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Specific fields to change</p>
                      <ul className="space-y-1 text-sm">
                        {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag ? <li>Lemma POS: {selectedLemmaVerificationError.suggestedChanges.lemmaPosTag}</li> : null}
                        {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology ? <li>Lemma morphology: {selectedLemmaVerificationError.suggestedChanges.lemmaMorphology}</li> : null}
                        {selectedLemmaVerificationError.suggestedChanges.surfacePosTag ? <li>Surface POS: {selectedLemmaVerificationError.suggestedChanges.surfacePosTag}</li> : null}
                        {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology ? <li>Surface morphology: {selectedLemmaVerificationError.suggestedChanges.surfaceMorphology}</li> : null}
                        {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation ? <li>Lemma translation: {selectedLemmaVerificationError.suggestedChanges.lexemeTranslation}</li> : null}
                        {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation ? <li>Surface translation: {selectedLemmaVerificationError.suggestedChanges.surfaceTranslation}</li> : null}
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
      {showSupplementaryMetadata || selectedMeaningSection ? (
        <>
          <p className="text-muted-foreground mt-1 text-base">{headerTranslation ?? "No translation available."}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {headerBadges.map((badge) => (
              <Badge
                key={`lemma-badge-${badge.label}`}
                variant={badge.tone === "primary" ? "default" : "secondary"}
                className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(headerPosTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
              >
                {badge.label}
              </Badge>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

export function WordbankDetailsLoadingSkeleton() {
  return (
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
    </div>
  )
}
