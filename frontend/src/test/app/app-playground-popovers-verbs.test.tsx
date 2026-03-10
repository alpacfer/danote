import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App playground", () => {
  it("does not retry noun translation when first response is unavailable", async () => {
    vi.useRealTimers()
    let translationCalls = 0

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
      translationHandler: async () => {
        translationCalls += 1
        return responseOf({
          status: "unavailable",
          source_word: "hus",
          lemma: "hus",
          english_translation: null,
        })
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("hus ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 180, clientY: 160 })

    const addButton = await screen.findByRole("button", { name: /add to wordbank/i })
    const popoverContent = addButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).queryByText(/^house$/i)).not.toBeInTheDocument()
    expect(translationCalls).toBe(1)
  })

  it("verb popover shows infinitive subtitle and present form in the title", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spiser",
          normalized_token: "spiser",
          lemma_candidate: "spise",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "spise",
          matched_surface_form: null,
          pos_tag: "VERB",
          morphology: "Mood=Ind|Tense=Pres|VerbForm=Fin",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "spiser",
        lemma: "spise",
        english_translation: "eat",
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("spiser ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 180, clientY: 150 })

    const addButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^spiser$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^\(spise\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^VERB$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Present$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^eat$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^Morphology: /i)).not.toBeInTheDocument()
  })

  it("verb popover maps participle morphology to past participle label in title", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spist",
          normalized_token: "spist",
          lemma_candidate: "spise",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "spise",
          matched_surface_form: null,
          pos_tag: "VERB",
          morphology: "Tense=Past|VerbForm=Part",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "spist",
        lemma: "spise",
        english_translation: "eaten",
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("spist ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 190, clientY: 155 })

    expect(await screen.findByText(/^Past participle$/i)).toBeInTheDocument()
  })

  it("remembers discovered verb metadata and reuses translation when later analysis degrades to X", async () => {
    vi.useRealTimers()
    let translationCalls = 0

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        const rawBody = String(init?.body ?? "{}")
        const payload = JSON.parse(rawBody) as { text?: string }

        if (payload.text === "hedde") {
          return responseOf({
            tokens: [
              {
                surface_token: "hedde",
                normalized_token: "hedde",
                lemma_candidate: "hedde",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "hedde",
                matched_surface_form: null,
                pos_tag: "VERB",
                morphology: "VerbForm=Inf",
              },
            ],
          })
        }

        if (payload.text === "hedde vinteren") {
          return responseOf({
            tokens: [
              {
                surface_token: "hedde",
                normalized_token: "hedde",
                lemma_candidate: "hedde",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "hedde",
                matched_surface_form: null,
                pos_tag: "X",
                morphology: null,
              },
              {
                surface_token: "vinteren",
                normalized_token: "vinteren",
                lemma_candidate: "vinter",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "vinter",
                matched_surface_form: null,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Definite=Def|Number=Sing",
              },
            ],
          })
        }

        return responseOf({ tokens: [] })
      },
      translationHandler: async () => {
        translationCalls += 1
        return responseOf({
          status: "generated",
          source_word: "hedde",
          lemma: "hedde",
          english_translation: "be called",
        })
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("hedde ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    let heddeMark = Array.from(getNotesEditor().querySelectorAll("mark[data-status='variation']")).find(
      (node) => node.textContent?.toLowerCase() === "hedde",
    )
    expect(heddeMark).toBeInTheDocument()
    fireEvent.click(heddeMark as HTMLElement, { clientX: 170, clientY: 145 })

    expect(await screen.findByText(/^VERB$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^\(hedde\)$/i)).not.toBeInTheDocument()
    expect(await screen.findByText(/^be called$/i)).toBeInTheDocument()
    expect(translationCalls).toBe(1)

    setNotesEditorText("hedde vinteren ")
    await waitFor(() => {
      const marks = getNotesEditor().querySelectorAll("mark[data-status='variation']")
      expect(marks.length).toBeGreaterThanOrEqual(2)
    })

    heddeMark = Array.from(getNotesEditor().querySelectorAll("mark[data-status='variation']")).find(
      (node) => node.textContent?.toLowerCase() === "hedde",
    )
    expect(heddeMark).toBeInTheDocument()
    fireEvent.click(heddeMark as HTMLElement, { clientX: 172, clientY: 147 })

    expect(await screen.findByText(/^VERB$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^\(hedde\)$/i)).not.toBeInTheDocument()
    expect(await screen.findByText(/^be called$/i)).toBeInTheDocument()
    expect(translationCalls).toBe(1)
  })

  it("updates popover fields when context changes a word to a new POS", async () => {
    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { text?: string }
        const text = body.text ?? ""
        if (text.trim() === "det") {
          return responseOf({
            tokens: [
              {
                surface_token: "det",
                normalized_token: "det",
                lemma_candidate: "den",
                pos_tag: "PRON",
                morphology: "Person=3|Number=Sing|PronType=Prs",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "den",
                matched_surface_form: "det",
              },
            ],
          })
        }
        return responseOf({
          tokens: [
            {
              surface_token: "det",
              normalized_token: "det",
              lemma_candidate: "den",
              pos_tag: "DET",
              morphology: "Gender=Neut|Number=Sing|PronType=Art",
              classification: "variation",
              match_source: "lemma",
              matched_lemma: "den",
              matched_surface_form: "det",
            },
            {
              surface_token: "hus",
              normalized_token: "hus",
              lemma_candidate: "hus",
              pos_tag: "NOUN",
              morphology: "Gender=Neut|Number=Sing",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      },
      translationResponse: {
        status: "generated",
        source_word: "det",
        lemma: "den",
        english_translation: "it",
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("det ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    let detMark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(detMark as HTMLElement, { clientX: 150, clientY: 130 })

    let addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    let popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^PRON$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^3rd person$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Singular$/i)).toBeInTheDocument()

    setNotesEditorText("det hus ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    detMark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(detMark as HTMLElement, { clientX: 152, clientY: 132 })

    addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    await waitFor(() => {
      expect(within(popoverContent as HTMLElement).getByText(/^DET$/)).toBeInTheDocument()
    })
    expect(within(popoverContent as HTMLElement).getByText(/^t-word$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Singular$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^3rd person$/i)).not.toBeInTheDocument()
  })
})
