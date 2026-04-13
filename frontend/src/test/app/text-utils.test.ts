import { formatSentenceTranslation } from "@/app/core"

describe("Sentence text utils", () => {
  it("preserves the original capitalization in sentence translations", () => {
    expect(formatSentenceTranslation("i am happy")).toBe("i am happy")
  })

  it("removes a trailing period from sentence translations", () => {
    expect(formatSentenceTranslation("i am happy.")).toBe("i am happy")
  })
})
