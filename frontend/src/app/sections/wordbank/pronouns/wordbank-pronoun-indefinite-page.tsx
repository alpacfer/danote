import type { SentencebankSentence } from "@/app/core"
import { INDEFINITE_PRONOUN_ROWS } from "@/app/sections/wordbank/pronouns/pronouns-data"
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

export function WordbankPronounIndefinitePage({
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: Props) {
  const entries: PinnedLemmaEntry[] = INDEFINITE_PRONOUN_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
    note: row.note ?? null,
    posTag: "PRON",
  }))
  return (
    <PinnedPageLayout
      title="Indefinite Pronouns"
      description="Words referring to non-specific people, things, or quantities — someone, no one, all, both, each other."
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
