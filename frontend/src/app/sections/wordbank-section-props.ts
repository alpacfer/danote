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
  isRethinkingCategories: boolean
  rethinkCategories: (meaningId: number | null) => Promise<void>
  isCompletingMeaningVariations: boolean
  completeMeaningVariations: (meaningId: number | null) => Promise<void>
  verificationOverview: ComponentProps<typeof WordbankSection>["verificationOverview"]
  isApplyingVerificationChanges: boolean
  applyVerificationAction: (targetKey: string, actionIndex: number) => Promise<void>
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
    isRethinkingCategories: args.isRethinkingCategories,
    onRethinkCategories: (meaningId: number | null) => {
      void args.rethinkCategories(meaningId)
    },
    isCompletingMeaningVariations: args.isCompletingMeaningVariations,
    onCompleteMeaningVariations: (meaningId: number | null) => {
      void args.completeMeaningVariations(meaningId)
    },
    verificationOverview: args.verificationOverview,
    isApplyingVerificationChanges: args.isApplyingVerificationChanges,
    onApplyVerificationAction: (targetKey: string, actionIndex: number) => {
      void args.applyVerificationAction(targetKey, actionIndex)
    },
  }
}
