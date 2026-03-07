import { type ComponentProps } from "react"

import { WordbankSection } from "@/app/sections/wordbank-section"

export type WordbankSectionAdapterArgs = {
  selectedLemma: ComponentProps<typeof WordbankSection>["selectedLemma"]
  wordbankError: ComponentProps<typeof WordbankSection>["wordbankError"]
  isWordbankLoading: boolean
  lemmas: ComponentProps<typeof WordbankSection>["lemmas"]
  groupedWordbankLemmas: ComponentProps<typeof WordbankSection>["groupedWordbankLemmas"]
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
  hasSuggestedVerificationChanges: ComponentProps<typeof WordbankSection>["hasSuggestedVerificationChanges"]
  isApplyingVerificationChanges: boolean
  applySelectedLemmaVerificationChanges: () => Promise<void>
}

export function buildWordbankSectionProps(
  args: WordbankSectionAdapterArgs,
): ComponentProps<typeof WordbankSection> {
  return {
    selectedLemma: args.selectedLemma,
    wordbankError: args.wordbankError,
    isWordbankLoading: args.isWordbankLoading,
    lemmas: args.lemmas,
    groupedWordbankLemmas: args.groupedWordbankLemmas,
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
    hasSuggestedVerificationChanges: args.hasSuggestedVerificationChanges,
    isApplyingVerificationChanges: args.isApplyingVerificationChanges,
    onApplySelectedLemmaVerificationChanges: () => {
      void args.applySelectedLemmaVerificationChanges()
    },
  }
}
