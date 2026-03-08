import { useEffect } from "react"

import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsLoadingSkeleton, WordbankLemmaHeader } from "@/app/sections/wordbank/wordbank-lemma-header"
import { WordbankMeaningSections } from "@/app/sections/wordbank/wordbank-meaning-sections"
import { WordbankVariationGrid } from "@/app/sections/wordbank/wordbank-variation-grid"
import { ScrollArea } from "@/components/ui/scroll-area"

type WordbankDetailsViewProps = Pick<
  WordbankSectionProps,
  | "selectedLemma"
  | "selectedMeaningId"
  | "lemmaDetails"
  | "lemmaDetailsError"
  | "isLemmaDetailsLoading"
  | "showLemmaDetailsLoadingSkeleton"
  | "pronunciationLoadingByForm"
  | "onPlayPronunciation"
  | "isRegeneratingLemmaPronunciation"
  | "onRegenerateSelectedLemmaPronunciation"
  | "selectedLemmaVerificationError"
  | "hasSuggestedVerificationChanges"
  | "isApplyingVerificationChanges"
  | "onApplySelectedLemmaVerificationChanges"
>

export function WordbankDetailsView({
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  lemmaDetailsError,
  isLemmaDetailsLoading,
  showLemmaDetailsLoadingSkeleton,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  isRegeneratingLemmaPronunciation,
  onRegenerateSelectedLemmaPronunciation,
  selectedLemmaVerificationError,
  hasSuggestedVerificationChanges,
  isApplyingVerificationChanges,
  onApplySelectedLemmaVerificationChanges,
}: WordbankDetailsViewProps) {
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

  if (isLemmaDetailsLoading && showLemmaDetailsLoadingSkeleton) {
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
            onPlayPronunciation={onPlayPronunciation}
            isRegeneratingLemmaPronunciation={isRegeneratingLemmaPronunciation}
            onRegenerateSelectedLemmaPronunciation={onRegenerateSelectedLemmaPronunciation}
            selectedLemmaVerificationError={selectedLemmaVerificationError}
            hasSuggestedVerificationChanges={hasSuggestedVerificationChanges}
            isApplyingVerificationChanges={isApplyingVerificationChanges}
            onApplySelectedLemmaVerificationChanges={onApplySelectedLemmaVerificationChanges}
            showSupplementaryMetadata={!isSectioned}
          />
          {isSectioned ? (
            <WordbankMeaningSections
              lemma={lemmaDetails.lemma}
              meaningSections={meaningSections}
              selectedMeaningId={selectedMeaningId}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              onPlayPronunciation={onPlayPronunciation}
            />
          ) : (
            <WordbankVariationGrid
              variationForms={variationForms}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              onPlayPronunciation={onPlayPronunciation}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
