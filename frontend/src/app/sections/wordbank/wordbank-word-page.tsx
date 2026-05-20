import { useEffect, useState } from "react"

import { normalizeSearchWord } from "@/app/core"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsLoadingSkeleton, WordbankLemmaHeader } from "@/app/sections/wordbank/wordbank-lemma-header"
import { WordbankLinkedSentences } from "@/app/sections/wordbank/wordbank-linked-sentences"
import { WordbankMeaningSections } from "@/app/sections/wordbank/wordbank-meaning-sections"
import { WordbankRelatedWords } from "@/app/sections/wordbank/wordbank-related-words"
import { MeaningDeletionDialog, type MeaningDeleteTarget } from "@/app/sections/wordbank/wordbank-deletion-dialogs"
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
  | "onDeleteMeaning"
  | "generatingExampleByMeaningId"
  | "onGenerateExample"
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
  onDeleteMeaning,
  generatingExampleByMeaningId,
  onGenerateExample,
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
      showSupplementaryMetadata={false}
      onOpenPinnedTab={onOpenPinnedTab}
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
        <div className="flex flex-col gap-3 pr-1">
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
          />
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
