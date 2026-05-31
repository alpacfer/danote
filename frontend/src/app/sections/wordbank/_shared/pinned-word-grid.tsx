import { PinnedWordCard, type PinnedWordEntry } from "@/app/sections/wordbank/_shared/pinned-word-card"

type PinnedWordGridProps = {
  entries: PinnedWordEntry[]
  onOpenWord: (lemma: string) => void
  hiddenBadges?: readonly string[]
}

export function PinnedWordGrid({
  entries,
  onOpenWord,
  hiddenBadges,
}: PinnedWordGridProps) {
  const dedupedEntries = dedupePinnedEntries(entries)
  return (
    <div className="grid min-w-0 items-start gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {dedupedEntries.map((entry, index) => (
        <PinnedWordCard
          key={`${entry.lemma}-${index}`}
          entry={entry}
          onOpenWord={onOpenWord}
          hiddenBadges={hiddenBadges}
        />
      ))}
    </div>
  )
}

function dedupePinnedEntries(entries: PinnedWordEntry[]): PinnedWordEntry[] {
  const seen = new Set<string>()
  return entries.filter((entry) => {
    const key = [
      entry.lemma.trim().toLocaleLowerCase("da-DK"),
      entry.posTag ?? "",
      entry.morphology ?? "",
      entry.translation.trim().toLocaleLowerCase("da-DK"),
    ].join("\u0000")
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}
