import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, seedSavedNotes, toast, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("renders header, lesson notes card, and backend status badge", async () => {
    mockFetchImplementation()

    renderApp()

    expect(screen.getAllByText(/danote/i).length).toBeGreaterThan(0)
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

  it("hides the second line for saved-word search results without a gloss", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
          {
            lemma: "kat",
            display_lemma: "kat",
            variation_count: 1,
            english_translation: null,
            match_surface: null,
          },
        ],
      },
      corSearchFormResponse: {
        form: "kat",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "kat" } })

    expect(await within(commandDialog).findByText(/^kat$/i, { selector: "strong" })).toBeInTheDocument()

    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-translation-skeleton")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/^no translation available\.$/i)).not.toBeInTheDocument()
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/translation")),
      ).toBe(false)
    })
  })

  it("hides the second line for COR search results without a gloss", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "kattens",
        groups: [
          {
            lemma: "kat",
            gloss: null,
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.777.111.01",
                form: "kattens",
                lemma: "kat",
                gloss: null,
                lemma_translation: null,
                gram_raw: "sb.fk.sg.best.gen",
                norm: "N",
                lemma_idx: 777,
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
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "kattens" } })

    expect(await within(commandDialog).findByText(/^kattens$/i, { selector: "strong" })).toBeInTheDocument()

    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-translation-skeleton")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/^no translation available\.$/i)).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/the cat's/i)).not.toBeInTheDocument()
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/translation")),
      ).toBe(false)
    })
  })

  it("keeps showing other add alternatives when an exact saved form exists", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1, english_translation: "teacher" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "lærer",
            display_lemma: "lærer",
            variation_count: 1,
            english_translation: "teacher",
            match_surface: null,
          },
        ],
      },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.110.01",
                form: "lærer",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.30686.203.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.præs.akt",
                norm: "N",
                lemma_idx: 30686,
                gram_code: 203,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
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
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    expect((await within(commandDialog).findAllByText(/^lærer$/i)).length).toBeGreaterThan(0)
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-add-icon")).length).toBeGreaterThan(0)
  })

  it("shows eye icon for already-saved variation and still keeps alternative COR entries", async () => {
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
            match_surface: "bogen",
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
                cor_id: "COR.123.111.01",
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
            lemma: "boge",
            gloss: "arc",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.456.111.01",
                form: "bogen",
                lemma: "boge",
                gloss: "arc",
                lemma_translation: "arc",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 456,
                gram_code: 111,
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

    expect((await within(commandDialog).findAllByText(/^bogen$/i)).length).toBeGreaterThan(0)
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-add-icon")).length).toBeGreaterThan(0)
    expect(await within(commandDialog).findByText(/^boge$/i, { selector: "em" })).toBeInTheDocument()
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

  it("renders prefix matches with the same from-lemma text design", async () => {
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

    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(0)
    })
    const options = within(commandDialog).getAllByRole("option")
    const topItem = options[0]
    expect(topItem).toHaveAttribute("data-value")
    expect(topItem.getAttribute("data-value")?.startsWith("wordbank-sigtbarhed")).toBe(true)
    expect(within(topItem).queryByTestId("search-open-icon")).toBeInTheDocument()
  })

  it("keeps exact-lemma open result above linked variation result for same query", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "lærer", variation_count: 1, english_translation: "teacher" },
          { lemma: "lære", variation_count: 3, english_translation: "learn" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "lære",
            display_lemma: "at lære",
            variation_count: 3,
            english_translation: "learn",
            match_surface: null,
            pos_tag: "VERB",
            morphology: "VerbForm=Inf",
          },
          {
            lemma: "lærer",
            display_lemma: "lærer",
            variation_count: 1,
            english_translation: "teacher",
            match_surface: null,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.30686.203.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.præs.akt",
                norm: "N",
                lemma_idx: 30686,
                gram_code: 203,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.110.01",
                form: "lærer",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 49032,
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
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(1)
    })
    const options = within(commandDialog).getAllByRole("option")
    const topItem = options[0]
    expect(topItem).toHaveTextContent(/^lærer/i)
    expect(within(topItem).queryByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(topItem).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
  })

  it("command search puts existing-lemma variation options before other COR options", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lære", variation_count: 3, english_translation: "learn" }],
      },
      searchWordbankResponse: {
        items: [],
      },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.110.01",
                form: "lærer",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.30686.203.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.præs.akt",
                norm: "N",
                lemma_idx: 30686,
                gram_code: 203,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
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
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    expect(await within(commandDialog).findByTestId("search-add-variation-label")).toBeInTheDocument()

    const verbLemma = await within(commandDialog).findByText(/^at lære$/i, { selector: "em" })
    const nounLemma = await within(commandDialog).findByText(/^lærer$/i, { selector: "em" })
    const verbItem = verbLemma.closest("[cmdk-item]")
    const nounItem = nounLemma.closest("[cmdk-item]")

    expect(verbItem).toBeTruthy()
    expect(nounItem).toBeTruthy()
    expect(verbItem && nounItem
      ? (verbItem.compareDocumentPosition(nounItem) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
      : false).toBe(true)
  })

  it("keeps saved lemma visible across ulykk -> ulykker query changes and shows non-legacy badges", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "ulykke", variation_count: 2, english_translation: "accident" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "ulykke",
            display_lemma: "ulykke",
            variation_count: 2,
            english_translation: "accident",
            match_surface: "ulykker",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Plur|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "ulykker",
        groups: [
          {
            lemma: "ulykke",
            gloss: "accident",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.700.112.01",
                form: "ulykker",
                lemma: "ulykke",
                gloss: "accidents",
                lemma_translation: "accident",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 700,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
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

    fireEvent.change(searchInput, { target: { value: "ulykk" } })
    expect(await within(commandDialog).findByText(/^ulykke$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Noun$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^n-word$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Indefinite$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^NOUN$/)).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    })

    fireEvent.change(searchInput, { target: { value: "ulykke" } })
    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(0)
    })

    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    })
  })

  it("keeps added ulykker visible and selected across exact query transitions", async () => {
    const lemmaItems: Array<{
      lemma: string
      variation_count: number
      english_translation?: string | null
    }> = []
    const searchItems: Array<{
      lemma: string
      display_lemma: string
      variation_count: number
      english_translation?: string | null
      match_surface?: string | null
      pos_tag?: string | null
      morphology?: string | null
    }> = []
    let addedCount = 0

    mockFetchImplementation({
      lemmasResponse: { items: lemmaItems },
      searchWordbankResponse: { items: searchItems },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = (url.searchParams.get("form") ?? "").trim().toLocaleLowerCase("da-DK")
        if (form !== "ulykker") {
          return responseOf({ form, groups: [] })
        }
        return responseOf({
          form: "ulykker",
          groups: [
            {
              lemma: "ulykke",
              gloss: "accident",
              pos_tag: "NOUN",
              variants: [
                {
                  cor_id: "COR.700.112.01",
                  form: "ulykker",
                  lemma: "ulykke",
                  gloss: "accidents",
                  lemma_translation: "accident",
                  gram_raw: "sb.fk.pl.ubest",
                  norm: "N",
                  lemma_idx: 700,
                  gram_code: 112,
                  variation: 1,
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                  extra_tags: [],
                },
              ],
            },
          ],
        })
      },
      addWordHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          surface_token?: string
          lemma_candidate?: string | null
        }
        if (body.surface_token === "ulykker" && body.lemma_candidate === "ulykke") {
          addedCount += 1
          if (lemmaItems.length === 0) {
            lemmaItems.push({
              lemma: "ulykke",
              variation_count: 2,
              english_translation: "accident",
            })
          }
          if (searchItems.length === 0) {
            searchItems.push({
              lemma: "ulykke",
              display_lemma: "ulykke",
              variation_count: 2,
              english_translation: "accident",
              match_surface: "ulykker",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Plur|Definite=Ind",
            })
          }
          return responseOf({
            status: "inserted",
            stored_lemma: "ulykke",
            stored_surface_form: "ulykker",
            source: "manual",
            message: "Added 'ulykke' to wordbank.",
          })
        }

        return responseOf({
          status: "exists",
          stored_lemma: body.lemma_candidate ?? "ulykke",
          stored_surface_form: body.surface_token ?? null,
          source: "manual",
          message: "Word already exists.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    let commandDialog = await screen.findByRole("dialog")
    let searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)

    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    const addOption = (await within(commandDialog).findByText(/^ulykker$/i)).closest("[cmdk-item]")
    expect(addOption).toBeTruthy()
    fireEvent.click(addOption as HTMLElement)

    await waitFor(() => {
      expect(addedCount).toBe(1)
    })
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    commandDialog = await screen.findByRole("dialog")
    searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)

    fireEvent.change(searchInput, { target: { value: "ulykk" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
    })
    expect(await within(commandDialog).findByText(/^Noun$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^n-word$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Indefinite$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^NOUN$/)).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "ulykke" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
    })

    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
    })

    fireEvent.change(searchInput, { target: { value: "ulykke" } })
    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(0)
    })
    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    })

    fireEvent.keyDown(window, { key: "k", ctrlKey: true })
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    commandDialog = await screen.findByRole("dialog")
    searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    })
  })

  it("resets selection to first result on each new search update", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "silde", variation_count: 1, english_translation: "herring" },
          { lemma: "sild", variation_count: 1, english_translation: "herring" },
          { lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "silde",
            display_lemma: "silde",
            variation_count: 1,
            english_translation: "herring",
            match_surface: null,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
          {
            lemma: "sild",
            display_lemma: "sild",
            variation_count: 1,
            english_translation: "herring",
            match_surface: null,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: null,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "si",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "si" } })

    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(2)
    })

    fireEvent.keyDown(searchInput, { key: "ArrowDown" })
    fireEvent.keyDown(searchInput, { key: "ArrowDown" })

    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("data-selected", "false")
    })

    fireEvent.change(searchInput, { target: { value: "sid" } })

    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("data-selected", "true")
    })
  })

  it("command search uses local COR endpoint, renders grouped variants, and adds selected variant", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.110.01",
                form: "lærer",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
              {
                cor_id: "COR.49032.112.01",
                form: "lærere",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.30686.203.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.præs.akt",
                norm: "N",
                lemma_idx: 30686,
                gram_code: 203,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordResponse: {
        status: "inserted",
        stored_lemma: "lære",
        stored_surface_form: "lærer",
        source: "manual",
        message: "Added 'lære' to wordbank.",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    expect((await within(commandDialog).findAllByText(/teacher/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/learn/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Noun$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Verb$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^n-word$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Singular$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Present$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Indefinite$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Active$/i)).length).toBeGreaterThan(0)
    const verbLemma = await within(commandDialog).findByText(/^at lære$/i, { selector: "em" })
    expect(verbLemma).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/\(to learn\)/i)).toBeInTheDocument()
    expect(screen.queryByText(/lære \(verb\)/i)).not.toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-add-icon")).length).toBeGreaterThan(0)
    expect(screen.queryByText(/english -> danish/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/danish -> english/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/add variation/i)).not.toBeInTheDocument()

    const verbVariant = verbLemma.closest("[cmdk-item]")
    expect(verbVariant).toBeTruthy()
    expect(verbVariant).toHaveTextContent(/from\s+at lære/i)
    fireEvent.click(verbVariant as HTMLElement)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes")) {
            return false
          }
          const body = JSON.parse(String(init?.body ?? "{}")) as {
            surface_token?: string
            lemma_candidate?: string
            pos_tag?: string
            morphology?: string
          }
          return (
            body.surface_token === "lærer"
            && body.lemma_candidate === "lære"
            && body.pos_tag === "VERB"
            && body.morphology === "Tense=Pres|VerbForm=Fin|Voice=Act"
          )
        }),
      ).toBe(true)
    })

    expect(
      fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/resolve-query")),
    ).toBe(false)
  })

  it("command search debounces local COR requests and caches repeated queries", async () => {
    let corRequestCount = 0
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormHandler: async (input) => {
        corRequestCount += 1
        const url = new URL(String(input), "http://localhost")
        const form = (url.searchParams.get("form") ?? "").toLocaleLowerCase("da-DK")
        return responseOf({
          form,
          groups: [
            {
              lemma: form || "house",
              gloss: null,
              pos_tag: "NOUN",
              variants: [
                {
                  cor_id: `COR.${corRequestCount}.110.01`,
                  form: form || "house",
                  lemma: form || "house",
                  gram_raw: "sb.fk.sg.ubest",
                  norm: "N",
                  lemma_idx: corRequestCount,
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
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)

    fireEvent.change(searchInput, { target: { value: "h" } })
    fireEvent.change(searchInput, { target: { value: "ho" } })
    fireEvent.change(searchInput, { target: { value: "house" } })

    await waitFor(() => {
      expect(corRequestCount).toBe(1)
    })

    fireEvent.change(searchInput, { target: { value: "home" } })
    await waitFor(() => {
      expect(corRequestCount).toBe(2)
    })

    fireEvent.change(searchInput, { target: { value: "house" } })
    await waitFor(() => {
      expect(corRequestCount).toBe(2)
    })
  })

  it("shows a backend connectivity message when adding from search hits a network failure", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.49032.210.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.prs.akt",
                norm: "V",
                lemma_idx: 49032,
                gram_code: 210,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordHandler: async () => {
        throw new TypeError("Failed to fetch")
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    fireEvent.click(await within(commandDialog).findByText(/^lærer$/i))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "Could not add word to wordbank. Could not reach the backend at http://127.0.0.1:8000. Check that it is running and try again.",
      )
    })
  })

  it("shows backend error details when adding from search returns an API error", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.49032.210.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.prs.akt",
                norm: "V",
                lemma_idx: 49032,
                gram_code: 210,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordHandler: async () => ({
        ok: false,
        status: 409,
        json: async () => ({ detail: "The word 'lærer' is already saved as a variation." }),
      } as Response),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    fireEvent.click(await within(commandDialog).findByText(/^lærer$/i))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith("The word 'lærer' is already saved as a variation.")
    })
  })

})
