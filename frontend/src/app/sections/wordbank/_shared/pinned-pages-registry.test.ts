import { describe, expect, it } from "vitest"

import {
  PINNED_PAGES,
  isDeprecatedPinnedSentinel,
  parsePinnedPageSentinel,
} from "@/app/sections/wordbank/_shared/pinned-pages-registry"

describe("pinned pages registry", () => {
  it("exposes the five grouped pinned pages", () => {
    expect(PINNED_PAGES.map((page) => page.title)).toEqual([
      "Pronouns",
      "HV Questions",
      "Prepositions",
      "Conjunctions",
      "Numbers & Time",
    ])
  })

  it("maps legacy sentinels to grouped pages and tabs", () => {
    expect(parsePinnedPageSentinel("__pronouns_personal")).toMatchObject({
      id: "pronouns",
      defaultTab: "personal",
    })
    expect(parsePinnedPageSentinel("__question_words")).toMatchObject({
      id: "hv_questions",
      defaultTab: "hv_people_things",
    })
    expect(parsePinnedPageSentinel("__pinned_pronouns_question_words")).toMatchObject({
      id: "hv_questions",
      defaultTab: "hv_people_things",
    })
    expect(parsePinnedPageSentinel("__prepositions")).toMatchObject({
      id: "prepositions",
      defaultTab: "prepositions",
    })
    expect(parsePinnedPageSentinel("__pinned_function_words_prepositions")).toMatchObject({
      id: "prepositions",
      defaultTab: "prepositions",
    })
    expect(parsePinnedPageSentinel("__conjunctions")).toMatchObject({
      id: "conjunctions",
      defaultTab: "conjunctions",
    })
    expect(parsePinnedPageSentinel("__pinned_function_words_conjunctions")).toMatchObject({
      id: "conjunctions",
      defaultTab: "conjunctions",
    })
    expect(parsePinnedPageSentinel("__numbers")).toMatchObject({
      id: "numbers_time",
      defaultTab: "cardinal_numbers",
    })
  })

  it("treats articles + function-words umbrella sentinels as deprecated", () => {
    expect(parsePinnedPageSentinel("__pinned_function_words")).toBeNull()
    expect(parsePinnedPageSentinel("__pinned_function_words_articles")).toBeNull()
    expect(parsePinnedPageSentinel("__articles_gender")).toBeNull()
    expect(isDeprecatedPinnedSentinel("__pinned_function_words")).toBe(true)
    expect(isDeprecatedPinnedSentinel("__pinned_function_words_articles")).toBe(true)
    expect(isDeprecatedPinnedSentinel("__articles_gender")).toBe(true)
    expect(isDeprecatedPinnedSentinel("__pinned_pronouns")).toBe(false)
  })
})
