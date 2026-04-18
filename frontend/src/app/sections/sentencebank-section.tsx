import { type SentencebankSentence } from "@/app/core"
import { type PendingSentence } from "@/app/hooks/app/use-section-navigation"
import { SentencebankListView } from "@/app/sections/sentencebank/sentencebank-list-view"
import { SentencebankSentencePage } from "@/app/sections/sentencebank/sentencebank-sentence-page"

export type SentencebankSectionProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  selectedSentenceId: number | null
  pendingSentence: PendingSentence | null
  pronunciationLoadingBySentenceId: Record<number, boolean>
  regeneratingPronunciationBySentenceId: Record<number, boolean>
  onOpenSentence: (id: number) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onPlayPronunciation: (sentenceId: number) => void
  onPlayPronunciationSlowly: (sentenceId: number) => void
  onRegeneratePronunciation: (sentenceId: number) => void
}

export function SentencebankSection({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  pendingSentence,
  pronunciationLoadingBySentenceId,
  regeneratingPronunciationBySentenceId,
  onOpenSentence,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onPlayPronunciation,
  onPlayPronunciationSlowly,
  onRegeneratePronunciation,
}: SentencebankSectionProps) {
  if (pendingSentence !== null && selectedSentenceId === null) {
    const sentenceShell: SentencebankSentence = {
      id: -1,
      source_text: pendingSentence.source_text,
      english_translation: pendingSentence.english_translation,
      created_at: new Date().toISOString(),
    }
    return (
      <SentencebankSentencePage
        sentence={sentenceShell}
        isLoadingTokens
        pronunciationLoadingBySentenceId={pronunciationLoadingBySentenceId}
        regeneratingPronunciationBySentenceId={regeneratingPronunciationBySentenceId}
        onOpenWordbankLemma={onOpenWordbankLemma}
        onOpenWordbankMeaning={onOpenWordbankMeaning}
        onPlayPronunciation={onPlayPronunciation}
        onPlayPronunciationSlowly={onPlayPronunciationSlowly}
        onRegeneratePronunciation={onRegeneratePronunciation}
      />
    )
  }

  if (selectedSentenceId !== null) {
    const sentence = sentences.find((s) => s.id === selectedSentenceId) ?? null
    return (
      <SentencebankSentencePage
        sentence={sentence}
        pronunciationLoadingBySentenceId={pronunciationLoadingBySentenceId}
        regeneratingPronunciationBySentenceId={regeneratingPronunciationBySentenceId}
        onOpenWordbankLemma={onOpenWordbankLemma}
        onOpenWordbankMeaning={onOpenWordbankMeaning}
        onPlayPronunciation={onPlayPronunciation}
        onPlayPronunciationSlowly={onPlayPronunciationSlowly}
        onRegeneratePronunciation={onRegeneratePronunciation}
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
