import { describe, expect, it } from "vitest"

import { PINNED_PAGES, parsePinnedPageSentinel } from "@/app/sections/wordbank/_shared/pinned-pages-registry"

describe("pinned pages registry", () => {
  it("exposes only the three grouped pinned pages", () => {
    expect(PINNED_PAGES.map((page) => page.title)).toEqual([
      "Pronouns",
      "Function Words",
      "Numbers & Time",
    ])
  })

  it("maps legacy sentinels to grouped pages and tabs", () => {
    expect(parsePinnedPageSentinel("__pronouns_personal")).toMatchObject({
      id: "pronouns",
      defaultTab: "personal",
    })
    expect(parsePinnedPageSentinel("__question_words")).toMatchObject({
      id: "pronouns",
      defaultTab: "question_words",
    })
    expect(parsePinnedPageSentinel("__numbers")).toMatchObject({
      id: "numbers_time",
      defaultTab: "cardinal_numbers",
    })
  })
})
