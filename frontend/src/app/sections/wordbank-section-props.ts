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
  regeneratingPronunciationByForm: ComponentProps<typeof WordbankSection>["regeneratingPronunciationByForm"]
  playPronunciation: (form: string) => Promise<void>
  regeneratePronunciation: (form: string) => Promise<void>
  isRethinkingCategories: boolean
  rethinkCategories: (meaningId: number | null) => Promise<void>
  isCompletingMeaningVariations: boolean
  completeMeaningVariations: (meaningId: number | null) => Promise<void>
  verificationOverview: ComponentProps<typeof WordbankSection>["verificationOverview"]
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  rerunningMeaningVerificationById: Record<number, boolean>
  markVisibleVerificationNotificationsAsRead: () => void
  applyVerificationAction: (targetKey: string, actionIndex: number) => Promise<void>
  retryVerificationTarget: (targetKey: string) => Promise<void>
  rerunMeaningVerification: (meaningId: number) => Promise<void>
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
    regeneratingPronunciationByForm: args.regeneratingPronunciationByForm,
    onPlayPronunciation: (form: string) => {
      void args.playPronunciation(form)
    },
    onRegeneratePronunciation: (form: string) => {
      void args.regeneratePronunciation(form)
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
    isRetryingVerification: args.isRetryingVerification,
    rerunningMeaningVerificationById: args.rerunningMeaningVerificationById,
    onMarkVisibleVerificationNotificationsAsRead: args.markVisibleVerificationNotificationsAsRead,
    onApplyVerificationAction: (targetKey: string, actionIndex: number) => {
      void args.applyVerificationAction(targetKey, actionIndex)
    },
    onRetryVerificationTarget: (targetKey: string) => {
      void args.retryVerificationTarget(targetKey)
    },
    onRerunMeaningVerification: (meaningId: number) => {
      void args.rerunMeaningVerification(meaningId)
    },
  }
}
