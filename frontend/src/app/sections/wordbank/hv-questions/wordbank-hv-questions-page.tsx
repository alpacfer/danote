import {
  QUESTION_WORDS,
  type QuestionWordCategory,
} from "@/app/sections/wordbank/question-words/question-words-data"
import {
  PinnedPageLayout,
  PinnedWordGrid,
  type PinnedPageTabId,
  type PinnedWordEntry,
} from "@/app/sections/wordbank/_shared"

type Props = {
  defaultTab: PinnedPageTabId
  onOpenWord: (lemma: string) => void
  onOpenTab: (sentinel: string) => void
}

const TAB_BY_CATEGORY: Record<QuestionWordCategory, PinnedPageTabId> = {
  people_things: "hv_people_things",
  choice: "hv_choice",
  place_time_manner_reason: "hv_place_time_manner",
}

export function WordbankHvQuestionsPage({ onOpenWord }: Props) {
  const entries: PinnedWordEntry[] = QUESTION_WORDS.map((entry) => ({
    lemma: entry.lemma,
    translation: entry.translation,
    posTag: entry.posTag,
    morphology: entry.morphology,
  }))

  return (
    <PinnedPageLayout title="HV Questions">
      <div className="flex flex-col gap-4">
        <PinnedWordGrid
          entries={entries}
          onOpenWord={onOpenWord}
          hiddenBadges={["Interrogative"]}
        />
      </div>
    </PinnedPageLayout>
  )
}

export { TAB_BY_CATEGORY }
