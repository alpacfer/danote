// Central registry of pinned built-in reference pages in the wordbank.
// Legacy sentinels are kept so existing search and sentence-token flows can
// still land on the right grouped page and tab.

export type PinnedPageId =
  | "pronouns"
  | "function_words"
  | "numbers_time"

export type PinnedPageTabId =
  | "personal"
  | "possessive"
  | "demonstrative"
  | "relative"
  | "indefinite"
  | "question_words"
  | "articles"
  | "prepositions"
  | "conjunctions"
  | "cardinal_numbers"
  | "ordinal_numbers"
  | "days"
  | "months"
  | "seasons"
  | "time_words"

export type PinnedPageMeta = {
  id: PinnedPageId
  sentinel: string
  title: string
  defaultTab: PinnedPageTabId
}

export const PINNED_PAGES: PinnedPageMeta[] = [
  { id: "pronouns", sentinel: "__pinned_pronouns", title: "Pronouns", defaultTab: "personal" },
  { id: "function_words", sentinel: "__pinned_function_words", title: "Function Words", defaultTab: "articles" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
]

const LEGACY_PINNED_PAGES: PinnedPageMeta[] = [
  { id: "pronouns", sentinel: "__pinned_pronouns_personal", title: "Pronouns", defaultTab: "personal" },
  { id: "pronouns", sentinel: "__pinned_pronouns_possessive", title: "Pronouns", defaultTab: "possessive" },
  { id: "pronouns", sentinel: "__pinned_pronouns_demonstrative", title: "Pronouns", defaultTab: "demonstrative" },
  { id: "pronouns", sentinel: "__pinned_pronouns_relative", title: "Pronouns", defaultTab: "relative" },
  { id: "pronouns", sentinel: "__pinned_pronouns_indefinite", title: "Pronouns", defaultTab: "indefinite" },
  { id: "pronouns", sentinel: "__pinned_pronouns_question_words", title: "Pronouns", defaultTab: "question_words" },
  { id: "function_words", sentinel: "__pinned_function_words_articles", title: "Function Words", defaultTab: "articles" },
  { id: "function_words", sentinel: "__pinned_function_words_prepositions", title: "Function Words", defaultTab: "prepositions" },
  { id: "function_words", sentinel: "__pinned_function_words_conjunctions", title: "Function Words", defaultTab: "conjunctions" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_cardinal_numbers", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_ordinal_numbers", title: "Numbers & Time", defaultTab: "ordinal_numbers" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_days", title: "Numbers & Time", defaultTab: "days" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_months", title: "Numbers & Time", defaultTab: "months" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_seasons", title: "Numbers & Time", defaultTab: "seasons" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_time_words", title: "Numbers & Time", defaultTab: "time_words" },
  { id: "pronouns", sentinel: "__pronouns_personal", title: "Pronouns", defaultTab: "personal" },
  { id: "pronouns", sentinel: "__pronouns_possessive", title: "Pronouns", defaultTab: "possessive" },
  { id: "pronouns", sentinel: "__pronouns_demonstrative", title: "Pronouns", defaultTab: "demonstrative" },
  { id: "pronouns", sentinel: "__pronouns_relative", title: "Pronouns", defaultTab: "relative" },
  { id: "pronouns", sentinel: "__pronouns_indefinite", title: "Pronouns", defaultTab: "indefinite" },
  { id: "pronouns", sentinel: "__question_words", title: "Pronouns", defaultTab: "question_words" },
  { id: "function_words", sentinel: "__articles_gender", title: "Function Words", defaultTab: "articles" },
  { id: "function_words", sentinel: "__prepositions", title: "Function Words", defaultTab: "prepositions" },
  { id: "function_words", sentinel: "__conjunctions", title: "Function Words", defaultTab: "conjunctions" },
  { id: "numbers_time", sentinel: "__numbers", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
  { id: "numbers_time", sentinel: "__days_months_seasons", title: "Numbers & Time", defaultTab: "days" },
  { id: "numbers_time", sentinel: "__time_expressions", title: "Numbers & Time", defaultTab: "time_words" },
]

export const PINNED_PAGE_BY_SENTINEL: Record<string, PinnedPageMeta> = Object.fromEntries(
  [...PINNED_PAGES, ...LEGACY_PINNED_PAGES].map((page) => [page.sentinel, page]),
)

export const PINNED_PAGE_BY_ID: Record<PinnedPageId, PinnedPageMeta> = Object.fromEntries(
  PINNED_PAGES.map((page) => [page.id, page]),
) as Record<PinnedPageId, PinnedPageMeta>

export const PINNED_PAGE_BY_TAB: Record<PinnedPageId, Partial<Record<PinnedPageTabId, PinnedPageMeta>>> = {
  pronouns: Object.fromEntries(
    LEGACY_PINNED_PAGES.filter((page) => page.id === "pronouns" && page.sentinel.startsWith("__pinned_")).map((page) => [page.defaultTab, page]),
  ),
  function_words: Object.fromEntries(
    LEGACY_PINNED_PAGES.filter((page) => page.id === "function_words" && page.sentinel.startsWith("__pinned_")).map((page) => [page.defaultTab, page]),
  ),
  numbers_time: Object.fromEntries(
    LEGACY_PINNED_PAGES.filter((page) => page.id === "numbers_time" && page.sentinel.startsWith("__pinned_")).map((page) => [page.defaultTab, page]),
  ),
} as Record<PinnedPageId, Partial<Record<PinnedPageTabId, PinnedPageMeta>>>

export function parsePinnedPageSentinel(lemma: string | null | undefined): PinnedPageMeta | null {
  if (!lemma) return null
  return PINNED_PAGE_BY_SENTINEL[lemma] ?? null
}

export function isPinnedPageSentinel(lemma: string | null | undefined): boolean {
  return parsePinnedPageSentinel(lemma) !== null
}

export function sentinelForPinnedPageTab(pageId: PinnedPageId, tabId: PinnedPageTabId): string {
  return PINNED_PAGE_BY_TAB[pageId]?.[tabId]?.sentinel ?? PINNED_PAGE_BY_ID[pageId].sentinel
}
