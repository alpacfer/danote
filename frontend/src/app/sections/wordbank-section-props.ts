import { type ComponentProps } from "react"

import type { CompleteVariationsResponse } from "@/app/core"
import { WordbankSection } from "@/app/sections/wordbank-section"

export type WordbankSectionAdapterArgs = {
  selectedLemma: ComponentProps<typeof WordbankSection>["selectedLemma"]
  selectedMeaningId: ComponentProps<typeof WordbankSection>["selectedMeaningId"]
  filters: ComponentProps<typeof WordbankSection>["filters"]
  onFiltersChange: ComponentProps<typeof WordbankSection>["onFiltersChange"]
  onApplyFilterAndNavigateBack: ComponentProps<typeof WordbankSection>["onApplyFilterAndNavigateBack"]
  wordbankError: ComponentProps<typeof WordbankSection>["wordbankError"]
  isWordbankLoading: boolean
  lemmas: ComponentProps<typeof WordbankSection>["lemmas"]
  groupedWordbankLemmas: ComponentProps<typeof WordbankSection>["groupedWordbankLemmas"]
  unreadWordbankLemmaCounts: ComponentProps<typeof WordbankSection>["unreadWordbankLemmaCounts"]
  setSelectedLemma: (lemma: string | null) => void
  openWordbankLemmaRaw: (lemma: string) => void
  openWordbankPinnedTab: (sentinel: string) => void
  lemmaDetails: ComponentProps<typeof WordbankSection>["lemmaDetails"]
  lemmaDetailsError: ComponentProps<typeof WordbankSection>["lemmaDetailsError"]
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: ComponentProps<typeof WordbankSection>["pronunciationLoadingByForm"]
  regeneratingPronunciationByForm: ComponentProps<typeof WordbankSection>["regeneratingPronunciationByForm"]
  playPronunciation: (form: string) => Promise<void>
  regeneratePronunciation: (form: string) => Promise<void>
  isFindingAlternativeTranslations: boolean
  findAlternativeTranslations: (meaningId: number | null) => Promise<void>
  isRethinkingCategories: boolean
  rethinkCategories: (meaningId: number | null) => Promise<void>
  isCompletingMeaningVariations: boolean
  completeMeaningVariations: (meaningId: number | null) => Promise<CompleteVariationsResponse | null>
  deleteMeaning: (meaningId: number) => Promise<void>
  deleteLemma: (lemma: string) => Promise<void>
  generatingExampleByMeaningId: Record<number, boolean>
  generateExampleForMeaning: (storedLemma: string, meaningId: number, tenseLabel?: string) => Promise<void>
  generatingStaticExampleByLemma: Record<string, boolean>
  generateStaticExampleForLemma: (storedLemma: string) => Promise<void>
  sentences: ComponentProps<typeof WordbankSection>["sentences"]
  verificationOverview: ComponentProps<typeof WordbankSection>["verificationOverview"]
  verificationChanges: ComponentProps<typeof WordbankSection>["verificationChanges"]
  isLoadingVerificationChanges: boolean
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  isRevertingVerificationChange: boolean
  rerunningMeaningVerificationById: Record<number, boolean>
  markVisibleVerificationNotificationsAsRead: () => void
  applyVerificationAction: (targetKey: string, actionIndex: number) => Promise<void>
  retryVerificationTarget: (targetKey: string) => Promise<void>
  rerunMeaningVerification: (meaningId: number) => Promise<void>
  revertVerificationChange: (changeId: number) => Promise<void>
  saveRelatedWordFromSearchSeed: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: import("@/app/core").SearchSaveSeed | null,
  ) => Promise<string | null>
  openRelatedWordTarget: (lemma: string, meaningId: number | null) => void
  openSentence?: (id: number) => void
}

export function buildWordbankSectionProps(
  args: WordbankSectionAdapterArgs,
): ComponentProps<typeof WordbankSection> {
  return {
    selectedLemma: args.selectedLemma,
    selectedMeaningId: args.selectedMeaningId,
    filters: args.filters,
    onFiltersChange: args.onFiltersChange,
    onApplyFilterAndNavigateBack: args.onApplyFilterAndNavigateBack,
    wordbankError: args.wordbankError,
    isWordbankLoading: args.isWordbankLoading,
    lemmas: args.lemmas,
    groupedWordbankLemmas: args.groupedWordbankLemmas,
    unreadWordbankLemmaCounts: args.unreadWordbankLemmaCounts,
    onSelectLemma: args.setSelectedLemma,
    onOpenPinnedWord: args.openWordbankLemmaRaw,
    onOpenPinnedTab: args.openWordbankPinnedTab,
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
    isFindingAlternativeTranslations: args.isFindingAlternativeTranslations,
    onFindAlternativeTranslations: (meaningId: number | null) => {
      void args.findAlternativeTranslations(meaningId)
    },
    isRethinkingCategories: args.isRethinkingCategories,
    onRethinkCategories: (meaningId: number | null) => {
      void args.rethinkCategories(meaningId)
    },
    isCompletingMeaningVariations: args.isCompletingMeaningVariations,
    onCompleteMeaningVariations: args.completeMeaningVariations,
    onDeleteMeaning: (meaningId: number) => {
      void args.deleteMeaning(meaningId)
    },
    onDeleteLemma: (lemma: string) => {
      void args.deleteLemma(lemma)
    },
    generatingExampleByMeaningId: args.generatingExampleByMeaningId,
    onGenerateExample: (meaningId: number, tense?: import("@/app/core/morphology").VerbFormLabel) => {
      if (args.selectedLemma) {
        void args.generateExampleForMeaning(args.selectedLemma, meaningId, tense)
      }
    },
    generatingStaticExampleByLemma: args.generatingStaticExampleByLemma,
    onGenerateStaticExample: (lemma: string) => {
      void args.generateStaticExampleForLemma(lemma)
    },
    sentences: args.sentences,
    verificationOverview: args.verificationOverview,
    verificationChanges: args.verificationChanges,
    isLoadingVerificationChanges: args.isLoadingVerificationChanges,
    isApplyingVerificationChanges: args.isApplyingVerificationChanges,
    isRetryingVerification: args.isRetryingVerification,
    isRevertingVerificationChange: args.isRevertingVerificationChange,
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
    onRevertVerificationChange: (changeId: number) => {
      void args.revertVerificationChange(changeId)
    },
    onSaveRelatedWordFromSearchSeed: args.saveRelatedWordFromSearchSeed,
    onOpenRelatedWordTarget: args.openRelatedWordTarget,
    onOpenSentence: args.openSentence,
  }
}
