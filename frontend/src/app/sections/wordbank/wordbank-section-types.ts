import type {
  CompleteVariationsResponse,
  LemmaDetailsResponse,
  SearchSaveSeed,
  SentencebankSentence,
  VerificationChangeEntry,
  VerificationOverview,
  WordbankLemma,
} from "@/app/core"

export type WordbankSectionProps = {
  selectedLemma: string | null
  selectedMeaningId: number | null
  filters: import("@/app/sections/wordbank/wordbank-list-filters").WordbankFilterState
  onFiltersChange: (filters: import("@/app/sections/wordbank/wordbank-list-filters").WordbankFilterState) => void
  onApplyFilterAndNavigateBack: (filters: import("@/app/sections/wordbank/wordbank-list-filters").WordbankFilterState) => void
  wordbankError: string | null
  isWordbankLoading: boolean
  lemmas: WordbankLemma[]
  groupedWordbankLemmas: Array<{ letter: string; items: WordbankLemma[] }>
  unreadWordbankLemmaCounts: Map<string, number>
  onSelectLemma: (lemma: string) => void
  onOpenPinnedWord: (lemma: string) => void
  onOpenPinnedTab: (sentinel: string) => void
  lemmaDetails: LemmaDetailsResponse | null
  lemmaDetailsError: string | null
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  isFindingAlternativeTranslations: boolean
  onFindAlternativeTranslations: (meaningId: number | null) => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
  isCompletingMeaningVariations: boolean
  onCompleteMeaningVariations: (meaningId: number | null) => Promise<CompleteVariationsResponse | null>
  onDeleteMeaning: (meaningId: number) => void
  onDeleteLemma: (lemma: string) => void
  generatingExampleByMeaningId: Record<number, boolean>
  onGenerateExample: (meaningId: number, tense?: import("@/app/core/morphology").VerbFormLabel) => void
  generatingStaticExampleByLemma: Record<string, boolean>
  onGenerateStaticExample: (lemma: string) => void
  sentences: SentencebankSentence[]
  verificationOverview: VerificationOverview
  verificationChanges: VerificationChangeEntry[]
  isLoadingVerificationChanges: boolean
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  isRevertingVerificationChange: boolean
  rerunningMeaningVerificationById: Record<number, boolean>
  onMarkVisibleVerificationNotificationsAsRead: () => void
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
  onRerunMeaningVerification: (meaningId: number) => void
  onRevertVerificationChange: (changeId: number) => void
  onSaveRelatedWordFromSearchSeed: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
  onOpenRelatedWordTarget: (lemma: string, meaningId: number | null) => void
  onOpenSentence?: (id: number) => void
}
