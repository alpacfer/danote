import { useEffect, useState } from "react"

import { normalizeSearchWord } from "@/app/core"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsLoadingSkeleton, WordbankLemmaHeader } from "@/app/sections/wordbank/wordbank-lemma-header"
import { WordbankLinkedSentences } from "@/app/sections/wordbank/wordbank-linked-sentences"
import { WordbankMeaningSections } from "@/app/sections/wordbank/wordbank-meaning-sections"
import { WordbankRelatedWords } from "@/app/sections/wordbank/wordbank-related-words"
import { MeaningDeletionDialog, type MeaningDeleteTarget } from "@/app/sections/wordbank/wordbank-deletion-dialogs"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MessageSquareQuote } from "lucide-react"

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
  | "onDeleteMeaning"
  | "generatingExampleByMeaningId"
  | "onGenerateExample"
  | "generatingStaticExampleByLemma"
  | "onGenerateStaticExample"
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
  | "onOpenPinnedTab"
> & {
  onApplyFilterAndNavigateBack?: (type: "pos" | "category", value: string) => void
}

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
  onDeleteMeaning,
  generatingExampleByMeaningId,
  onGenerateExample,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
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
  onOpenPinnedTab,
  onApplyFilterAndNavigateBack,
}: WordbankWordPageProps) {
  const [meaningToDelete, setMeaningToDelete] = useState<MeaningDeleteTarget | null>(null)
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
  const renderedMeaningSections = isSectioned ? meaningSections : activeLemmaDetails ? [
    {
      id: 0,
      meaning_key: "root",
      dictionary_status: activeLemmaDetails.dictionary_status,
      gloss: null,
      english_translation: activeLemmaDetails.english_translation,
      additional_translations: activeLemmaDetails.additional_translations ?? [],
      gloss_translation: null,
      pos_tag: activeLemmaDetails.pos_tag,
      morphology: activeLemmaDetails.morphology,
      gram_raw: null,
      categories: activeLemmaDetails.categories ?? [],
      reference_links: activeLemmaDetails.reference_links ?? [],
      verification: activeLemmaDetails.verification ?? null,
      surface_forms: variationForms,
    },
  ] : []
  const exampleMeaningId = selectedMeaningId
    ?? meaningSections.find((section) => section.id > 0)?.id
    ?? null

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
    return <WordbankDetailsLoadingSkeleton layout={selectedMeaningId ? "sectioned" : "root"} />
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
      onOpenPinnedTab={onOpenPinnedTab}
      onApplyFilterAndNavigateBack={onApplyFilterAndNavigateBack}
    />
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4" data-grid-page="wordbank-detail">
      {lemmaDetailsError ? (
        <p className="text-destructive text-sm" role="alert">
          {lemmaDetailsError}
        </p>
      ) : null}
        <div className="flex flex-col gap-4">
          {lemmaHeader}
          <WordbankMeaningSections
            lemma={activeLemmaDetails.lemma}
            lemmaSurfaceForms={activeLemmaDetails.surface_forms}
            meaningSections={renderedMeaningSections}
            selectedMeaningId={isSectioned ? selectedMeaningId : null}
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
            onRequestDeleteMeaning={setMeaningToDelete}
            generatingExampleByMeaningId={generatingExampleByMeaningId}
            onGenerateExample={onGenerateExample}
            rerunningMeaningVerificationById={rerunningMeaningVerificationById}
            onRerunMeaningVerification={onRerunMeaningVerification}
            onOpenPinnedTab={onOpenPinnedTab}
            onApplyFilterAndNavigateBack={onApplyFilterAndNavigateBack}
          />
          {(activeLemmaDetails.linked_sentences?.length ?? 0) === 0 ? (
            <Card
              className="max-md:min-h-52"
              data-material="sentence"
              data-grid-anchor="unit"
              data-grid-height="unit"
            >
              <CardHeader className="gap-2 px-4 md:px-6">
                <CardTitle className="text-base">A sentence is waiting to be collected</CardTitle>
              </CardHeader>
              <CardContent className="flex min-h-14 flex-wrap items-center justify-between gap-4 px-4 md:px-6">
                <p className="text-muted-foreground max-w-xl text-sm leading-6">
                  Generate an example, review it, and save it as the first clipping for this word.
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={
                    exampleMeaningId !== null
                      ? Boolean(generatingExampleByMeaningId[exampleMeaningId])
                      : Boolean(generatingStaticExampleByLemma[activeLemmaDetails.lemma])
                  }
                  onClick={() => {
                    if (exampleMeaningId !== null) {
                      onGenerateExample(exampleMeaningId)
                    } else {
                      onGenerateStaticExample(activeLemmaDetails.lemma)
                    }
                  }}
                >
                  <MessageSquareQuote data-icon="inline-start" />
                  Generate example
                </Button>
              </CardContent>
            </Card>
          ) : null}
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
      <MeaningDeletionDialog
        meaning={meaningToDelete}
        onOpenChange={(open) => {
          if (!open) setMeaningToDelete(null)
        }}
        onConfirm={(meaningId) => {
          onDeleteMeaning(meaningId)
          setMeaningToDelete(null)
        }}
      />
    </div>
  )
}
