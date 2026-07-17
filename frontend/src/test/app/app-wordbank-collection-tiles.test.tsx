import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"
import { vi } from "vitest"

describe("App wordbank collection tiles", () => {
  it("renders compact specimen labels and exposes metadata on keyboard focus", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 3,
            pos_tags: ["NOUN"],
            categories: ["School"],
          },
          {
            lemma: "passe på",
            english_translation: "watch out",
            variation_count: 1,
            pos_tags: ["VERB"],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const bogTile = await screen.findByRole("button", { name: "bog" })
    expect(bogTile).toHaveTextContent("bog· 3")
    expect(bogTile.querySelector("svg")).toBeInTheDocument()
    expect(bogTile).toHaveAttribute("data-material", "word")
    expect(bogTile).toHaveAttribute("data-grid-anchor", "unit")

    fireEvent.focus(bogTile)
    const tooltip = await screen.findByRole("tooltip")
    expect(within(tooltip).getByText("book")).toBeInTheDocument()
    expect(within(tooltip).getByText("Noun")).toBeInTheDocument()
    expect(within(tooltip).queryByText("Pronunciation available")).not.toBeInTheDocument()

    const mweTile = screen.getByRole("button", { name: "passe på" })
    expect(mweTile).toHaveAttribute("data-mwe", "true")
  })

  it("keeps whole-lemma deletion on the specimen context menu", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            variation_count: 1,
            pos_tags: [],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.contextMenu(await screen.findByRole("button", { name: "bog" }))
    expect(await screen.findByRole("menuitem", { name: /delete whole lemma/i })).toBeInTheDocument()
  })

  it("marks only activity from the last seven days as recent", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date("2026-07-17T12:00:00Z"))
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: ["School"],
            created_at: "2026-06-01 08:00:00",
            last_enriched_at: "2026-07-14T08:00:00+00:00",
          },
          {
            lemma: "gammel",
            variation_count: 1,
            pos_tags: ["ADJ"],
            categories: [],
            created_at: "2026-05-01 08:00:00",
            last_enriched_at: "2026-07-01 08:00:00",
          },
        ],
      },
    })

    renderApp()
    expect(await screen.findByLabelText("Recently enriched bog")).toBeInTheDocument()
    expect(screen.queryByLabelText("Recently enriched gammel")).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it("renders all five references as a distinct deck shelf", async () => {
    mockFetchImplementation({ lemmasResponse: { items: [] } })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(await screen.findByRole("heading", { name: "Reference collections" })).toBeInTheDocument()
    const labels = ["Pronouns", "HV Questions", "Prepositions", "Conjunctions", "Numbers & Time"]
    const tones = new Set<string>()
    for (const label of labels) {
      const deck = screen.getByRole("button", { name: `Open ${label} reference` })
      const material = deck.closest<HTMLElement>("[data-material='reference']")
      expect(material).toBeInTheDocument()
      tones.add(material?.dataset.materialTone ?? "")
    }
    expect(tones.size).toBe(5)

    fireEvent.click(screen.getByRole("button", { name: "Open Numbers & Time reference" }))
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Numbers & Time" })).toBeInTheDocument()
    })
  })
})
