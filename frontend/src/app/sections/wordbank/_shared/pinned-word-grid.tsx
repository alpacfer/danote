import { PinnedWordCard, type PinnedWordEntry } from "@/app/sections/wordbank/_shared/pinned-word-card"

type PinnedWordGridProps = {
  entries: PinnedWordEntry[]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onOpenWord: (lemma: string) => void
  hiddenBadges?: readonly string[]
}

export function PinnedWordGrid({
  entries,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  onOpenWord,
  hiddenBadges,
}: PinnedWordGridProps) {
  return (
    <div className="grid items-start gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {entries.map((entry, index) => (
        <PinnedWordCard
          key={`${entry.lemma}-${index}`}
          entry={entry}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          onOpenWord={onOpenWord}
          hiddenBadges={hiddenBadges}
        />
      ))}
    </div>
  )
}
