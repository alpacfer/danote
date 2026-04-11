import { type SentencebankSentence } from "@/app/core"
import { SentencebankListView } from "@/app/sections/sentencebank/sentencebank-list-view"
import { SentencebankSentencePage } from "@/app/sections/sentencebank/sentencebank-sentence-page"

export type SentencebankSectionProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  selectedSentenceId: number | null
  onOpenSentence: (id: number) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankSection({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  onOpenSentence,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankSectionProps) {
  if (selectedSentenceId !== null) {
    const sentence = sentences.find((s) => s.id === selectedSentenceId) ?? null
    return (
      <SentencebankSentencePage
        sentence={sentence}
        onOpenWordbankLemma={onOpenWordbankLemma}
        onOpenWordbankMeaning={onOpenWordbankMeaning}
      />
    )
  }

  return (
    <SentencebankListView
      sentencebankError={sentencebankError}
      isSentencebankLoading={isSentencebankLoading}
      sentences={sentences}
      onOpenSentence={onOpenSentence}
    />
  )
}
