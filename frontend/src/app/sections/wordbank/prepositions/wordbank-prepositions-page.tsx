import type { SentencebankSentence } from "@/app/core"
import { PREPOSITION_ROWS } from "@/app/sections/wordbank/prepositions/prepositions-data"
import {
  PinnedLemmaGrid,
  PinnedPageLayout,
  PinnedPageSection,
  type PinnedLemmaEntry,
} from "@/app/sections/wordbank/_shared"

type Props = {
  sentences: SentencebankSentence[]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  generatingStaticExampleByLemma: Record<string, boolean>
  onGenerateStaticExample: (lemma: string) => void
  onOpenSentence?: (id: number) => void
}

export function WordbankPrepositionsPage({
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: Props) {
  const entries: PinnedLemmaEntry[] = PREPOSITION_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    note: row.note ?? null,
    posTag: "ADP",
  }))
  return (
    <PinnedPageLayout
      title="Prepositions"
      description="High-frequency Danish prepositions with English glosses and short usage notes."
    >
      <PinnedPageSection>
        <PinnedLemmaGrid
          entries={entries}
          sentences={sentences}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          generatingExampleByLemma={generatingStaticExampleByLemma}
          onGenerateExample={onGenerateStaticExample}
          onOpenSentence={onOpenSentence}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
