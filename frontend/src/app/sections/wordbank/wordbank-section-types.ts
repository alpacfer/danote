import type {
  LemmaDetailsResponse,
  VerificationOverview,
  WordbankLemma,
} from "@/app/core"

export type WordbankSectionProps = {
  selectedLemma: string | null
  selectedMeaningId: number | null
  wordbankError: string | null
  isWordbankLoading: boolean
  lemmas: WordbankLemma[]
  groupedWordbankLemmas: Array<{ letter: string; items: WordbankLemma[] }>
  unreadWordbankLemmaCounts: Map<string, number>
  onSelectLemma: (lemma: string) => void
  lemmaDetails: LemmaDetailsResponse | null
  lemmaDetailsError: string | null
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRegeneratingLemmaPronunciation: boolean
  onRegenerateSelectedLemmaPronunciation: () => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
  verificationOverview: VerificationOverview
  isApplyingVerificationChanges: boolean
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
}
