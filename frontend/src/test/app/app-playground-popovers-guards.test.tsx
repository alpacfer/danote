import { act, fireEvent, getNotesEditor, mockFetchImplementation, renderApp, screen, setNotesEditorText, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App playground", () => {
  it("clicking a typo_likely highlight does not open popover or request translation", async () => {
    vi.useRealTimers()
    const fetchSpy = mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spisr",
          normalized_token: "spisr",
          lemma_candidate: "spiser",
          classification: "typo_likely",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationHandler: async () => {
        throw new Error("translation endpoint should not be called for typo_likely")
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("spisr ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='typo_likely']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='typo_likely']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.queryByText(/^translations$/i)).not.toBeInTheDocument()
    const translationCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/wordbank/translation"),
    )
    expect(translationCalls).toHaveLength(0)
  })

  it("does not highlight proper nouns or numerals or open popover for them", async () => {
    const fetchSpy = mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "København",
          normalized_token: "københavn",
          lemma_candidate: "København",
          pos_tag: "PROPN",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "42",
          normalized_token: "42",
          lemma_candidate: "42",
          pos_tag: "NUM",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationHandler: async () => {
        throw new Error("translation endpoint should not be called for proper nouns or numerals")
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("København 42 ")
    await waitFor(() => {
      expect(getNotesEditor().querySelector("mark")).not.toBeInTheDocument()
    })

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.queryByText(/^translations$/i)).not.toBeInTheDocument()
    const translationCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/wordbank/translation"),
    )
    expect(translationCalls).toHaveLength(0)
  })

  it("adjective popover shows gender and number with translation", async () => {
    const fetchSpy = mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "stor",
          normalized_token: "stor",
          lemma_candidate: "stor",
          pos_tag: "ADJ",
          morphology: "Degree=Pos|Gender=Com|Number=Plur",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "stor",
        lemma: "stor",
        english_translation: "big",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    setNotesEditorText("stor ")

    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 140, clientY: 120 })

    expect(await screen.findByText(/^ADJ$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^Common$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^big$/i)).toBeInTheDocument()
    const translationCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/wordbank/translation"),
    )
    expect(translationCalls).toHaveLength(1)
  })

  it("aux popover follows verb layout and shows translation", async () => {
    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "har",
          normalized_token: "har",
          lemma_candidate: "have",
          pos_tag: "AUX",
          morphology: "Mood=Ind|Tense=Pres|VerbForm=Fin",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "have",
          matched_surface_form: "have",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "har",
        lemma: "have",
        english_translation: "have",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    setNotesEditorText("har ")

    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(mark as HTMLElement, { clientX: 150, clientY: 130 })

    const addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^AUX$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Present$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^\(have\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^have$/i)).toBeInTheDocument()
  })
})
