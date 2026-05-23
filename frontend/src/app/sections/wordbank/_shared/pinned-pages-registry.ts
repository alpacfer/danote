// Central registry of pinned built-in reference pages in the wordbank.
// Legacy sentinels are kept so existing search and sentence-token flows can
// still land on the right grouped page and tab.

export type PinnedPageId =
  | "pronouns"
  | "prepositions"
  | "conjunctions"
  | "numbers_time"
  | "hv_questions"

export type PinnedPageTabId =
  | "personal"
  | "possessive"
  | "demonstrative"
  | "relative"
  | "indefinite"
  | "hv_people_things"
  | "hv_choice"
  | "hv_place_time_manner"
  | "prepositions"
  | "conjunctions"
  | "cardinal_numbers"
  | "ordinal_numbers"
  | "days"
  | "months"

export type PinnedPageMeta = {
  id: PinnedPageId
  sentinel: string
  title: string
  defaultTab: PinnedPageTabId
}

export const PINNED_PAGES: PinnedPageMeta[] = [
  { id: "pronouns", sentinel: "__pinned_pronouns", title: "Pronouns", defaultTab: "personal" },
  { id: "hv_questions", sentinel: "__pinned_hv_questions", title: "HV Questions", defaultTab: "hv_people_things" },
  { id: "prepositions", sentinel: "__pinned_prepositions", title: "Prepositions", defaultTab: "prepositions" },
  { id: "conjunctions", sentinel: "__pinned_conjunctions", title: "Conjunctions", defaultTab: "conjunctions" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
]

const LEGACY_PINNED_PAGES: PinnedPageMeta[] = [
  { id: "pronouns", sentinel: "__pinned_pronouns_personal", title: "Pronouns", defaultTab: "personal" },
  { id: "pronouns", sentinel: "__pinned_pronouns_possessive", title: "Pronouns", defaultTab: "possessive" },
  { id: "pronouns", sentinel: "__pinned_pronouns_demonstrative", title: "Pronouns", defaultTab: "demonstrative" },
  { id: "pronouns", sentinel: "__pinned_pronouns_relative", title: "Pronouns", defaultTab: "relative" },
  { id: "pronouns", sentinel: "__pinned_pronouns_indefinite", title: "Pronouns", defaultTab: "indefinite" },
  { id: "hv_questions", sentinel: "__pinned_hv_questions_people_things", title: "HV Questions", defaultTab: "hv_people_things" },
  { id: "hv_questions", sentinel: "__pinned_hv_questions_choice", title: "HV Questions", defaultTab: "hv_choice" },
  { id: "hv_questions", sentinel: "__pinned_hv_questions_place_time_manner", title: "HV Questions", defaultTab: "hv_place_time_manner" },
  // Legacy mapping: prepositions/conjunctions used to live under Function Words; they now have their own pages.
  { id: "prepositions", sentinel: "__pinned_function_words_prepositions", title: "Prepositions", defaultTab: "prepositions" },
  { id: "conjunctions", sentinel: "__pinned_function_words_conjunctions", title: "Conjunctions", defaultTab: "conjunctions" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_cardinal_numbers", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_ordinal_numbers", title: "Numbers & Time", defaultTab: "ordinal_numbers" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_days", title: "Numbers & Time", defaultTab: "days" },
  { id: "numbers_time", sentinel: "__pinned_numbers_time_months", title: "Numbers & Time", defaultTab: "months" },
  { id: "pronouns", sentinel: "__pronouns_personal", title: "Pronouns", defaultTab: "personal" },
  { id: "pronouns", sentinel: "__pronouns_possessive", title: "Pronouns", defaultTab: "possessive" },
  { id: "pronouns", sentinel: "__pronouns_demonstrative", title: "Pronouns", defaultTab: "demonstrative" },
  { id: "pronouns", sentinel: "__pronouns_relative", title: "Pronouns", defaultTab: "relative" },
  { id: "pronouns", sentinel: "__pronouns_indefinite", title: "Pronouns", defaultTab: "indefinite" },
  { id: "hv_questions", sentinel: "__pinned_pronouns_question_words", title: "HV Questions", defaultTab: "hv_people_things" },
  { id: "hv_questions", sentinel: "__question_words", title: "HV Questions", defaultTab: "hv_people_things" },
  { id: "prepositions", sentinel: "__prepositions", title: "Prepositions", defaultTab: "prepositions" },
  { id: "conjunctions", sentinel: "__conjunctions", title: "Conjunctions", defaultTab: "conjunctions" },
  { id: "numbers_time", sentinel: "__numbers", title: "Numbers & Time", defaultTab: "cardinal_numbers" },
  { id: "numbers_time", sentinel: "__days_months_seasons", title: "Numbers & Time", defaultTab: "days" },
]

// Sentinels that previously rendered a pinned page but no longer have one
// (Function Words umbrella + the Articles tab). Treat them as a request to
// return to the wordbank list view so stale URLs/back-nav land somewhere safe.
const DEPRECATED_PINNED_SENTINELS: ReadonlySet<string> = new Set([
  "__pinned_function_words",
  "__pinned_function_words_articles",
  "__articles_gender",
  "__pinned_numbers_time_seasons",
  "__pinned_numbers_time_time_words",
  "__time_expressions",
])

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
  hv_questions: Object.fromEntries(
    LEGACY_PINNED_PAGES.filter((page) => page.id === "hv_questions" && page.sentinel.startsWith("__pinned_hv_questions_")).map((page) => [page.defaultTab, page]),
  ),
  prepositions: {},
  conjunctions: {},
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

export function isDeprecatedPinnedSentinel(lemma: string | null | undefined): boolean {
  if (!lemma) return false
  return DEPRECATED_PINNED_SENTINELS.has(lemma)
}

export function sentinelForPinnedPageTab(pageId: PinnedPageId, tabId: PinnedPageTabId): string {
  return PINNED_PAGE_BY_TAB[pageId]?.[tabId]?.sentinel ?? PINNED_PAGE_BY_ID[pageId].sentinel
}
