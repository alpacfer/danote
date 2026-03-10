import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App playground", () => {
  it("clicking a highlighted noun opens noun popover with word, lemma subtitle, and translation", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      lemmasResponse: {
        items: [],
      },
      translationResponse: {
        status: "generated",
        source_word: "katten",
        lemma: "kat",
        english_translation: "cat",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    const addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^katten$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^\(kat\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^\(katten\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^NOUN$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^n-word$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^cat$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^Morphology: /i)).not.toBeInTheDocument()
  })

  it("re-opening the same highlighted token reuses popover enrich cache", async () => {
    vi.useRealTimers()
    let enrichCalls = 0

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      enrichTokenHandler: async () => {
        enrichCalls += 1
        return responseOf({
          query_surface: "katten",
          query_lemma: "kat",
          classification: "variation",
          matched_lemma: "kat",
          matched_lemma_summary: { lemma: "kat", english_translation: "cat", variation_count: 1 },
          query_pos_tag: "NOUN",
          query_morphology: "Gender=Com|Number=Sing|Definite=Def",
          resolved_surface: "katten",
          resolved_lemma: "kat",
          da_to_en_translation: "cat",
          en_to_da_translation: null,
          en_to_da_lemma: null,
          en_to_da_pos_tag: null,
          en_to_da_morphology: null,
          query_language: "da",
          query_language_confidence: 0.99,
          word_actions: [
            {
              action_type: "add_variation",
              surface: "katten",
              lemma: "kat",
              translation_label: "katten",
              direction: "variation",
              direction_label: "Variation",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Def",
              show_lemma: false,
            },
          ],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })
    await screen.findByRole("button", { name: /add variation/i })
    expect(enrichCalls).toBe(1)

    setNotesEditorText("katten  ")
    await waitFor(() => {
      const nextMark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(nextMark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const nextMark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(nextMark as HTMLElement, { clientX: 160, clientY: 140 })
    await screen.findByRole("button", { name: /add variation/i })
    expect(enrichCalls).toBe(1)
  })

  it("clicking a known word opens popover with wordbank action instead of add", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "bogen",
          normalized_token: "bogen",
          lemma_candidate: "bog",
          classification: "known",
          match_source: "exact",
          matched_lemma: "bog",
          matched_surface_form: "bogen",
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        surface_forms: [{ form: "bogen" }],
      },
      translationResponse: {
        status: "generated",
        source_word: "bogen",
        lemma: "bog",
        english_translation: "book",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("bogen ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='known']")
      expect(mark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const mark = getNotesEditor().querySelector("mark[data-status='known']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    const openButton = await screen.findByRole("button", { name: /open in wordbank/i })
    const popoverContent = openButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^bogen$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^\(bog\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^\(bogen\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^NOUN$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^n-word$/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /add to wordbank/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /add variation/i })).not.toBeInTheDocument()

    fireEvent.click(openButton)
    expect(await screen.findByText(/^bog$/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/^book$/i)).length).toBeGreaterThanOrEqual(1)
  })

  it("noun popover hides duplicate lemma and shows translation skeleton when unavailable", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "hus",
          normalized_token: "hus",
          lemma_candidate: "hus",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Neut|Number=Sing|Definite=Ind",
        },
      ],
      translationResponse: {
        status: "unavailable",
        source_word: "hus",
        lemma: "hus",
        english_translation: null,
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("hus ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 180, clientY: 160 })

    const addButton = await screen.findByRole("button", { name: /add to wordbank/i })
    const popoverContent = addButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^hus$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^\(hus\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^t-word$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByTestId("noun-translation-skeleton")).toBeInTheDocument()
  })
})
