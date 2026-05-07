// Central registry of pinned built-in reference pages in the wordbank.
// Each pinned page has a sentinel lemma value; the wordbank dispatcher uses
// these to render the page instead of a normal lemma details view.

export type PinnedPageId =
  | "pronouns_personal"
  | "pronouns_possessive"
  | "pronouns_demonstrative"
  | "pronouns_relative"
  | "pronouns_indefinite"
  | "question_words"
  | "articles_gender"
  | "prepositions"
  | "conjunctions"
  | "numbers"
  | "days_months_seasons"
  | "time_expressions"

export type PinnedPageGroup = "pronouns" | "function_words" | "numbers_and_time"

export const PINNED_PAGE_GROUP_LABELS: Record<PinnedPageGroup, string> = {
  pronouns: "Pronouns",
  function_words: "Function words",
  numbers_and_time: "Numbers & time",
}

export type PinnedPageMeta = {
  id: PinnedPageId
  sentinel: string
  title: string
  group: PinnedPageGroup
}

export const PINNED_PAGES: PinnedPageMeta[] = [
  { id: "pronouns_personal", sentinel: "__pronouns_personal", title: "Personal Pronouns", group: "pronouns" },
  { id: "pronouns_possessive", sentinel: "__pronouns_possessive", title: "Possessive Pronouns", group: "pronouns" },
  { id: "pronouns_demonstrative", sentinel: "__pronouns_demonstrative", title: "Demonstrative Pronouns", group: "pronouns" },
  { id: "pronouns_relative", sentinel: "__pronouns_relative", title: "Relative Pronouns", group: "pronouns" },
  { id: "pronouns_indefinite", sentinel: "__pronouns_indefinite", title: "Indefinite Pronouns", group: "pronouns" },
  { id: "question_words", sentinel: "__question_words", title: "Question Words", group: "pronouns" },
  { id: "articles_gender", sentinel: "__articles_gender", title: "Articles & Gender", group: "function_words" },
  { id: "prepositions", sentinel: "__prepositions", title: "Prepositions", group: "function_words" },
  { id: "conjunctions", sentinel: "__conjunctions", title: "Conjunctions", group: "function_words" },
  { id: "numbers", sentinel: "__numbers", title: "Numbers", group: "numbers_and_time" },
  { id: "days_months_seasons", sentinel: "__days_months_seasons", title: "Days, Months & Seasons", group: "numbers_and_time" },
  { id: "time_expressions", sentinel: "__time_expressions", title: "Time Expressions", group: "numbers_and_time" },
]

export const PINNED_PAGE_BY_SENTINEL: Record<string, PinnedPageMeta> = Object.fromEntries(
  PINNED_PAGES.map((page) => [page.sentinel, page]),
)

export const PINNED_PAGES_BY_GROUP: Record<PinnedPageGroup, PinnedPageMeta[]> = {
  pronouns: PINNED_PAGES.filter((p) => p.group === "pronouns"),
  function_words: PINNED_PAGES.filter((p) => p.group === "function_words"),
  numbers_and_time: PINNED_PAGES.filter((p) => p.group === "numbers_and_time"),
}

export function parsePinnedPageSentinel(lemma: string | null | undefined): PinnedPageMeta | null {
  if (!lemma) return null
  return PINNED_PAGE_BY_SENTINEL[lemma] ?? null
}

export function isPinnedPageSentinel(lemma: string | null | undefined): boolean {
  return parsePinnedPageSentinel(lemma) !== null
}
