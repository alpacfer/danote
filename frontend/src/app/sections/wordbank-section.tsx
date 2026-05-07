import { parseHvQuestionSentinel } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { WordbankHvQuestionPage } from "@/app/sections/wordbank/hv-questions/wordbank-hv-question-page"
import { parseNumbersSentinel } from "@/app/sections/wordbank/numbers/numbers-data"
import { WordbankNumbersPage } from "@/app/sections/wordbank/numbers/wordbank-numbers-page"
import { parsePronounSentinel } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { WordbankPronounPage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-page"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankListView } from "@/app/sections/wordbank/wordbank-list-view"
import { WordbankWordPage } from "@/app/sections/wordbank/wordbank-word-page"

export type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"

export function WordbankSection(props: WordbankSectionProps) {
  if (!props.selectedLemma) {
    return <WordbankListView {...props} />
  }

  const pronounCategory = parsePronounSentinel(props.selectedLemma)
  if (parseHvQuestionSentinel(props.selectedLemma)) {
    return (
      <WordbankHvQuestionPage
        sentences={props.sentences}
        generatingStaticExampleByLemma={props.generatingStaticExampleByLemma}
        onGenerateStaticExample={props.onGenerateStaticExample}
        onOpenSentence={props.onOpenSentence}
      />
    )
  }
  if (parseNumbersSentinel(props.selectedLemma)) {
    return <WordbankNumbersPage />
  }

  if (pronounCategory) {
    return (
      <WordbankPronounPage
        category={pronounCategory}
        lemmas={props.lemmas}
      />
    )
  }

  return <WordbankWordPage {...props} />
}
