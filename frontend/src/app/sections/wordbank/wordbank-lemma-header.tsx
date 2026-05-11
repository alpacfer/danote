import type { LemmaDetailsResponse, VerificationChangeEntry, VerificationOverview } from "@/app/core"
import { additionalTranslationsDisplay, corSecondaryBadgeClass, normalizeSearchWord, posBadgeClass } from "@/app/core"
import { pinnedHomesForLemma } from "@/app/sections/wordbank/_shared/pinned-word-index"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { WordbankVerificationPopover } from "@/app/sections/wordbank/wordbank-verification-popover"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { AudioLines, Languages, Loader2, Sparkles } from "lucide-react"

type WordbankLemmaHeaderProps = {
  selectedLemma: string
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  isFindingAlternativeTranslations: boolean
  onFindAlternativeTranslations: (meaningId: number | null) => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
  verificationOverview: VerificationOverview
  verificationChanges: VerificationChangeEntry[]
  isLoadingVerificationChanges: boolean
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  isRevertingVerificationChange: boolean
  onMarkVisibleVerificationNotificationsAsRead: () => void
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
  onRevertVerificationChange: (changeId: number) => void
  showSupplementaryMetadata: boolean
  onOpenPinnedTab: (sentinel: string) => void
}

export function WordbankLemmaHeader({
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  isFindingAlternativeTranslations,
  onFindAlternativeTranslations,
  isRethinkingCategories,
  onRethinkCategories,
  verificationOverview,
  verificationChanges,
  isLoadingVerificationChanges,
  isApplyingVerificationChanges,
  isRetryingVerification,
  isRevertingVerificationChange,
  onMarkVisibleVerificationNotificationsAsRead,
  onApplyVerificationAction,
  onRetryVerificationTarget,
  onRevertVerificationChange,
  showSupplementaryMetadata,
  onOpenPinnedTab,
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
  const headerAdditionalTranslations = lemmaDetails.is_sectioned
    ? []
    : (selectedMeaningSection?.additional_translations ?? lemmaDetails.additional_translations ?? [])
  const headerTranslationLine = additionalTranslationsDisplay(
    headerTranslation,
    headerAdditionalTranslations,
  )
  const headerPosTag = selectedMeaningSection?.pos_tag ?? lemmaDetails.pos_tag
  const headerMorphology = selectedMeaningSection?.morphology ?? lemmaDetails.morphology
  const headerBadges = showSupplementaryMetadata
    ? wordPageBadgesForSavedForm({
        pos_tag: headerPosTag ?? null,
        morphology: headerMorphology ?? null,
        gram_raw: selectedMeaningSection?.gram_raw ?? lemmaSurfaceDetails?.gram_raw ?? null,
      })
    : []
  const pinnedHomes = pinnedHomesForLemma(lemmaDetails.lemma)
  const isRegeneratingLemma = Boolean(regeneratingPronunciationByForm[normalizeSearchWord(lemmaDetails.lemma)])
  const lemmaContextMenuItems = [
    {
      icon: isRegeneratingLemma ? <Loader2 className="animate-spin" /> : <AudioLines />,
      label: isRegeneratingLemma ? "Regenerating audio..." : "Regenerate audio",
      disabled: isRegeneratingLemma,
      onSelect: () => onRegeneratePronunciation(lemmaDetails.lemma),
    },
    ...(!lemmaDetails.is_sectioned
      ? [{
          icon: isFindingAlternativeTranslations ? <Loader2 className="animate-spin" /> : <Languages />,
          label: isFindingAlternativeTranslations ? "Finding alternative translations..." : "Find alternative translations",
          disabled: isFindingAlternativeTranslations,
          separatorBefore: true as const,
          onSelect: () => onFindAlternativeTranslations(null),
        }, {
          icon: isRethinkingCategories ? <Loader2 className="animate-spin" /> : <Sparkles />,
          label: isRethinkingCategories ? "Rethinking categories..." : "Rethink categories",
          disabled: isRethinkingCategories,
          onSelect: () => onRethinkCategories(null),
        }]
      : []),
  ]
  const isBuiltInLemma = pinnedHomes.length > 0
  const effectiveVerificationOverview = isBuiltInLemma
    ? buildBuiltInVerificationOverview(lemmaDetails.lemma)
    : verificationOverview
  const verificationTrigger = (
    <div className="shrink-0">
      <WordbankVerificationPopover
        verificationOverview={effectiveVerificationOverview}
        changes={isBuiltInLemma ? [] : verificationChanges}
        isLoadingChanges={isBuiltInLemma ? false : isLoadingVerificationChanges}
        isApplyingVerificationChanges={isBuiltInLemma ? false : isApplyingVerificationChanges}
        isRetryingVerification={isBuiltInLemma ? false : isRetryingVerification}
        isRevertingChange={isBuiltInLemma ? false : isRevertingVerificationChange}
        onOpenChange={(open) => {
          if (open && !isBuiltInLemma) {
            onMarkVisibleVerificationNotificationsAsRead()
          }
        }}
        onApplyVerificationAction={onApplyVerificationAction}
        onRetryVerificationTarget={onRetryVerificationTarget}
        onRevertChange={onRevertVerificationChange}
      />
    </div>
  )

  return (
    <div id="wordbank-lemma-header">
      {/* Lemma word + verification button. Categories, POS badges, translation,
          and pinned-home chips live inside the meaning section card(s) below so
          every word page (saved or built-in) shares the same chrome. */}
      <div className="flex items-start justify-between gap-3">
        <WordbankPronunciationWord
          form={lemmaDetails.lemma}
          playForm={lemmaPronunciationForm ?? undefined}
          hasPronunciation={Boolean(lemmaPronunciationForm)}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          contextMenuItems={lemmaContextMenuItems}
          className="text-3xl font-bold tracking-tight leading-tight"
          iconClassName="size-4"
          as="h2"
        />
        {verificationTrigger}
      </div>

      {/* POS + morphology badges */}
      {headerBadges.length > 0 ? (
        <div data-testid="wordbank-lemma-header-badges" className="mt-1.5 flex flex-wrap gap-1.5">
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
      ) : null}

      {/* Translation */}
      {headerTranslationLine && (showSupplementaryMetadata || selectedMeaningSection) ? (
        <p className="text-muted-foreground mt-2 text-base italic">{headerTranslationLine}</p>
      ) : null}

      {/* Pinned section links */}
      {showSupplementaryMetadata && pinnedHomes.length > 0 ? (
        <div data-testid="wordbank-pinned-home-card" className="mt-2 flex flex-wrap gap-1.5">
          {pinnedHomes.map((home) => (
            <Button
              key={home.sentinel}
              type="button"
              variant="outline"
              size="sm"
              className="h-auto px-2 py-0.5 text-xs"
              onClick={() => onOpenPinnedTab(home.sentinel)}
            >
              {home.pageTitle}: {home.tabTitle}
            </Button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

type WordbankDetailsLoadingSkeletonProps = {
  layout?: "root" | "sectioned"
}

export function WordbankDetailsLoadingSkeleton({ layout = "root" }: WordbankDetailsLoadingSkeletonProps) {
  const header = <WordbankHeaderLoadingSkeleton showCategoryRow={layout === "root"} />

  return (
    <div data-testid="wordbank-details-loading-skeleton" className="flex min-h-0 flex-1 flex-col gap-4">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-3 pr-1">
          {layout === "sectioned" ? (
            <>
              {header}
              <div className="grid grid-cols-2 gap-3">
                {[0, 1].map((item) => (
                  <WordbankMeaningCardLoadingSkeleton key={`wordbank-details-loading-card-${item}`} />
                ))}
              </div>
            </>
          ) : (
            <Card data-testid="wordbank-details-loading-card" className="w-1/2 py-5 border-border/70">
              <CardContent className="space-y-3">
                {header}
                <WordbankParadigmLoadingSkeleton />
              </CardContent>
            </Card>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

function WordbankHeaderLoadingSkeleton({ showCategoryRow }: { showCategoryRow: boolean }) {
  return (
    <div>
      {showCategoryRow ? (
        <div className="flex flex-wrap justify-end gap-1.5">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-24 rounded-full" />
        </div>
      ) : null}
      <div className="mt-2 flex items-start justify-between gap-3">
        <Skeleton className="h-9 w-36" />
        <Skeleton className="h-9 w-9 rounded-md" />
      </div>
      {showCategoryRow ? (
        <>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <Skeleton className="h-5 w-14 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="mt-2 h-6 w-40" />
        </>
      ) : null}
    </div>
  )
}

function WordbankMeaningCardLoadingSkeleton() {
  return (
    <Card data-testid="wordbank-details-loading-card" className="py-5 border-border/70">
      <CardContent className="space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-1.5 sm:max-w-[45%]">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-24 rounded-full" />
          </div>
        </div>
        <WordbankParadigmLoadingSkeleton />
      </CardContent>
    </Card>
  )
}

function buildBuiltInVerificationOverview(lemma: string): VerificationOverview {
  return {
    targets: [
      {
        key: `builtin::${lemma}`,
        label: lemma,
        scopeLabel: "Built-in reference",
        meaningId: null,
        storedSurfaceForm: null,
        verification: null,
        errorDetail: null,
        successDetail: {
          provider: "built_in",
          rawMessage: "Built-in reference word, no verification needed.",
          storedSurfaceForm: null,
          meaningId: null,
          verifiedAt: null,
        },
        queuedDetail: null,
      },
    ],
    queuedCount: 0,
    verifiedCount: 1,
    reviewCount: 0,
    totalSuggestedActions: 0,
  }
}

function WordbankParadigmLoadingSkeleton() {
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {[0, 1, 2].map((row) => (
          <div key={`wordbank-details-loading-row-${row}`} className="grid grid-cols-[6rem_minmax(0,1fr)] items-center gap-4 py-2">
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-28" />
          </div>
        ))}
      </div>
    </div>
  )
}
