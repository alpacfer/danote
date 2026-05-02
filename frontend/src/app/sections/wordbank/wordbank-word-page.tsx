import { useEffect } from "react"

import { normalizeSearchWord } from "@/app/core"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsLoadingSkeleton, WordbankLemmaHeader } from "@/app/sections/wordbank/wordbank-lemma-header"
import { WordbankLinkedSentences } from "@/app/sections/wordbank/wordbank-linked-sentences"
import { WordbankMeaningSections } from "@/app/sections/wordbank/wordbank-meaning-sections"
import { WordbankRelatedWords } from "@/app/sections/wordbank/wordbank-related-words"
import { WordbankVariationGrid } from "@/app/sections/wordbank/wordbank-variation-grid"
import { Card, CardContent } from "@/components/ui/card"
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
  | "isFindingAlternativeTranslations"
  | "onFindAlternativeTranslations"
  | "isRethinkingCategories"
  | "onRethinkCategories"
  | "isCompletingMeaningVariations"
  | "onCompleteMeaningVariations"
  | "verificationOverview"
  | "verificationChanges"
  | "isLoadingVerificationChanges"
  | "isApplyingVerificationChanges"
  | "isRetryingVerification"
  | "isRevertingVerificationChange"
  | "rerunningMeaningVerificationById"
  | "onMarkVisibleVerificationNotificationsAsRead"
  | "onApplyVerificationAction"
  | "onRetryVerificationTarget"
  | "onRerunMeaningVerification"
  | "onRevertVerificationChange"
  | "onSaveRelatedWordFromSearchSeed"
  | "onOpenRelatedWordTarget"
  | "onOpenSentence"
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
  isFindingAlternativeTranslations,
  onFindAlternativeTranslations,
  isRethinkingCategories,
  onRethinkCategories,
  isCompletingMeaningVariations,
  onCompleteMeaningVariations,
  verificationOverview,
  verificationChanges,
  isLoadingVerificationChanges,
  isApplyingVerificationChanges,
  isRetryingVerification,
  isRevertingVerificationChange,
  rerunningMeaningVerificationById,
  onMarkVisibleVerificationNotificationsAsRead,
  onApplyVerificationAction,
  onRetryVerificationTarget,
  onRerunMeaningVerification,
  onRevertVerificationChange,
  onSaveRelatedWordFromSearchSeed,
  onOpenRelatedWordTarget,
  onOpenSentence,
}: WordbankWordPageProps) {
  const normalizedRequestedLemma = normalizeSearchWord(selectedLemma ?? "")
  const normalizedLoadedLemma = normalizeSearchWord(lemmaDetails?.lemma ?? "")
  const hasMatchingLemmaDetails = !normalizedRequestedLemma || normalizedRequestedLemma === normalizedLoadedLemma
  const activeLemmaDetails = hasMatchingLemmaDetails ? lemmaDetails : null
  const normalizedSelectedLemma = (activeLemmaDetails?.lemma ?? selectedLemma ?? "").trim().toLocaleLowerCase("da-DK")
  const variationForms = (activeLemmaDetails?.surface_forms ?? []).filter(
    (form) => form.form.trim().toLocaleLowerCase("da-DK") !== normalizedSelectedLemma,
  )
  const meaningSections = activeLemmaDetails?.meaning_sections ?? []
  const isSectioned = Boolean(activeLemmaDetails?.is_sectioned)

  useEffect(() => {
    if (!selectedMeaningId || !activeLemmaDetails || !isSectioned) {
      return
    }
    const frameId = window.requestAnimationFrame(() => {
      const section = document.getElementById(`wordbank-meaning-${selectedMeaningId}`)
      section?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    })
    return () => {
      window.cancelAnimationFrame(frameId)
    }
  }, [activeLemmaDetails, isSectioned, selectedMeaningId])

  if (isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton && !activeLemmaDetails) {
    return <WordbankDetailsLoadingSkeleton />
  }

  if (!activeLemmaDetails) {
    return isLemmaDetailsLoading ? null : <p className="text-muted-foreground text-sm">No details found for this lemma.</p>
  }

  const lemmaHeader = (
    <WordbankLemmaHeader
      selectedLemma={selectedLemma ?? activeLemmaDetails.lemma}
      selectedMeaningId={selectedMeaningId}
      lemmaDetails={activeLemmaDetails}
      pronunciationLoadingByForm={pronunciationLoadingByForm}
      regeneratingPronunciationByForm={regeneratingPronunciationByForm}
      onPlayPronunciation={onPlayPronunciation}
      onRegeneratePronunciation={onRegeneratePronunciation}
      isFindingAlternativeTranslations={isFindingAlternativeTranslations}
      onFindAlternativeTranslations={onFindAlternativeTranslations}
      isRethinkingCategories={isRethinkingCategories}
      onRethinkCategories={onRethinkCategories}
      verificationOverview={verificationOverview}
      verificationChanges={verificationChanges}
      isLoadingVerificationChanges={isLoadingVerificationChanges}
      isApplyingVerificationChanges={isApplyingVerificationChanges}
      isRetryingVerification={isRetryingVerification}
      isRevertingVerificationChange={isRevertingVerificationChange}
      onMarkVisibleVerificationNotificationsAsRead={onMarkVisibleVerificationNotificationsAsRead}
      onApplyVerificationAction={onApplyVerificationAction}
      onRetryVerificationTarget={onRetryVerificationTarget}
      onRevertVerificationChange={onRevertVerificationChange}
      showSupplementaryMetadata={!isSectioned}
    />
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {lemmaDetailsError ? (
        <p className="text-destructive text-sm" role="alert">
          {lemmaDetailsError}
        </p>
      ) : null}
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-3 pr-1">
          {isSectioned ? (
            <>
              {lemmaHeader}
              <WordbankMeaningSections
                lemma={activeLemmaDetails.lemma}
                lemmaSurfaceForms={activeLemmaDetails.surface_forms}
                meaningSections={meaningSections}
                selectedMeaningId={selectedMeaningId}
                pronunciationLoadingByForm={pronunciationLoadingByForm}
                regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                onPlayPronunciation={onPlayPronunciation}
                onRegeneratePronunciation={onRegeneratePronunciation}
                isFindingAlternativeTranslations={isFindingAlternativeTranslations}
                onFindAlternativeTranslations={onFindAlternativeTranslations}
                isRethinkingCategories={isRethinkingCategories}
                onRethinkCategories={onRethinkCategories}
                isCompletingMeaningVariations={isCompletingMeaningVariations}
                onCompleteMeaningVariations={onCompleteMeaningVariations}
                rerunningMeaningVerificationById={rerunningMeaningVerificationById}
                onRerunMeaningVerification={onRerunMeaningVerification}
              />
            </>
          ) : (
            <Card data-testid="wordbank-lemma-scope-card" className="w-1/2 py-5">
              <CardContent className="space-y-3">
                {lemmaHeader}
                <WordbankVariationGrid
                  allSurfaceForms={activeLemmaDetails.surface_forms}
                  variationForms={variationForms}
                  posTag={activeLemmaDetails.pos_tag}
                  pronunciationLoadingByForm={pronunciationLoadingByForm}
                  regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                  onPlayPronunciation={onPlayPronunciation}
                  onRegeneratePronunciation={onRegeneratePronunciation}
                />
              </CardContent>
            </Card>
          )}
          <WordbankRelatedWords
            relatedWords={activeLemmaDetails.related_words}
            onSaveRelatedWordFromSearchSeed={onSaveRelatedWordFromSearchSeed}
            onOpenRelatedWordTarget={onOpenRelatedWordTarget}
          />
          <WordbankLinkedSentences
            linkedSentences={activeLemmaDetails.linked_sentences}
            onOpenSentence={onOpenSentence}
          />
        </div>
      </ScrollArea>
    </div>
  )
}
