import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, seedSavedNotes, waitFor, within } from "@/test/app-test-helpers"
import { bogVariationGlossWordPageContractFixture, cloneContractFixture } from "@/test/app/wordbank-contract-fixtures"

describe("App shell and search", () => {
  it("renders header, lesson notes card, and backend status badge", async () => {
    mockFetchImplementation()

    renderApp()

    expect(screen.queryByText(/^danote$/i)).not.toBeInTheDocument()
    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
    expect(getNotesEditor()).toBeInTheDocument()
    const statusBadge = await screen.findByLabelText("backend-connection-status")
    expect(statusBadge).toHaveTextContent(/connected/i)
  })

  it("renders sidebar navigation with playground, notes, wordbank, and sentencebank", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(screen.getByRole("button", { name: /playground/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^notes$/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /wordbank/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sentencebank/i })).toBeInTheDocument()
  })

  it("command dialog search opens and supports wordbank + notes results", async () => {
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
    seedSavedNotes([
        {
          id: "note-1",
          name: "Bogen note",
          text: "Jeg laeser en bog i dag",
          tokens: [],
          discoveredTokenMetadata: {},
          generatedTranslationMap: {},
          savedAt: "2026-02-28T12:00:00.000Z",
        },
      ],
    )

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bogens" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()

    fireEvent.click((await within(commandDialog).findAllByText(/^bogens$/i))[0] as HTMLElement)
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const reopenedDialog = await screen.findByRole("dialog")
    const reopenedSearchInput = within(reopenedDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(reopenedSearchInput, { target: { value: "bogen" } })
    const savedNoteResult = await within(reopenedDialog).findByText(/bogen note/i)
    fireEvent.click(savedNoteResult)

    expect(await screen.findByRole("button", { name: /create new note/i })).toBeInTheDocument()
    expect(getNotesEditor()).toHaveTextContent(/jeg laeser en bog i dag/i)
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
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bog" } })

    expect(await within(commandDialog).findByText(/^bog$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()

    fireEvent.click(await within(commandDialog).findByText(/^bog$/i, { selector: "strong" }))
    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
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
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bog" } })

    await waitFor(() => {
      expect(within(commandDialog).queryByText(/^bog$/i)).not.toBeInTheDocument()
      expect(within(commandDialog).queryByTestId("search-open-icon")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
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
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
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
      wordbankSearchHandler: async (_input, _init) => {
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
    const input = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(input, { target: { value: "huse" } })

    await waitFor(() => {
      expect(screen.getByText(/did you mean/i)).toBeInTheDocument()
      expect(screen.getByText(/"hus"/i)).toBeInTheDocument()
    })
  })

  it("selecting Did you mean replaces the search query", async () => {
    mockFetchImplementation({
      wordbankSearchHandler: async (_input, _init) => {
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
    const input = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(input, { target: { value: "huse" } })

    const suggestion = await screen.findByText(/did you mean/i)
    fireEvent.click(suggestion)

    await waitFor(() => {
      expect(input).toHaveValue("hus")
    })
  })
})
