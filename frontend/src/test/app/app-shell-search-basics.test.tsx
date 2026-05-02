import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"
import { bogVariationGlossWordPageContractFixture, cloneContractFixture } from "@/test/app/wordbank-contract-fixtures"

describe("App shell and search", () => {
  it("renders wordbank as the default section with backend status", async () => {
    mockFetchImplementation()

    renderApp()

    expect(screen.queryByText(/^danote$/i)).not.toBeInTheDocument()
    const statusBadge = await screen.findByLabelText("backend-connection-status")
    expect(statusBadge).toHaveTextContent(/connected/i)
    expect(screen.getAllByText(/^Wordbank$/).length).toBeGreaterThan(0)
  })

  it("renders sidebar navigation without Playground", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(screen.queryByRole("button", { name: /playground/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^notes$/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /wordbank/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sentencebank/i })).toBeInTheDocument()
  })

  it("command dialog search opens and supports wordbank results", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 1, english_translation: "book" },
          { lemma: "hus", variation_count: 1, english_translation: "house" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            variation_count: 2,
            english_translation: "book",
            match_surface: "bogens",
            query_cor_ids: ["COR.100.111.01"],
          },
        ],
      },
      corSearchFormResponse: {
        form: "bogens",
        groups: [
          {
            lemma: "bog",
            gloss: "book",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.100.111.01",
                form: "bogens",
                lemma: "bog",
                gloss: "book's",
                lemma_translation: "book",
                gram_raw: "sb.fk.sg.best.gen",
                norm: "N",
                lemma_idx: 100,
                gram_code: 111,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def|Case=Gen",
                features: { Gender: "Com", Number: "Sing", Definite: "Def", Case: "Gen" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "bogens" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()

    fireEvent.click((await within(commandDialog).findAllByText(/^bogens$/i, { selector: "strong" }))[0] as HTMLElement)
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()

    expect(screen.queryByRole("textbox", { name: /lesson notes/i })).not.toBeInTheDocument()
  }, 10_000)

  it("command search shows saved lemma as top action with eye icon", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            variation_count: 2,
            english_translation: "book",
            match_surface: null,
          },
        ],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "bog" } })

    expect(await within(commandDialog).findByText(/^bog$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()

    fireEvent.click(await within(commandDialog).findByText(/^bog$/i, { selector: "strong" }))
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
  })

  it("command search preserves typed spaces so sentence queries can be entered", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i) as HTMLInputElement

    fireEvent.change(searchInput, { target: { value: "jeg " } })

    expect(searchInput.value).toBe("jeg ")
  })

  it("command search does not use legacy local lemma fallback when API search returns no matches", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      searchWordbankResponse: {
        items: [],
      },
      corSearchFormResponse: {
        form: "bog",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "bog" } })

    await waitFor(() => {
      expect(within(commandDialog).queryByText(/^bog$/i, { selector: "strong" })).not.toBeInTheDocument()
      expect(within(commandDialog).queryByTestId("search-open-icon")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
    })
  })

  it("renders English queries as Danish COR results using the translated word", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      resolveQueryResponse: {
        query_surface: "notebook",
        query_lemma: "notebook",
        classification: "new",
        matched_lemma: null,
        matched_lemma_summary: null,
        query_pos_tag: "NOUN",
        query_morphology: null,
        resolved_surface: "notesbog",
        resolved_lemma: "notesbog",
        da_to_en_translation: null,
        en_to_da_translation: "notesbog",
        en_to_da_lemma: "notesbog",
        en_to_da_pos_tag: "NOUN",
        en_to_da_morphology: null,
        query_language: "en",
        query_language_confidence: 0.95,
        en_pos_groups: [
          {
            lemma: "notebook",
            pos_ud: "NOUN",
            pos_raw: "noun",
            danish_translation: "notesbog",
            senses: [
              {
                pos_ud: "NOUN",
                sense_idx: 0,
                gloss: "book for writing notes",
                danish_translation: "notesbog",
                examples: [],
              },
            ],
          },
        ],
        word_actions: [
          {
            action_type: "add_as_new",
            surface: "notesbog",
            lemma: "notesbog",
            translation_label: "notesbog",
            direction: "en_to_da",
            direction_label: "English -> Danish",
            pos_tag: "NOUN",
            morphology: null,
            show_lemma: false,
          },
        ],
      },
      corSearchFormHandler: async (input) => {
        const form = new URL(String(input), "http://localhost").searchParams.get("form") ?? ""
        if (form === "notesbog") {
          return responseOf({
            form,
            groups: [
              {
                lemma: "notesbog",
                gloss: "notebook",
                pos_tag: "NOUN",
                variants: [
                  {
                    cor_id: "COR.NOTEBOOK.1",
                    form: "notesbog",
                    lemma: "notesbog",
                    gloss: "notebook",
                    lemma_translation: "notebook",
                    saveable_translation: "notebook",
                    gram_raw: "sb.fk.sg.ubest",
                    norm: "N",
                    lemma_idx: 1200,
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
          })
        }
        return responseOf({ form, groups: [] })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "notebook" } })

    expect(await within(commandDialog).findByText(/^translated from english$/i)).toBeInTheDocument()
    await waitFor(() => {
      const translatedRow = within(commandDialog).getByText(/^notesbog$/i, { selector: "strong" })
      expect(translatedRow).toBeInTheDocument()
      expect(translatedRow.closest("[cmdk-item]")).toHaveTextContent(/from\s+notesbog\s+\(notebook\)/i)
    })

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/search/cor-form?form=notesbog")),
      ).toBe(true)
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/search/cor-form?form=notebook")),
      ).toBe(true)
    })
  })

  it("command search skips wordbank API calls for one-character queries", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sol",
            display_lemma: "sol",
            variation_count: 1,
            english_translation: "sun",
            match_surface: null,
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "s" } })

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.filter(([input]) => String(input).includes("/api/wordbank/search?")),
      ).toHaveLength(0)
    })

    fireEvent.change(searchInput, { target: { value: "so" } })

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.filter(([input]) => String(input).includes("/api/wordbank/search?")),
      ).toHaveLength(1)
    })
  })

  it("shows Did you mean suggestion when search returns did_you_mean", async () => {
    mockFetchImplementation({
      wordbankSearchHandler: async (_input) => {
        const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
        const parsed = new URL(url, "http://localhost")
        const query = parsed.searchParams.get("query") ?? ""
        if (query === "huse") {
          return responseOf({
            items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
            did_you_mean: "hus",
          })
        }
        return responseOf({ items: [] })
      },
    })

    renderApp()

    const searchButton = await screen.findByRole("button", { name: /search/i })
    fireEvent.click(searchButton)

    const commandDialog = await screen.findByRole("dialog")
    const input = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(input, { target: { value: "huse" } })

    await waitFor(() => {
      expect(screen.getByText(/did you mean/i)).toBeInTheDocument()
      expect(screen.getByText(/"hus"/i)).toBeInTheDocument()
    })
  })

  it("selecting Did you mean replaces the search query", async () => {
    mockFetchImplementation({
      wordbankSearchHandler: async (_input) => {
        const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
        const parsed = new URL(url, "http://localhost")
        const query = parsed.searchParams.get("query") ?? ""
        if (query === "huse") {
          return responseOf({
            items: [],
            did_you_mean: "hus",
          })
        }
        if (query === "hus") {
          return responseOf({
            items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
            did_you_mean: null,
          })
        }
        return responseOf({ items: [] })
      },
    })

    renderApp()

    const searchButton = await screen.findByRole("button", { name: /search/i })
    fireEvent.click(searchButton)

    const commandDialog = await screen.findByRole("dialog")
    const input = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(input, { target: { value: "huse" } })

    const suggestion = await screen.findByText(/did you mean/i)
    fireEvent.click(suggestion)

    await waitFor(() => {
      expect(input).toHaveValue("hus")
    })
  })

  it("suppresses did-you-mean when COR has a direct match, even if wordbank has a correction", async () => {
    mockFetchImplementation({
      wordbankSearchHandler: async (_input) => {
        const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
        const parsed = new URL(url, "http://localhost")
        const query = parsed.searchParams.get("query") ?? ""
        if (query === "huse") {
          return responseOf({
            items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
            did_you_mean: "hus",
          })
        }
        return responseOf({ items: [] })
      },
      corSearchFormResponse: {
        form: "huse",
        did_you_mean: null,
        groups: [
          {
            lemma: "hus",
            gloss: "house",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.HUS.1",
                form: "huse",
                lemma: "hus",
                gloss: "houses",
                lemma_translation: "house",
                gram_raw: "sb.itk.pl.ubest",
                norm: "N",
                lemma_idx: 1,
                gram_code: 1,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Number=Plur|Definite=Ind",
                features: { Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    const searchButton = await screen.findByRole("button", { name: /search/i })
    fireEvent.click(searchButton)
    const commandDialog = await screen.findByRole("dialog")
    const input = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(input, { target: { value: "huse" } })

    const corResult = await within(commandDialog).findByText(/^huse$/i)

    expect(corResult).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/did you mean/i)).not.toBeInTheDocument()
  })
})
