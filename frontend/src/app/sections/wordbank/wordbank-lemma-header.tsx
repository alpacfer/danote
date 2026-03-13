import type { LemmaDetailsResponse, VerificationErrorDetail, VerificationQueuedDetail, VerificationSuccessDetail } from "@/app/core"
import { badgesForSavedForm, corSecondaryBadgeClass, posBadgeClass } from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { WordbankVerificationPopover } from "@/app/sections/wordbank/wordbank-verification-popover"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Skeleton } from "@/components/ui/skeleton"
import { RefreshCw } from "lucide-react"

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
        </div>
        <ButtonGroup className="shrink-0">
          <ButtonGroup>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={isRegeneratingLemmaPronunciation}
              onClick={onRegenerateSelectedLemmaPronunciation}
            >
              <RefreshCw className={isRegeneratingLemmaPronunciation ? "animate-spin" : ""} />
              Regenerate Audio
            </Button>
          </ButtonGroup>
          <ButtonGroup>
            <WordbankVerificationPopover
              selectedLemmaVerificationError={selectedLemmaVerificationError}
              selectedLemmaVerificationQueued={selectedLemmaVerificationQueued}
              selectedLemmaVerificationSuccess={selectedLemmaVerificationSuccess}
              selectedVerificationTimestamp={selectedVerificationTimestamp}
              hasSuggestedVerificationActions={hasSuggestedVerificationActions}
              isApplyingVerificationChanges={isApplyingVerificationChanges}
              onApplySelectedLemmaVerificationAction={onApplySelectedLemmaVerificationAction}
            />
          </ButtonGroup>
        </ButtonGroup>
      </div>
      {headerTranslation && (showSupplementaryMetadata || selectedMeaningSection) ? (
        <p className="text-muted-foreground mt-1 pl-1 text-sm italic">{headerTranslation}</p>
      ) : null}
    </div>
  )
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
