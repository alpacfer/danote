import type {
  LemmaDetailsResponse,
  VerificationErrorDetail,
  WordbankLemma,
} from "@/app/core"

export type WordbankSectionProps = {
  selectedLemma: string | null
  selectedMeaningId: number | null
  wordbankError: string | null
  isWordbankLoading: boolean
  lemmas: WordbankLemma[]
  groupedWordbankLemmas: Array<{ letter: string; items: WordbankLemma[] }>
  onSelectLemma: (lemma: string) => void
  lemmaDetails: LemmaDetailsResponse | null
  lemmaDetailsError: string | null
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  isRegeneratingLemmaPronunciation: boolean
  onRegenerateSelectedLemmaPronunciation: () => void
  selectedLemmaVerificationError: VerificationErrorDetail | null
  hasSuggestedVerificationChanges: (detail: VerificationErrorDetail | null) => boolean
  isApplyingVerificationChanges: boolean
  onApplySelectedLemmaVerificationChanges: () => void
}
