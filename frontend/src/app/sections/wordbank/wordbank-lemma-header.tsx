import type { LemmaDetailsResponse, VerificationChangeEntry, VerificationOverview } from "@/app/core"
import {
  additionalTranslationsDisplay,
  corSecondaryBadgeClass,
  isMultiWordLemma,
  normalizeSearchWord,
  posBadgeClass,
  semanticCategoryBadgeClass,
} from "@/app/core"
import { pinnedHomesForLemma } from "@/app/sections/wordbank/_shared/pinned-word-index"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { applyPrimaryBadgeLabelOverride, primaryPosBadgeOverride } from "@/app/sections/wordbank/wordbank-primary-pos-badge"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { WordbankVerificationPopover } from "@/app/sections/wordbank/wordbank-verification-popover"
import { wordViewTransitionName } from "@/app/sections/wordbank/wordbank-view-transition"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ScrollableBadgeRow } from "@/components/ui/scrollable-badge-row"
import { Skeleton } from "@/components/ui/skeleton"
import { AudioLines, Bookmark, Languages, Loader2, Sparkles } from "lucide-react"

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
  onOpenPinnedTab: (sentinel: string) => void
  onApplyFilterAndNavigateBack?: (type: "pos" | "category", value: string) => void
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
  onOpenPinnedTab,
  onApplyFilterAndNavigateBack,
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
    : lemmaDetails.english_translation
  const headerAdditionalTranslations = lemmaDetails.is_sectioned
    ? []
    : lemmaDetails.additional_translations ?? []
  const headerTranslationLine = additionalTranslationsDisplay(
    headerTranslation,
    headerAdditionalTranslations,
  )
  const headerPosTag = selectedMeaningSection?.pos_tag ?? lemmaDetails.pos_tag
  const headerMorphology = selectedMeaningSection?.morphology ?? lemmaDetails.morphology
  const headerBadges = lemmaDetails.is_sectioned
    ? []
    : applyPrimaryBadgeLabelOverride(
        wordPageBadgesForSavedForm({
          pos_tag: headerPosTag ?? null,
          morphology: headerMorphology ?? null,
          gram_raw: selectedMeaningSection?.gram_raw ?? lemmaSurfaceDetails?.gram_raw ?? null,
          // Pass the lemma so multi-word entries ("se ud", "passe på") render the
          // "Phrasal verb" badge instead of "Verb" in the page header.
          lemma: lemmaDetails.lemma,
        }),
        { posTag: headerPosTag ?? null, morphology: headerMorphology ?? null, lemma: lemmaDetails.lemma },
      )
  const headerCategories = lemmaDetails.is_sectioned ? [] : lemmaDetails.categories ?? []
  const referenceLinks = lemmaDetails.reference_links ?? []
  const headerPosBadgeOverride = primaryPosBadgeOverride({
    posTag: headerPosTag ?? null,
    morphology: headerMorphology ?? null,
    lemma: lemmaDetails.lemma,
  })
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
    <Card
      id="wordbank-lemma-header"
      className="gap-4 py-4"
      data-material="meaning"
      data-paper-stock
      data-grid-anchor="rule"
      data-grid-height="unit"
      style={{ viewTransitionName: wordViewTransitionName(lemmaDetails.lemma) }}
    >
      <CardHeader className="grid-rows-1 gap-2 px-4 md:px-6">
      <div className="flex min-h-8 items-start justify-between gap-3">
        <WordbankPronunciationWord
          form={lemmaDetails.lemma}
          playForm={lemmaPronunciationForm ?? undefined}
          hasPronunciation={Boolean(lemmaPronunciationForm)}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          contextMenuItems={lemmaContextMenuItems}
          className="font-lexical text-3xl leading-8 font-semibold tracking-tight"
          iconClassName="size-4"
          as="h2"
        />
        {verificationTrigger}
      </div>

      {/* POS + morphology badges */}
      {headerBadges.length > 0 || headerCategories.length > 0 ? (
        <ScrollableBadgeRow
          className="order-2 md:order-none"
          fadeFromClass="from-material-meaning"
          testId="wordbank-lemma-header-badges"
        >
          {headerBadges.map((badge) => {
            const isWordType = badge.tone === "primary"
            const pinnedSentinel = isWordType ? headerPosBadgeOverride?.pinnedSentinel ?? null : null
            const isClickable = isWordType && Boolean(pinnedSentinel ? onOpenPinnedTab : onApplyFilterAndNavigateBack)
            const handleClick = !isClickable
              ? undefined
              : pinnedSentinel
                ? () => onOpenPinnedTab(pinnedSentinel)
                : () => onApplyFilterAndNavigateBack!("pos", isMultiWordLemma(lemmaDetails.lemma) ? (badge.label === "Phrasal verb" ? "PHRASAL_VERB" : "IDIOM") : headerPosTag ?? "")

            return (
              <Badge
                key={`lemma-badge-${badge.label}`}
                variant={badge.tone === "primary" ? "default" : "secondary"}
                className={`shrink-0 text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(badge.label === "HV Word" ? "HV_WORD" : headerPosTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`} ${
                  isClickable ? "cursor-pointer hover:scale-105 transition-transform" : ""
                }`.trim()}
                onClick={handleClick}
                aria-label={badge.tone === "primary" ? badge.label : undefined}
              >
                {badge.label}
              </Badge>
            )
          })}
          {headerCategories.map((category) => (
            <Badge
              key={`lemma-category-${category}`}
              variant="outline"
              className={`shrink-0 text-xs ${semanticCategoryBadgeClass(category)}`}
              onClick={
                onApplyFilterAndNavigateBack
                  ? () => onApplyFilterAndNavigateBack("category", category)
                  : undefined
              }
            >
              {category}
            </Badge>
          ))}
        </ScrollableBadgeRow>
      ) : null}

      {/* Translation */}
      {headerTranslationLine ? (
        <p className="text-muted-foreground order-1 min-h-6 text-base leading-6 italic md:order-none">
          {headerTranslationLine}
        </p>
      ) : null}
      {referenceLinks.length > 0 ? (
        <div className="flex flex-wrap gap-2" aria-label="Reference bookmarks">
          {referenceLinks.map((link) => (
            <Button
              key={`${link.page_id}-${link.tab_id}`}
              type="button"
              variant="secondary"
              size="xs"
              onClick={() => onOpenPinnedTab(link.sentinel)}
            >
              <Bookmark data-icon="inline-start" />
              {link.page_title}
            </Button>
          ))}
        </div>
      ) : null}
      </CardHeader>
    </Card>
  )
}

type WordbankDetailsLoadingSkeletonProps = {
  layout?: "root" | "sectioned"
}

export function WordbankDetailsLoadingSkeleton({ layout = "root" }: WordbankDetailsLoadingSkeletonProps) {
  const header = <WordbankHeaderLoadingSkeleton showCategoryRow={layout === "root"} />

  return (
    <div data-testid="wordbank-details-loading-skeleton" className="flex min-h-0 flex-1 flex-col gap-4">
        <div className="flex flex-col gap-4">
          {layout === "sectioned" ? (
            <>
              {header}
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {[0, 1].map((item) => (
                  <WordbankMeaningCardLoadingSkeleton key={`wordbank-details-loading-card-${item}`} />
                ))}
              </div>
            </>
          ) : (
            <Card data-testid="wordbank-details-loading-card" className="w-full py-5 border-border/70 md:w-1/2">
              <CardContent className="space-y-3">
                {header}
                <WordbankParadigmLoadingSkeleton />
              </CardContent>
            </Card>
          )}
        </div>
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
