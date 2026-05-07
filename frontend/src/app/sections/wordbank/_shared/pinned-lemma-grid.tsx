import type { SentencebankSentence } from "@/app/core"
import { PinnedLemmaCard, type PinnedLemmaEntry } from "@/app/sections/wordbank/_shared/pinned-lemma-card"

type PinnedLemmaGridProps = {
  entries: PinnedLemmaEntry[]
  sentences?: SentencebankSentence[]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  generatingExampleByLemma?: Record<string, boolean>
  onGenerateExample?: (lemma: string) => void
  onOpenSentence?: (id: number) => void
  columns?: 2 | 3
}

export function PinnedLemmaGrid({
  entries,
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingExampleByLemma,
  onGenerateExample,
  onOpenSentence,
  columns = 3,
}: PinnedLemmaGridProps) {
  const colsClass = columns === 2 ? "sm:grid-cols-2" : "sm:grid-cols-2 xl:grid-cols-3"
  return (
    <div className={`grid items-start gap-3 ${colsClass}`}>
      {entries.map((entry) => (
        <PinnedLemmaCard
          key={entry.lemma}
          entry={entry}
          sentences={sentences}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          generatingExample={Boolean(generatingExampleByLemma?.[entry.lemma])}
          onGenerateExample={onGenerateExample}
          onOpenSentence={onOpenSentence}
        />
      ))}
    </div>
  )
}
