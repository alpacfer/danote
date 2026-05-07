import type { SentencebankSentence } from "@/app/core"
import { RELATIVE_PRONOUN_ROWS } from "@/app/sections/wordbank/pronouns/pronouns-data"
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

export function WordbankPronounRelativePage({
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: Props) {
  const entries: PinnedLemmaEntry[] = RELATIVE_PRONOUN_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
    note: row.note ?? null,
    posTag: "PRON",
  }))
  return (
    <PinnedPageLayout
      title="Relative Pronouns"
      description="Words that link a relative clause to its antecedent (the noun being described)."
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
          columns={2}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
