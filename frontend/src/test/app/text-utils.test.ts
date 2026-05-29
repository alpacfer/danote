import { formatSentenceTranslation, isAtVerbCandidate, hasMultipleWords } from "@/app/core"

describe("Sentence text utils", () => {
  it("preserves the original capitalization in sentence translations", () => {
    expect(formatSentenceTranslation("i am happy")).toBe("i am happy")
  })

  it("removes a trailing period from sentence translations", () => {
    expect(formatSentenceTranslation("i am happy.")).toBe("i am happy")
  })
})

describe("At Verb utilities", () => {
  it("correctly identifies 'at <verb>' candidate queries", () => {
    expect(isAtVerbCandidate("at lave")).toBe(true)
    expect(isAtVerbCandidate("at spise")).toBe(true)
    expect(isAtVerbCandidate("AT spise")).toBe(true)
    expect(isAtVerbCandidate("at  spise")).toBe(true)
    expect(isAtVerbCandidate("spise")).toBe(false)
    expect(isAtVerbCandidate("at spise mad")).toBe(false)
    expect(isAtVerbCandidate("at")).toBe(false)
  })

  it("does not classify 'at <verb>' as multiple words", () => {
    expect(hasMultipleWords("at spise")).toBe(false)
    expect(hasMultipleWords("at lave")).toBe(false)
    expect(hasMultipleWords("at spise æbler")).toBe(true)
    expect(hasMultipleWords("spise æbler")).toBe(true)
    expect(hasMultipleWords("spise")).toBe(false)
  })
})
