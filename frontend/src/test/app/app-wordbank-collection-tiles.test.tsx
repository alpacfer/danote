import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

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
    expect(bogTile.querySelector("svg")).not.toBeInTheDocument()

    fireEvent.focus(bogTile)
    const tooltip = await screen.findByRole("tooltip")
    expect(within(tooltip).getByText("book")).toBeInTheDocument()
    expect(within(tooltip).getByText("Noun")).toBeInTheDocument()
    expect(within(tooltip).queryByText("Pronunciation available")).not.toBeInTheDocument()

    const mweTile = screen.getByRole("button", { name: "passe på" })
    expect(mweTile.querySelector("svg")).not.toBeInTheDocument()
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

  it("renders all five references as a distinct deck shelf", async () => {
    mockFetchImplementation({ lemmasResponse: { items: [] } })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(await screen.findByRole("heading", { name: "Reference collections" })).toBeInTheDocument()
    const labels = ["Pronouns", "HV Questions", "Prepositions", "Conjunctions", "Numbers & Time"]
    for (const label of labels) {
      expect(screen.getByRole("button", { name: `Open ${label} reference` })).toBeInTheDocument()
    }

    fireEvent.click(screen.getByRole("button", { name: "Open Numbers & Time reference" }))
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Numbers & Time" })).toBeInTheDocument()
    })
  })
})
