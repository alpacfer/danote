import { describe, expect, it } from "vitest"

import { getTokenSpansFromText, mapAnalyzedTokensToHighlights } from "./token-highlights"

describe("token highlight mapping", () => {
  it("extracts wordlike spans with unicode letters", () => {
    const spans = getTokenSpansFromText("Hej! bogen's og MilkoScna")

    expect(spans).toEqual([
      { token: "Hej", from: 0, to: 3 },
      { token: "bogen's", from: 5, to: 12 },
      { token: "og", from: 13, to: 15 },
      { token: "MilkoScna", from: 16, to: 25 },
    ])
  })

  it("maps tokens in order and only returns highlightable classifications", () => {
    const highlights = mapAnalyzedTokensToHighlights("kan bogen nyord ", [
      {
        surface_token: "kan",
        normalized_token: "kan",
        classification: "known",
      },
      {
        surface_token: "bogen",
        normalized_token: "bogen",
        classification: "variation",
      },
      {
        surface_token: "nyord",
        normalized_token: "nyord",
        classification: "new",
      },
    ])

    expect(highlights).toEqual([
      { from: 4, to: 9, classification: "variation", tokenIndex: 1 },
      { from: 10, to: 15, classification: "new", tokenIndex: 2 },
    ])
  })

  it("soft-fails mismatches and duplicate drift without throwing", () => {
    const highlights = mapAnalyzedTokensToHighlights("kat kat ", [
      {
        surface_token: "kat",
        normalized_token: "kat",
        classification: "new",
      },
      {
        surface_token: "ukendt",
        normalized_token: "ukendt",
        classification: "new",
      },
      {
        surface_token: "kat",
        normalized_token: "kat",
        classification: "typo_likely",
      },
    ])

    expect(highlights).toEqual([
      { from: 0, to: 3, classification: "new", tokenIndex: 0 },
      { from: 4, to: 7, classification: "typo_likely", tokenIndex: 2 },
    ])
  })
})
