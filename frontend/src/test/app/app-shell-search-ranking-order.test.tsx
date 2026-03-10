import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("keeps exact-form COR add actions for unsaved homograph meanings", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: null }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            meaning_id: 1,
            meaning_key: "book",
            gloss: "book",
            cor_lemma_idx: 123,
            variation_count: 2,
            english_translation: "book",
            match_surface: "bogen",
            query_cor_ids: ["COR.BOG.BOOK.1"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Def",
          },
        ],
      },
      corSearchFormResponse: {
        form: "bogen",
        groups: [
          {
            lemma: "bog",
            gloss: "book",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.BOG.BOOK.1",
                form: "bogen",
                lemma: "bog",
                gloss: "book",
                lemma_translation: "book",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 123,
                gram_code: 111,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                features: { Gender: "Com", Number: "Sing", Definite: "Def" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "bog",
            gloss: "swamp",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.BOG.SWAMP.1",
                form: "bogen",
                lemma: "bog",
                gloss: "swamp",
                lemma_translation: "swamp",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 124,
                gram_code: 211,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                features: { Gender: "Com", Number: "Sing", Definite: "Def" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bogen" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(await within(commandDialog).findAllByTestId("search-add-icon")).toHaveLength(1)
  })

  it("opens the selected saved meaning section from search", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: null }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            meaning_id: 1,
            meaning_key: "book",
            gloss: "book",
            cor_lemma_idx: 123,
            variation_count: 2,
            english_translation: "book",
            match_surface: "bog",
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
          },
          {
            lemma: "bog",
            display_lemma: "bog",
            meaning_id: 2,
            meaning_key: "swamp",
            gloss: "swamp",
            cor_lemma_idx: 124,
            variation_count: 2,
            english_translation: "swamp",
            match_surface: "bog",
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: null,
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            surface_forms: [{ form: "bogen", has_pronunciation: false }],
          },
          {
            id: 2,
            meaning_key: "swamp",
            gloss: "swamp",
            english_translation: "swamp",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            surface_forms: [{ form: "moser", has_pronunciation: false }],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bog" } })

    const swampOption = (await within(commandDialog).findAllByRole("option")).find((option) =>
      option.textContent?.toLocaleLowerCase("da-DK").includes("swamp"),
    )
    expect(swampOption).toBeTruthy()
    fireEvent.click(swampOption as HTMLElement)

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    const selectedSection = document.getElementById("wordbank-meaning-2")
    expect(selectedSection).toHaveAttribute("data-selected", "true")
    expect(selectedSection).toHaveTextContent(/swamp/i)
  })

  it("shows standard saved-lemma row with consistent from-lemma text and badges", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            query_cor_ids: ["COR.999.110.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbarhed",
        groups: [
          {
            lemma: "sigtbarhed",
            gloss: "visibility",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.999.110.01",
                form: "sigtbarhed",
                lemma: "sigtbarhed",
                gloss: "visibility",
                lemma_translation: "visibility",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 999,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(await within(commandDialog).findByRole("option", { name: /sigtbarhed/i })).toBeInTheDocument()
    expect(within(commandDialog).getByText(/\bfrom\b/i)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^sigtbarhed$/i, { selector: "em" })).toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-metadata-badge")).length).toBeGreaterThan(0)
  })

  it("hides saved prefix matches until the query is exact", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            query_cor_ids: ["COR.302.110.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbar",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "sigtbar" } })
    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-open-icon")).not.toBeInTheDocument()
    })
    expect(within(commandDialog).queryByText(/^sigtbarhed$/i, { selector: "strong" })).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })
    expect(await within(commandDialog).findByText(/^sigtbarhed$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).getByText(/\bfrom\b/i)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^sigtbarhed$/i, { selector: "em" })).toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-metadata-badge")).length).toBeGreaterThan(0)
  })

  it("prioritizes already-saved exact match above add-variation candidates", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" },
          { lemma: "sigtbar", variation_count: 1, english_translation: "visible" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbar",
            display_lemma: "sigtbar",
            variation_count: 1,
            english_translation: "visible",
            match_surface: null,
            pos_tag: "ADJ",
            morphology: "Degree=Pos",
          },
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbarhed",
        groups: [
          {
            lemma: "sigtbar",
            gloss: "visible",
            pos_tag: "ADJ",
            variants: [
              {
                cor_id: "COR.301.110.01",
                form: "sigtbarhed",
                lemma: "sigtbar",
                gloss: "visible",
                lemma_translation: "visible",
                gram_raw: "adj.sg.ubest.fk",
                norm: "N",
                lemma_idx: 301,
                gram_code: 110,
                variation: 1,
                pos_tag: "ADJ",
                morphology: "Degree=Pos",
                features: { Degree: "Pos" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "sigtbarhed",
            gloss: "visibility",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.302.110.01",
                form: "sigtbarhed",
                lemma: "sigtbarhed",
                gloss: "visibility",
                lemma_translation: "visibility",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 302,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })

    let topItem: HTMLElement | null = null
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      topItem = options[0] ?? null
      expect(topItem).not.toBeNull()
      expect(topItem?.getAttribute("data-value")?.startsWith("wordbank-sigtbarhed")).toBe(true)
    })
    expect(topItem).toHaveAttribute("data-value")
    expect(within(topItem).queryByTestId("search-open-icon")).toBeInTheDocument()
  })
})
