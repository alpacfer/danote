import type { UseAppSectionPropsParams } from "@/app/hooks/app/use-app-section-props"
import type { WordbankContext } from "@/app/hooks/app/controller/section-props-types"

export function buildWordbankSectionProps(
  context: WordbankContext,
): Pick<
  UseAppSectionPropsParams,
  | "selectedLemma"
  | "wordbankError"
  | "isWordbankLoading"
  | "lemmas"
  | "groupedWordbankLemmas"
  | "setSelectedLemma"
  | "lemmaDetails"
  | "lemmaDetailsError"
  | "isLemmaDetailsLoading"
  | "showLemmaDetailsLoadingSkeleton"
  | "pronunciationLoadingByForm"
  | "playPronunciation"
  | "isRegeneratingLemmaPronunciation"
  | "regenerateSelectedLemmaPronunciation"
  | "selectedLemmaVerificationError"
  | "hasSuggestedVerificationChanges"
  | "isApplyingVerificationChanges"
  | "applySelectedLemmaVerificationChanges"
  | "sentencebankError"
  | "isSentencebankLoading"
  | "sentences"
> {
  return {
    selectedLemma: context.selectedLemma,
    wordbankError: context.wordbankError,
    isWordbankLoading: context.isWordbankLoading,
    lemmas: context.lemmas,
    groupedWordbankLemmas: context.groupedWordbankLemmas,
    setSelectedLemma: context.setSelectedLemma,
    lemmaDetails: context.lemmaDetails,
    lemmaDetailsError: context.lemmaDetailsError,
    isLemmaDetailsLoading: context.isLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton: context.showLemmaDetailsLoadingSkeleton,
    pronunciationLoadingByForm: context.pronunciationLoadingByForm,
    playPronunciation: context.playPronunciation,
    isRegeneratingLemmaPronunciation: context.isRegeneratingLemmaPronunciation,
    regenerateSelectedLemmaPronunciation: context.regenerateSelectedLemmaPronunciation,
    selectedLemmaVerificationError: context.selectedLemmaVerificationError,
    hasSuggestedVerificationChanges: context.hasSuggestedVerificationChanges,
    isApplyingVerificationChanges: context.isApplyingVerificationChanges,
    applySelectedLemmaVerificationChanges: context.applySelectedLemmaVerificationChanges,
    sentencebankError: context.sentencebankError,
    isSentencebankLoading: context.isSentencebankLoading,
    sentences: context.sentences,
  }
}
