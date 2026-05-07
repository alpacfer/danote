import type { SentencebankSentence } from "@/app/core"
import {
  CONJUNCTION_NOTES,
  COORDINATING_CONJUNCTION_ROWS,
  SUBORDINATING_CONJUNCTION_ROWS,
} from "@/app/sections/wordbank/conjunctions/conjunctions-data"
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

export function WordbankConjunctionsPage({
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: Props) {
  const coordinating: PinnedLemmaEntry[] = COORDINATING_CONJUNCTION_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    note: row.note ?? null,
    posTag: "CCONJ",
  }))
  const subordinating: PinnedLemmaEntry[] = SUBORDINATING_CONJUNCTION_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    note: row.note ?? null,
    posTag: "SCONJ",
  }))
  return (
    <PinnedPageLayout
      title="Conjunctions"
      description="Words that link clauses. Coordinating conjunctions keep main-clause word order; subordinating ones shift it."
    >
      <PinnedPageSection title="Coordinating">
        <PinnedLemmaGrid
          entries={coordinating}
          sentences={sentences}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          generatingExampleByLemma={generatingStaticExampleByLemma}
          onGenerateExample={onGenerateStaticExample}
          onOpenSentence={onOpenSentence}
        />
      </PinnedPageSection>
      <PinnedPageSection title="Subordinating">
        <PinnedLemmaGrid
          entries={subordinating}
          sentences={sentences}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          generatingExampleByLemma={generatingStaticExampleByLemma}
          onGenerateExample={onGenerateStaticExample}
          onOpenSentence={onOpenSentence}
        />
      </PinnedPageSection>
      <PinnedPageSection title="Word-order notes">
        <ul className="space-y-2 text-sm">
          {CONJUNCTION_NOTES.map((note) => (
            <li key={note} className="text-muted-foreground leading-relaxed">
              {note}
            </li>
          ))}
        </ul>
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
