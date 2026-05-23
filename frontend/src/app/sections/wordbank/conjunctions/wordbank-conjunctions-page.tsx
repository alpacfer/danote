import {
  COORDINATING_CONJUNCTION_ROWS,
  SUBORDINATING_CONJUNCTION_ROWS,
} from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import {
  PinnedPageLayout,
  PinnedWordGrid,
  type PinnedWordEntry,
  hiddenBadgesForPinnedTab,
} from "@/app/sections/wordbank/_shared"

type Props = {
  onOpenWord: (lemma: string) => void
}

export function WordbankConjunctionsPage({ onOpenWord }: Props) {
  return (
    <PinnedPageLayout title="Conjunctions">
      <PinnedWordGrid
        entries={conjunctionEntries()}
        onOpenWord={onOpenWord}
        hiddenBadges={hiddenBadgesForPinnedTab("conjunctions", "conjunctions")}
      />
    </PinnedPageLayout>
  )
}

function conjunctionEntries(): PinnedWordEntry[] {
  return [...COORDINATING_CONJUNCTION_ROWS, ...SUBORDINATING_CONJUNCTION_ROWS].map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    posTag: ["og", "eller", "men", "for", "så"].includes(row.lemma) ? "CCONJ" : "SCONJ",
  }))
}
