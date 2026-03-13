import type { LemmaDetailsResponse, VerificationErrorDetail, VerificationQueuedDetail, VerificationSuccessDetail } from "@/app/core"
import { badgesForSavedForm, corSecondaryBadgeClass, formatSavedNoteTimestamp, posBadgeClass } from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { BadgeCheck, Info, LoaderCircle, RefreshCw } from "lucide-react"

type WordbankLemmaHeaderProps = {
  selectedLemma: string
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRegeneratingLemmaPronunciation: boolean
  onRegenerateSelectedLemmaPronunciation: () => void
  selectedLemmaVerificationError: VerificationErrorDetail | null
  selectedLemmaVerificationQueued: VerificationQueuedDetail | null
  selectedLemmaVerificationSuccess: VerificationSuccessDetail | null
  hasSuggestedVerificationActions: (detail: VerificationErrorDetail | null) => boolean
  isApplyingVerificationChanges: boolean
  onApplySelectedLemmaVerificationAction: (actionIndex: number) => void
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
  selectedLemmaVerificationQueued,
  selectedLemmaVerificationSuccess,
  hasSuggestedVerificationActions,
  isApplyingVerificationChanges,
  onApplySelectedLemmaVerificationAction,
  showSupplementaryMetadata,
}: WordbankLemmaHeaderProps) {
  const normalizedSelectedLemma = (lemmaDetails.lemma ?? selectedLemma).trim().toLocaleLowerCase("da-DK")
  const selectedMeaningSection = (lemmaDetails.meaning_sections ?? []).find((section) => section.id === selectedMeaningId) ?? null
  const lemmaPronunciationForm = (() => {
    const selectedMeaningForms = selectedMeaningSection?.surface_forms ?? []
    const allMeaningForms = (lemmaDetails.meaning_sections ?? []).flatMap((s) => s.surface_forms)
    const searchForms = [...selectedMeaningForms, ...lemmaDetails.surface_forms, ...allMeaningForms]
    const exactMatch = searchForms.find(
      (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma && form.has_pronunciation,
    )
    if (exactMatch) {
      return exactMatch.form
    }
    const firstAvailable = searchForms.find((form) => form.has_pronunciation)
    return firstAvailable?.form ?? null
  })()
  const lemmaSurfaceDetails = lemmaDetails.surface_forms.find(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") === normalizedSelectedLemma,
  ) ?? null
  const headerTranslation = lemmaDetails.is_sectioned
    ? null
    : (selectedMeaningSection?.english_translation ?? lemmaDetails.english_translation)
  const headerPosTag = selectedMeaningSection?.pos_tag ?? lemmaDetails.pos_tag
  const headerMorphology = selectedMeaningSection?.morphology ?? lemmaDetails.morphology
  const headerBadges = showSupplementaryMetadata
    ? badgesForSavedForm({
      pos_tag: headerPosTag ?? null,
      morphology: headerMorphology ?? null,
      gram_raw: lemmaSurfaceDetails?.gram_raw ?? null,
    })
    : []
  const selectedVerificationTimestamp =
    selectedMeaningSection?.verification?.completed_at
    ?? selectedMeaningSection?.verification?.requested_at
    ?? lemmaDetails.verification?.completed_at
    ?? lemmaDetails.verification?.requested_at
    ?? new Date().toISOString()
  const verificationStatusLine = selectedLemmaVerificationQueued
    ? `Verifying since ${formatSavedNoteTimestamp(selectedLemmaVerificationQueued.requestedAt)}`
    : selectedLemmaVerificationSuccess
      ? `Verified ${formatSavedNoteTimestamp(selectedLemmaVerificationSuccess.verifiedAt)}`
      : selectedLemmaVerificationError
        ? `Review needed ${formatSavedNoteTimestamp(selectedVerificationTimestamp)}`
        : null

  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <WordbankPronunciationWord
            form={lemmaDetails.lemma}
            playForm={lemmaPronunciationForm ?? undefined}
            hasPronunciation={Boolean(lemmaPronunciationForm)}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
            className="text-3xl font-bold leading-tight"
            iconClassName="size-4"
            as="h2"
          />
          {headerBadges.length > 0 ? (
            <span data-testid="wordbank-lemma-header-badges" className="inline-flex flex-wrap gap-1.5">
              {headerBadges.map((badge) => (
                <Badge
                  key={`lemma-badge-${badge.label}`}
                  variant={badge.tone === "primary" ? "default" : "secondary"}
                  className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(headerPosTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                >
                  {badge.label}
                </Badge>
              ))}
            </span>
          ) : null}
          {selectedLemmaVerificationSuccess ? (
            <Badge
              variant="outline"
              aria-label="Gemini verification passed"
              className="border-emerald-500/60 bg-emerald-500/10 text-emerald-700"
            >
              <BadgeCheck className="mr-1 size-3.5" />
              Verified
            </Badge>
          ) : null}
          {selectedLemmaVerificationQueued ? (
            <Badge
              variant="outline"
              aria-label="Gemini verification queued"
              className="border-sky-500/60 bg-sky-500/10 text-sky-700"
            >
              <LoaderCircle className="mr-1 size-3.5 animate-spin" />
              Verifying...
            </Badge>
          ) : null}
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
                  {selectedLemmaVerificationError?.suggestedActions.length ? (
                    <span className="ml-1 text-[11px] leading-none">{selectedLemmaVerificationError.suggestedActions.length}</span>
                  ) : null}
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
                    <p className="text-muted-foreground text-xs">
                      Reviewed {formatSavedNoteTimestamp(selectedVerificationTimestamp)}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Problem</p>
                    <p className="text-sm">{selectedLemmaVerificationError.problem}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Change to implement</p>
                    <p className="text-sm">{selectedLemmaVerificationError.changeToImplement}</p>
                  </div>
                  {hasSuggestedVerificationActions(selectedLemmaVerificationError) ? (
                    <div className="space-y-1">
                      <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Suggested actions</p>
                      <div className="space-y-2">
                        {selectedLemmaVerificationError.suggestedActions.map((action, index) => (
                          <div key={`${action.action_type}-${index}`} className="space-y-2 rounded-md border p-3">
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{verificationActionTitle(action)}</p>
                              <p className="text-muted-foreground text-xs">
                                {action.reason?.trim() || verificationActionSummary(action)}
                              </p>
                              {!action.reason?.trim() ? null : (
                                <p className="text-sm">{verificationActionSummary(action)}</p>
                              )}
                            </div>
                            <Button
                              type="button"
                              size="sm"
                              className="w-full"
                              disabled={isApplyingVerificationChanges}
                              onClick={() => onApplySelectedLemmaVerificationAction(index)}
                            >
                              {isApplyingVerificationChanges ? "Applying..." : "Accept Action"}
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </PopoverContent>
          </Popover>
        </ButtonGroup>
      </div>
      {verificationStatusLine ? (
        <p className="text-muted-foreground mt-1 pl-1 text-xs">{verificationStatusLine}</p>
      ) : null}
      {headerTranslation && (showSupplementaryMetadata || selectedMeaningSection) ? (
        <p className="text-muted-foreground mt-1 pl-1 text-sm italic">{headerTranslation}</p>
      ) : null}
    </div>
  )
}

function verificationActionTitle(action: VerificationErrorDetail["suggestedActions"][number]): string {
  if (action.action_type === "fix_translation") {
    return "Fix translation"
  }
  if (action.action_type === "fix_gloss") {
    return "Fix gloss"
  }
  if (action.action_type === "move_to_meaning_section") {
    return "Move to different meaning"
  }
  if (action.action_type === "move_to_lemma") {
    return "Move to different lemma"
  }
  return "Review action"
}

function verificationActionSummary(action: VerificationErrorDetail["suggestedActions"][number]): string {
  if (action.action_type === "fix_translation") {
    return `Set translation to '${action.english_translation ?? ""}'.`
  }
  if (action.action_type === "fix_gloss") {
    return `Set gloss to '${action.gloss ?? ""}'.`
  }
  if (action.action_type === "move_to_meaning_section") {
    return `Move this entry to meaning section #${action.target_meaning_id ?? "?"}.`
  }
  if (action.action_type === "move_to_lemma") {
    const targetLemma = action.target_lemma ?? "new lemma"
    const targetMeaning = action.target_meaning_key ?? "new meaning"
    return `Move this entry to '${targetLemma}' under '${targetMeaning}'.`
  }
  return "Review the Gemini recommendation."
}

export function WordbankDetailsLoadingSkeleton() {
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-5 w-14 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <Skeleton className="h-4 w-32" />
      </div>
    </div>
  )
}
