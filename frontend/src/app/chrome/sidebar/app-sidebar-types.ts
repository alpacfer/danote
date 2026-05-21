import { type AppSection, type SearchFeedbackContext, type SearchSaveSeed, type SentencebankSentence, type WordbankLemma } from "@/app/core"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  sentences: SentencebankSentence[]
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
  unreadWordbankNotificationCount: number
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onSelectAccount: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankLemmaRaw: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onOpenSentence: (id: number) => void
  onAddSentenceToSentencebank: (sourceText: string, englishTranslation?: string | null) => Promise<void>
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
}
