import { ARTICLE_ROWS } from "@/app/sections/wordbank/articles-gender/articles-gender-data"
import { COORDINATING_CONJUNCTION_ROWS, SUBORDINATING_CONJUNCTION_ROWS } from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import { DAYS_OF_WEEK, MONTHS, SEASONS } from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import { BASIC_NUMBER_ROWS, ORDINAL_NUMBER_ROWS, TENS_NUMBER_ROWS } from "@/app/sections/wordbank/numbers/numbers-data"
import { PREPOSITION_ROWS } from "@/app/sections/wordbank/prepositions/prepositions-data"
import {
  DEMONSTRATIVE_ROWS,
  INDEFINITE_PRONOUN_ROWS,
  PERSONAL_PRONOUN_ROWS,
  POSSESSIVE_PRONOUN_ROWS,
  RELATIVE_PRONOUN_ROWS,
} from "@/app/sections/wordbank/pronouns/pronouns-data"
import { QUESTION_WORDS } from "@/app/sections/wordbank/question-words/question-words-data"
import { DURATION_ROWS, FREQUENCY_ROWS, RELATIVE_DAY_ROWS } from "@/app/sections/wordbank/time-expressions/time-expressions-data"
import { sentinelForPinnedPageTab, type PinnedPageId, type PinnedPageTabId } from "@/app/sections/wordbank/_shared/pinned-pages-registry"

export type PinnedWordHome = {
  pageId: PinnedPageId
  pageTitle: string
  tabId: PinnedPageTabId
  tabTitle: string
  sentinel: string
}

const HOME_LABELS: Record<PinnedPageId, string> = {
  pronouns: "Pronouns",
  function_words: "Function Words",
  numbers_time: "Numbers & Time",
}

const TAB_LABELS: Record<PinnedPageTabId, string> = {
  personal: "Personal",
  possessive: "Possessive",
  demonstrative: "Demonstrative",
  relative: "Relative",
  indefinite: "Indefinite",
  question_words: "Question Words",
  articles: "Articles",
  prepositions: "Prepositions",
  conjunctions: "Conjunctions",
  cardinal_numbers: "Cardinal Numbers",
  ordinal_numbers: "Ordinal Numbers",
  days: "Days",
  months: "Months",
  seasons: "Seasons",
  time_words: "Time Words",
}

const HOMES_BY_LEMMA = new Map<string, PinnedWordHome[]>()

function addHome(lemmas: string[], pageId: PinnedPageId, tabId: PinnedPageTabId) {
  const home: PinnedWordHome = {
    pageId,
    pageTitle: HOME_LABELS[pageId],
    tabId,
    tabTitle: TAB_LABELS[tabId],
    sentinel: sentinelForPinnedPageTab(pageId, tabId),
  }
  for (const lemma of lemmas) {
    const key = lemma.trim().toLocaleLowerCase("da-DK")
    if (!key) continue
    const existing = HOMES_BY_LEMMA.get(key) ?? []
    if (!existing.some((item) => item.sentinel === home.sentinel)) {
      existing.push(home)
    }
    HOMES_BY_LEMMA.set(key, existing)
  }
}

addHome(
  PERSONAL_PRONOUN_ROWS.flatMap((row) => [row.nominative, row.accusative].filter(Boolean) as string[]),
  "pronouns",
  "personal",
)
addHome(
  POSSESSIVE_PRONOUN_ROWS.flatMap((row) => [row.common, row.neuter, row.plural]),
  "pronouns",
  "possessive",
)
addHome(
  DEMONSTRATIVE_ROWS.flatMap((row) => [row.common, row.neuter, row.plural]),
  "pronouns",
  "demonstrative",
)
addHome(RELATIVE_PRONOUN_ROWS.map((row) => row.lemma), "pronouns", "relative")
addHome(INDEFINITE_PRONOUN_ROWS.map((row) => row.lemma), "pronouns", "indefinite")
addHome(QUESTION_WORDS.map((row) => row.lemma), "pronouns", "question_words")
addHome(ARTICLE_ROWS.map((row) => row.lemma), "function_words", "articles")
addHome(PREPOSITION_ROWS.map((row) => row.lemma), "function_words", "prepositions")
addHome([...COORDINATING_CONJUNCTION_ROWS, ...SUBORDINATING_CONJUNCTION_ROWS].map((row) => row.lemma), "function_words", "conjunctions")
addHome([...BASIC_NUMBER_ROWS, ...TENS_NUMBER_ROWS].map((row) => row.word), "numbers_time", "cardinal_numbers")
addHome(ORDINAL_NUMBER_ROWS.map((row) => row.ordinal), "numbers_time", "ordinal_numbers")
addHome(DAYS_OF_WEEK.map((row) => row.lemma), "numbers_time", "days")
addHome(MONTHS.map((row) => row.lemma), "numbers_time", "months")
addHome(SEASONS.map((row) => row.lemma), "numbers_time", "seasons")
addHome(
  [...RELATIVE_DAY_ROWS, ...DURATION_ROWS, ...FREQUENCY_ROWS]
    .filter((row) => !row.lemma.includes(" ") && !row.lemma.includes("…"))
    .map((row) => row.lemma),
  "numbers_time",
  "time_words",
)

export function pinnedHomesForLemma(lemma: string | null | undefined): PinnedWordHome[] {
  const normalized = (lemma ?? "").trim().toLocaleLowerCase("da-DK")
  if (!normalized) return []
  return HOMES_BY_LEMMA.get(normalized) ?? []
}
