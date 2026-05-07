import type { SentencebankSentence } from "@/app/core"
import {
  PinnedLemmaGrid,
  PinnedPageLayout,
  PinnedPageSection,
} from "@/app/sections/wordbank/_shared"
import {
  QUESTION_WORD_CATEGORY_LABELS,
  QUESTION_WORDS,
  type QuestionWordCategory,
  type QuestionWordEntry,
} from "@/app/sections/wordbank/question-words/question-words-data"

type WordbankQuestionWordsPageProps = {
  sentences: SentencebankSentence[]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  generatingStaticExampleByLemma: Record<string, boolean>
  onGenerateStaticExample: (lemma: string) => void
  onOpenSentence?: (id: number) => void
}

export function WordbankQuestionWordsPage({
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: WordbankQuestionWordsPageProps) {
  const grouped = groupQuestionWords()
  return (
    <PinnedPageLayout
      title="Question Words"
      description="Danish question words (interrogative pronouns and adverbs) used to ask who, what, which, where, when, how, and why."
    >
      {grouped.map(([category, entries]) => (
        <PinnedPageSection key={category} title={QUESTION_WORD_CATEGORY_LABELS[category]}>
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
      ))}
    </PinnedPageLayout>
  )
}

function groupQuestionWords(): Array<[QuestionWordCategory, QuestionWordEntry[]]> {
  return (Object.keys(QUESTION_WORD_CATEGORY_LABELS) as QuestionWordCategory[]).map((category) => [
    category,
    QUESTION_WORDS.filter((entry) => entry.category === category),
  ])
}
