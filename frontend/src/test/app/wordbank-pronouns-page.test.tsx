import { render, screen } from "@testing-library/react"

import { WordbankPronounsPage } from "@/app/sections/wordbank/pronouns/wordbank-pronouns-page"

describe("WordbankPronounsPage", () => {
  it("exposes the full tab list through a focusable horizontal scroll region", () => {
    render(<WordbankPronounsPage defaultTab="personal" onOpenWord={vi.fn()} onOpenTab={vi.fn()} />)

    const tabScroller = screen.getByRole("region", { name: /pronoun categories/i })
    expect(tabScroller).toHaveAttribute("tabindex", "0")
    expect(screen.getAllByRole("tab")).toHaveLength(5)
  })

  it("renders identical personal pronoun forms only once per tab", () => {
    render(<WordbankPronounsPage defaultTab="personal" onOpenWord={vi.fn()} onOpenTab={vi.fn()} />)

    expect(screen.getAllByRole("button", { name: /^open den in wordbank$/i })).toHaveLength(1)
    expect(screen.getAllByRole("button", { name: /^open det in wordbank$/i })).toHaveLength(1)
  })
})
