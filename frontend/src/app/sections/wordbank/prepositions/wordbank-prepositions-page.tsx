import { PREPOSITION_ROWS } from "@/app/sections/wordbank/prepositions/prepositions-data"
import {
  PinnedPageLayout,
  PinnedWordGrid,
  type PinnedWordEntry,
  hiddenBadgesForPinnedTab,
} from "@/app/sections/wordbank/_shared"

type Props = {
  onOpenWord: (lemma: string) => void
}

export function WordbankPrepositionsPage({ onOpenWord }: Props) {
  return (
    <PinnedPageLayout title="Prepositions">
      <PinnedWordGrid
        entries={prepositionEntries()}
        onOpenWord={onOpenWord}
        hiddenBadges={hiddenBadgesForPinnedTab("prepositions", "prepositions")}
      />
    </PinnedPageLayout>
  )
}

function prepositionEntries(): PinnedWordEntry[] {
  return PREPOSITION_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    posTag: "ADP",
  }))
}
