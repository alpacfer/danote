import { COORDINATING_CONJUNCTION_ROWS, SUBORDINATING_CONJUNCTION_ROWS } from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import { DAYS_OF_WEEK, MONTHS } from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import { BASIC_NUMBER_ROWS, ORDINAL_NUMBER_ROWS, TENS_NUMBER_ROWS } from "@/app/sections/wordbank/numbers/numbers-data"
import { PREPOSITION_ROWS } from "@/app/sections/wordbank/prepositions/prepositions-data"
import {
  DEMONSTRATIVE_ROWS,
  INDEFINITE_PRONOUN_ROWS,
  PERSONAL_PRONOUN_ROWS,
  POSSESSIVE_PRONOUN_ROWS,
  RELATIVE_PRONOUN_ROWS,
} from "@/app/sections/wordbank/pronouns/pronouns-data"
import { QUESTION_WORDS, type QuestionWordCategory } from "@/app/sections/wordbank/question-words/question-words-data"
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
  hv_questions: "HV Questions",
  prepositions: "Prepositions",
  conjunctions: "Conjunctions",
  numbers_time: "Numbers & Time",
}

const TAB_LABELS: Record<PinnedPageTabId, string> = {
  personal: "Personal",
  possessive: "Possessive",
  demonstrative: "Demonstrative",
  relative: "Relative",
  indefinite: "Indefinite",
  hv_people_things: "People & Things",
  hv_choice: "Choice",
  hv_place_time_manner: "Place, Time, Manner & Reason",
  prepositions: "Prepositions",
  conjunctions: "Conjunctions",
  cardinal_numbers: "Cardinal Numbers",
  ordinal_numbers: "Ordinal Numbers",
  days: "Days",
  months: "Months",
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

const HV_TAB_BY_CATEGORY: Record<QuestionWordCategory, PinnedPageTabId> = {
  people_things: "hv_people_things",
  choice: "hv_choice",
  place_time_manner_reason: "hv_place_time_manner",
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
for (const category of Object.keys(HV_TAB_BY_CATEGORY) as QuestionWordCategory[]) {
  addHome(
    QUESTION_WORDS.filter((row) => row.category === category).map((row) => row.lemma),
    "hv_questions",
    HV_TAB_BY_CATEGORY[category],
  )
}
addHome(PREPOSITION_ROWS.map((row) => row.lemma), "prepositions", "prepositions")
addHome([...COORDINATING_CONJUNCTION_ROWS, ...SUBORDINATING_CONJUNCTION_ROWS].map((row) => row.lemma), "conjunctions", "conjunctions")
addHome([...BASIC_NUMBER_ROWS, ...TENS_NUMBER_ROWS].map((row) => row.word), "numbers_time", "cardinal_numbers")
addHome(ORDINAL_NUMBER_ROWS.map((row) => row.ordinal), "numbers_time", "ordinal_numbers")
addHome(DAYS_OF_WEEK.map((row) => row.lemma), "numbers_time", "days")
addHome(MONTHS.map((row) => row.lemma), "numbers_time", "months")

export function pinnedHomesForLemma(lemma: string | null | undefined): PinnedWordHome[] {
  const normalized = (lemma ?? "").trim().toLocaleLowerCase("da-DK")
  if (!normalized) return []
  return HOMES_BY_LEMMA.get(normalized) ?? []
}
