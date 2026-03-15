import type { LemmaDetailsResponse, VerificationOverview } from "@/app/core"
import { badgesForSavedForm, corSecondaryBadgeClass, normalizeSearchWord, posBadgeClass, semanticCategoryBadgeClass } from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { WordbankVerificationPopover } from "@/app/sections/wordbank/wordbank-verification-popover"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

type WordbankLemmaHeaderProps = {
  selectedLemma: string
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
  verificationOverview: VerificationOverview
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
  showSupplementaryMetadata: boolean
}

export function WordbankLemmaHeader({
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  isRethinkingCategories,
  onRethinkCategories,
  verificationOverview,
  isApplyingVerificationChanges,
  isRetryingVerification,
  onApplyVerificationAction,
  onRetryVerificationTarget,
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
        gram_raw: selectedMeaningSection?.gram_raw ?? lemmaSurfaceDetails?.gram_raw ?? null,
      })
    : []
  const isRegeneratingLemma = Boolean(regeneratingPronunciationByForm[normalizeSearchWord(lemmaDetails.lemma)])
  const lemmaContextMenuItems = [
    {
      label: isRegeneratingLemma ? "Regenerating audio..." : "Regenerate audio",
      disabled: isRegeneratingLemma,
      onSelect: () => onRegeneratePronunciation(lemmaDetails.lemma),
    },
    ...(!lemmaDetails.is_sectioned
      ? [{
          label: isRethinkingCategories ? "Rethinking categories..." : "Rethink categories",
          disabled: isRethinkingCategories,
          onSelect: () => onRethinkCategories(null),
        }]
      : []),
  ]

  const content = (
    <div data-testid={!lemmaDetails.is_sectioned ? "wordbank-lemma-scope-card" : undefined}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <WordbankPronunciationWord
            form={lemmaDetails.lemma}
            playForm={lemmaPronunciationForm ?? undefined}
            hasPronunciation={Boolean(lemmaPronunciationForm)}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
            contextMenuItems={lemmaContextMenuItems}
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
        <div className="shrink-0">
          <WordbankVerificationPopover
            verificationOverview={verificationOverview}
            isApplyingVerificationChanges={isApplyingVerificationChanges}
            isRetryingVerification={isRetryingVerification}
            onApplyVerificationAction={onApplyVerificationAction}
            onRetryVerificationTarget={onRetryVerificationTarget}
          />
        </div>
      </div>
      {headerTranslation && (showSupplementaryMetadata || selectedMeaningSection) ? (
        <p className="text-muted-foreground mt-1 pl-1 text-sm italic">{headerTranslation}</p>
      ) : null}
      {lemmaDetails.categories && lemmaDetails.categories.length > 0 ? (
        <div data-testid="wordbank-lemma-category-badges" className="mt-2 flex flex-wrap justify-end gap-1.5">
          {lemmaDetails.categories.map((category) => (
            <Badge
              key={`lemma-category-${category}`}
              variant="outline"
              className={`text-xs ${semanticCategoryBadgeClass(category)}`.trim()}
            >
              {category}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  )

  if (lemmaDetails.is_sectioned) {
    return content
  }

  return content
}

export function WordbankDetailsLoadingSkeleton() {
  return (
    <div data-testid="wordbank-details-loading-skeleton" className="space-y-4">
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Skeleton className="h-9 w-36" />
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-9 w-12 rounded-md" />
        </div>
        <div className="flex flex-wrap justify-end gap-1.5">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-24 rounded-full" />
        </div>
      </div>
      {[0, 1, 2].map((item) => (
        <div
          key={`wordbank-details-loading-card-${item}`}
          data-testid="wordbank-details-loading-card"
          className="space-y-3 rounded-md border border-border/70 p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Skeleton className="h-5 w-6 rounded-full" />
            <Skeleton className="h-6 w-28" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-44" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-36" />
          </div>
        </div>
      ))}
    </div>
  )
}
