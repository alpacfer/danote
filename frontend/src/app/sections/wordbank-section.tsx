import { parsePinnedPageSentinel } from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import { WordbankArticlesGenderPage } from "@/app/sections/wordbank/articles-gender/wordbank-articles-gender-page"
import { WordbankConjunctionsPage } from "@/app/sections/wordbank/conjunctions/wordbank-conjunctions-page"
import { WordbankDaysMonthsSeasonsPage } from "@/app/sections/wordbank/days-months-seasons/wordbank-days-months-seasons-page"
import { WordbankNumbersPage } from "@/app/sections/wordbank/numbers/wordbank-numbers-page"
import { WordbankPrepositionsPage } from "@/app/sections/wordbank/prepositions/wordbank-prepositions-page"
import { WordbankPronounDemonstrativePage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-demonstrative-page"
import { WordbankPronounIndefinitePage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-indefinite-page"
import { WordbankPronounPersonalPage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-personal-page"
import { WordbankPronounPossessivePage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-possessive-page"
import { WordbankPronounRelativePage } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-relative-page"
import { WordbankQuestionWordsPage } from "@/app/sections/wordbank/question-words/wordbank-question-words-page"
import { WordbankTimeExpressionsPage } from "@/app/sections/wordbank/time-expressions/wordbank-time-expressions-page"
import { WordbankListView } from "@/app/sections/wordbank/wordbank-list-view"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankWordPage } from "@/app/sections/wordbank/wordbank-word-page"

export type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"

export function WordbankSection(props: WordbankSectionProps) {
  if (!props.selectedLemma) {
    return <WordbankListView {...props} />
  }

  const pinned = parsePinnedPageSentinel(props.selectedLemma)
  if (pinned) {
    const tableProps = {
      pronunciationLoadingByForm: props.pronunciationLoadingByForm,
      onPlayPronunciation: props.onPlayPronunciation,
    }
    const gridProps = {
      ...tableProps,
      sentences: props.sentences,
      generatingStaticExampleByLemma: props.generatingStaticExampleByLemma,
      onGenerateStaticExample: props.onGenerateStaticExample,
      onOpenSentence: props.onOpenSentence,
    }
    switch (pinned.id) {
      case "pronouns_personal":
        return <WordbankPronounPersonalPage {...tableProps} />
      case "pronouns_possessive":
        return <WordbankPronounPossessivePage {...tableProps} />
      case "pronouns_demonstrative":
        return <WordbankPronounDemonstrativePage {...tableProps} />
      case "pronouns_relative":
        return <WordbankPronounRelativePage {...gridProps} />
      case "pronouns_indefinite":
        return <WordbankPronounIndefinitePage {...gridProps} />
      case "question_words":
        return <WordbankQuestionWordsPage {...gridProps} />
      case "articles_gender":
        return <WordbankArticlesGenderPage {...tableProps} />
      case "prepositions":
        return <WordbankPrepositionsPage {...gridProps} />
      case "conjunctions":
        return <WordbankConjunctionsPage {...gridProps} />
      case "numbers":
        return <WordbankNumbersPage />
      case "days_months_seasons":
        return <WordbankDaysMonthsSeasonsPage {...tableProps} />
      case "time_expressions":
        return <WordbankTimeExpressionsPage {...tableProps} />
    }
  }

  return <WordbankWordPage {...props} />
}
