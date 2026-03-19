import { useEffect } from "react"

import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsLoadingSkeleton, WordbankLemmaHeader } from "@/app/sections/wordbank/wordbank-lemma-header"
import { WordbankMeaningSections } from "@/app/sections/wordbank/wordbank-meaning-sections"
import { WordbankVariationGrid } from "@/app/sections/wordbank/wordbank-variation-grid"
import { ScrollArea } from "@/components/ui/scroll-area"

type WordbankWordPageProps = Pick<
  WordbankSectionProps,
  | "selectedLemma"
  | "selectedMeaningId"
  | "lemmaDetails"
  | "lemmaDetailsError"
  | "isLemmaDetailsLoading"
  | "showLemmaDetailsLoadingSkeleton"
  | "pronunciationLoadingByForm"
  | "regeneratingPronunciationByForm"
  | "onPlayPronunciation"
  | "onRegeneratePronunciation"
  | "isRethinkingCategories"
  | "onRethinkCategories"
  | "isCompletingMeaningVariations"
  | "onCompleteMeaningVariations"
  | "verificationOverview"
  | "isApplyingVerificationChanges"
  | "isRetryingVerification"
  | "onMarkVisibleVerificationNotificationsAsRead"
  | "onApplyVerificationAction"
  | "onRetryVerificationTarget"
>

export function WordbankWordPage({
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  lemmaDetailsError,
  isLemmaDetailsLoading,
  showLemmaDetailsLoadingSkeleton,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  isRethinkingCategories,
  onRethinkCategories,
  isCompletingMeaningVariations,
  onCompleteMeaningVariations,
  verificationOverview,
  isApplyingVerificationChanges,
  isRetryingVerification,
  onMarkVisibleVerificationNotificationsAsRead,
  onApplyVerificationAction,
  onRetryVerificationTarget,
}: WordbankWordPageProps) {
  const normalizedSelectedLemma = (lemmaDetails?.lemma ?? selectedLemma ?? "").trim().toLocaleLowerCase("da-DK")
  const variationForms = (lemmaDetails?.surface_forms ?? []).filter(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") !== normalizedSelectedLemma,
  )
  const meaningSections = lemmaDetails?.meaning_sections ?? []
  const isSectioned = Boolean(lemmaDetails?.is_sectioned)

  useEffect(() => {
    if (!selectedMeaningId || !lemmaDetails || !isSectioned) {
      return
    }
    const frameId = window.requestAnimationFrame(() => {
      const section = document.getElementById(`wordbank-meaning-${selectedMeaningId}`)
      section?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    })
    return () => {
      window.cancelAnimationFrame(frameId)
    }
  }, [isSectioned, lemmaDetails, selectedMeaningId])

  if (isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton && !lemmaDetails) {
    return <WordbankDetailsLoadingSkeleton />
  }

  if (!lemmaDetails) {
    return isLemmaDetailsLoading ? null : <p className="text-muted-foreground text-sm">No details found for this lemma.</p>
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {lemmaDetailsError ? (
        <p className="text-destructive text-sm" role="alert">
          {lemmaDetailsError}
        </p>
      ) : null}
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-3 pr-1">
          <WordbankLemmaHeader
            selectedLemma={selectedLemma ?? lemmaDetails.lemma}
            selectedMeaningId={selectedMeaningId}
            lemmaDetails={lemmaDetails}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            regeneratingPronunciationByForm={regeneratingPronunciationByForm}
            onPlayPronunciation={onPlayPronunciation}
            onRegeneratePronunciation={onRegeneratePronunciation}
            isRethinkingCategories={isRethinkingCategories}
            onRethinkCategories={onRethinkCategories}
            verificationOverview={verificationOverview}
            isApplyingVerificationChanges={isApplyingVerificationChanges}
            isRetryingVerification={isRetryingVerification}
            onMarkVisibleVerificationNotificationsAsRead={onMarkVisibleVerificationNotificationsAsRead}
            onApplyVerificationAction={onApplyVerificationAction}
            onRetryVerificationTarget={onRetryVerificationTarget}
            showSupplementaryMetadata={!isSectioned}
          />
          {isSectioned ? (
            <WordbankMeaningSections
              lemma={lemmaDetails.lemma}
              meaningSections={meaningSections}
              selectedMeaningId={selectedMeaningId}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              regeneratingPronunciationByForm={regeneratingPronunciationByForm}
              onPlayPronunciation={onPlayPronunciation}
              onRegeneratePronunciation={onRegeneratePronunciation}
              isRethinkingCategories={isRethinkingCategories}
              onRethinkCategories={onRethinkCategories}
              isCompletingMeaningVariations={isCompletingMeaningVariations}
              onCompleteMeaningVariations={onCompleteMeaningVariations}
            />
          ) : (
            <WordbankVariationGrid
              allSurfaceForms={lemmaDetails.surface_forms}
              variationForms={variationForms}
              posTag={lemmaDetails.pos_tag}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              regeneratingPronunciationByForm={regeneratingPronunciationByForm}
              onPlayPronunciation={onPlayPronunciation}
              onRegeneratePronunciation={onRegeneratePronunciation}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
