import { type ComponentProps } from "react"

import { WordbankSection } from "@/app/sections/wordbank-section"

export type WordbankSectionAdapterArgs = {
  selectedLemma: ComponentProps<typeof WordbankSection>["selectedLemma"]
  selectedMeaningId: ComponentProps<typeof WordbankSection>["selectedMeaningId"]
  wordbankError: ComponentProps<typeof WordbankSection>["wordbankError"]
  isWordbankLoading: boolean
  lemmas: ComponentProps<typeof WordbankSection>["lemmas"]
  groupedWordbankLemmas: ComponentProps<typeof WordbankSection>["groupedWordbankLemmas"]
  unreadWordbankLemmaCounts: ComponentProps<typeof WordbankSection>["unreadWordbankLemmaCounts"]
  setSelectedLemma: (lemma: string | null) => void
  lemmaDetails: ComponentProps<typeof WordbankSection>["lemmaDetails"]
  lemmaDetailsError: ComponentProps<typeof WordbankSection>["lemmaDetailsError"]
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: ComponentProps<typeof WordbankSection>["pronunciationLoadingByForm"]
  playPronunciation: (form: string) => Promise<void>
  isRegeneratingLemmaPronunciation: boolean
  regenerateSelectedLemmaPronunciation: () => Promise<void>
  selectedLemmaVerificationError: ComponentProps<typeof WordbankSection>["selectedLemmaVerificationError"]
  selectedLemmaVerificationSuccess: ComponentProps<typeof WordbankSection>["selectedLemmaVerificationSuccess"]
  hasSuggestedVerificationActions: ComponentProps<typeof WordbankSection>["hasSuggestedVerificationActions"]
  isApplyingVerificationChanges: boolean
  applySelectedLemmaVerificationAction: (actionIndex: number) => Promise<void>
}

export function buildWordbankSectionProps(
  args: WordbankSectionAdapterArgs,
): ComponentProps<typeof WordbankSection> {
  return {
    selectedLemma: args.selectedLemma,
    selectedMeaningId: args.selectedMeaningId,
    wordbankError: args.wordbankError,
    isWordbankLoading: args.isWordbankLoading,
    lemmas: args.lemmas,
    groupedWordbankLemmas: args.groupedWordbankLemmas,
    unreadWordbankLemmaCounts: args.unreadWordbankLemmaCounts,
    onSelectLemma: args.setSelectedLemma,
    lemmaDetails: args.lemmaDetails,
    lemmaDetailsError: args.lemmaDetailsError,
    isLemmaDetailsLoading: args.isLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton: args.showLemmaDetailsLoadingSkeleton,
    pronunciationLoadingByForm: args.pronunciationLoadingByForm,
    onPlayPronunciation: (form: string) => {
      void args.playPronunciation(form)
    },
    isRegeneratingLemmaPronunciation: args.isRegeneratingLemmaPronunciation,
    onRegenerateSelectedLemmaPronunciation: () => {
      void args.regenerateSelectedLemmaPronunciation()
    },
    selectedLemmaVerificationError: args.selectedLemmaVerificationError,
    selectedLemmaVerificationSuccess: args.selectedLemmaVerificationSuccess,
    hasSuggestedVerificationActions: args.hasSuggestedVerificationActions,
    isApplyingVerificationChanges: args.isApplyingVerificationChanges,
    onApplySelectedLemmaVerificationAction: (actionIndex: number) => {
      void args.applySelectedLemmaVerificationAction(actionIndex)
    },
  }
}
