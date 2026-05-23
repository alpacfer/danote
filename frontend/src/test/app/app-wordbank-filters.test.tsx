import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

describe("App wordbank filters", () => {
  it("filters lemmas by word type while keeping multi-POS lemmas visible", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "lege", variation_count: 1, pos_tags: ["VERB", "NOUN"], categories: ["School"] },
          { lemma: "bog", variation_count: 1, pos_tags: ["NOUN"], categories: ["School"] },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /^word type/i }))
    fireEvent.click(await screen.findByText("Verb"))

    expect(screen.getByRole("button", { name: /^lege/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^bog/i })).not.toBeInTheDocument()
  })

  it("requires all selected categories and combines them with selected word type", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "lære", variation_count: 1, pos_tags: ["VERB"], categories: ["School", "Work"] },
          { lemma: "klasse", variation_count: 1, pos_tags: ["NOUN"], categories: ["School", "Work"] },
          { lemma: "kontor", variation_count: 1, pos_tags: ["NOUN"], categories: ["Work"] },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /^category/i }))
    fireEvent.click(await screen.findByText("School"))
    fireEvent.click(screen.getByText("Work"))

    expect(screen.getByRole("button", { name: /^lære/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^klasse/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^kontor/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /^word type/i }))
    fireEvent.click(await screen.findByText("Verb"))

    expect(screen.getByRole("button", { name: /^lære/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^klasse/i })).not.toBeInTheDocument()
  })

  it("searches category options and clears active filters", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "mor", variation_count: 1, pos_tags: ["NOUN"], categories: ["People"] },
          { lemma: "skole", variation_count: 1, pos_tags: ["NOUN"], categories: ["School"] },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /^category/i }))
    fireEvent.change(screen.getByPlaceholderText("Search categories..."), { target: { value: "peo" } })

    expect(screen.getByText("People")).toBeVisible()
    expect(screen.queryByText("School")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("People"))
    expect(screen.getByRole("button", { name: /^mor/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^skole/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /clear filters/i }))

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^mor/i })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: /^skole/i })).toBeInTheDocument()
    })
  })

  it("navigates and filters wordbank when clicking POS and Category badges on the word page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 2, pos_tags: ["NOUN"], categories: ["School"] },
          { lemma: "lege", variation_count: 1, pos_tags: ["VERB"], categories: ["Sports"] },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            categories: ["School"],
            surface_forms: [],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    // Open Wordbank, click 'bog' to go to word details page
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    const bogItem = await screen.findByRole("button", { name: /^bog$/i })
    fireEvent.click(bogItem)

    // Verify we are on details page (heading 'bog' is visible)
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()

    // Find the badges container
    const meaningBadges = screen.getByTestId("wordbank-meaning-badges-1")
    const nounBadge = within(meaningBadges).getByText(/^Noun$/i)

    // 1. Click POS badge (Noun)
    fireEvent.click(nounBadge)

    // This should redirect to list view and apply 'NOUN' filter
    // Let's verify 'bog' is in the list, but 'lege' (VERB) is not
    expect(await screen.findByRole("button", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^lege$/i })).not.toBeInTheDocument()

    // Clear filters to reset
    fireEvent.click(screen.getByRole("button", { name: /clear filters/i }))
    await screen.findByRole("button", { name: /^lege$/i }) // lege comes back

    // Open 'bog' details page again
    fireEvent.click(screen.getByRole("button", { name: /^bog$/i }))
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()

    // 2. Click Category badge (School)
    const meaningBadges2 = screen.getByTestId("wordbank-meaning-badges-1")
    const schoolBadge2 = within(meaningBadges2).getByText(/^School$/i)
    fireEvent.click(schoolBadge2)

    // This should redirect to list view and apply 'School' category filter
    // 'bog' has category "School", 'lege' has category "Sports"
    // Let's verify 'bog' is in the list, but 'lege' is not
    expect(await screen.findByRole("button", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^lege$/i })).not.toBeInTheDocument()
  })
})

