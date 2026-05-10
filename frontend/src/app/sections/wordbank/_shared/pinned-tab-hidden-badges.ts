import type { PinnedPageId, PinnedPageTabId } from "@/app/sections/wordbank/_shared/pinned-pages-registry"

const HIDDEN_BADGES_BY_TAB: Record<PinnedPageId, Partial<Record<PinnedPageTabId, readonly string[]>>> = {
  pronouns: {
    personal: ["Pronoun", "Personal"],
    possessive: ["Pronoun", "Possessive"],
    demonstrative: ["Pronoun", "Demonstrative"],
    relative: ["Pronoun", "Relative"],
    indefinite: ["Pronoun", "Indefinite"],
    question_words: ["Interrogative"],
  },
  function_words: {
    articles: ["Determiner"],
    prepositions: ["Preposition"],
    conjunctions: ["Conjunction"],
  },
  numbers_time: {
    cardinal_numbers: ["Numeral"],
    ordinal_numbers: ["Adjective", "Numeral"],
    days: ["Noun"],
    months: ["Noun"],
    seasons: ["Noun"],
    time_words: ["Adverb", "Preposition"],
  },
}

export function hiddenBadgesForPinnedTab(
  pageId: PinnedPageId,
  tabId: PinnedPageTabId,
): readonly string[] {
  return HIDDEN_BADGES_BY_TAB[pageId]?.[tabId] ?? []
}
