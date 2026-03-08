import { act, fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, toast, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App playground", () => {
  it("shows lesson notes in playground", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByText(/connected/i)

    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
  })

  it("notes editor accepts typing and paste-like updates", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const editor = getNotesEditor()
    expect(editor).toHaveAttribute("spellcheck", "false")
    expect(editor).toHaveAttribute("autocorrect", "off")
    expect(editor).toHaveAttribute("autocapitalize", "off")
    expect(editor).toHaveAttribute("autocomplete", "off")

    setNotesEditorText("Jeg kan godt lide bogen")
    expect(getNotesEditor()).toHaveTextContent("Jeg kan godt lide bogen")

    setNotesEditorText("linje 1\nlinje 2")
    expect(getNotesEditor()).toHaveTextContent(/linje 1/i)
    expect(getNotesEditor()).toHaveTextContent(/linje 2/i)
  })

  it("debounce collapses rapid typing into one analyze call", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({ tokens: [] })
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("Jeg")
    setNotesEditorText("Jeg kan")
    setNotesEditorText("Jeg kan godt lide bogen ")

    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    expect(analyzeBodies).toHaveLength(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
      await Promise.resolve()
    })
    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "Jeg kan godt lide bogen" }))
  })

  it("does not analyze unfinished trailing token until finalization", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({
          tokens: [
            {
              surface_token: "bogen",
              normalized_token: "bogen",
              lemma_candidate: "bog",
              classification: "variation",
              match_source: "lemma",
              matched_lemma: "bog",
              matched_surface_form: null,
            },
          ],
        })
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")
    setNotesEditorText("b")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("bo")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("boge")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("bogen")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(analyzeBodies).toHaveLength(0)

    setNotesEditorText("bogen ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "bogen" }))

    expect(screen.getAllByText(/^bogen$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("stale responses do not overwrite newer results", async () => {
    vi.useFakeTimers()
    const resolvers: Array<(value: Response) => void> = []

    mockFetchImplementation({
      analyzeHandler: () =>
        new Promise<Response>((resolve) => {
          resolvers.push(resolve)
        }),
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("første ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    setNotesEditorText("anden ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(resolvers).toHaveLength(2)

    await act(async () => {
      resolvers[1](
        responseOf({
          tokens: [
            {
              surface_token: "anden",
              normalized_token: "anden",
              lemma_candidate: "anden",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)

    await act(async () => {
      resolvers[0](
        responseOf({
          tokens: [
            {
              surface_token: "første",
              normalized_token: "første",
              lemma_candidate: "første",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.queryByText(/^første$/i)).not.toBeInTheDocument()
    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("highlights new, variation, and typo_likely tokens in the editor", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "bogen",
          normalized_token: "bogen",
          lemma_candidate: "bog",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "bog",
          matched_surface_form: null,
        },
        {
          surface_token: "spisr",
          normalized_token: "spisr",
          lemma_candidate: "spiser",
          classification: "typo_likely",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "nyord",
          normalized_token: "nyord",
          lemma_candidate: "nyord",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kan bogen spisr nyord ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const editor = getNotesEditor()
    expect(editor.querySelector('mark[data-status="variation"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="typo_likely"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="new"]')).toBeInTheDocument()
  })

  it("does not visually highlight uncertain tokens and keeps known tokens unstyled", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "MilkoScna",
          normalized_token: "milkoscna",
          lemma_candidate: null,
          classification: "uncertain",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kan MilkoScna ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const editor = getNotesEditor()
    expect(editor.querySelector('mark[data-status="known"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="uncertain"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="new"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="variation"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="typo_likely"]')).not.toBeInTheDocument()
  })

  it("highlights full words at the start of each new line", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "asdfsadf",
          normalized_token: "asdfsadf",
          lemma_candidate: "asdfsadf",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
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
        {
          surface_token: "komputer",
          normalized_token: "komputer",
          lemma_candidate: "komputer",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "dyr",
          normalized_token: "dyr",
          lemma_candidate: "dyr",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("asdfsadf\n\nkatten \n\nkomputer\n\ndyr ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const marks = Array.from(getNotesEditor().querySelectorAll("mark")).map((node) => node.textContent)
    expect(marks).toEqual(expect.arrayContaining(["asdfsadf", "katten", "komputer", "dyr"]))
    expect(marks).not.toContain("atten")
    expect(marks).not.toContain("mputer")
  })

  it("renders hash comments with dedicated comment marks", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "lide",
          normalized_token: "lide",
          lemma_candidate: "lide",
          classification: "known",
          match_source: "exact",
          matched_lemma: "lide",
          matched_surface_form: "lide",
        },
      ],
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kan # min kommentar\nlide # anden kommentar")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const commentMarks = Array.from(getNotesEditor().querySelectorAll('mark[data-comment="true"]'))
    expect(commentMarks.map((node) => node.textContent)).toEqual(["# min kommentar", "# anden kommentar"])
  })

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
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

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
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })
    await screen.findByRole("button", { name: /add variation/i })
    expect(enrichCalls).toBe(1)

    setNotesEditorText("katten  ")
    await waitFor(() => {
      const nextMark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(nextMark).toBeInTheDocument()
    })

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
        surface_forms: [{ form: "bogen", english_translation: "book" }],
      },
      translationResponse: {
        status: "generated",
        source_word: "bogen",
        lemma: "bog",
        english_translation: "book",
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("bogen ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='known']")
      expect(mark).toBeInTheDocument()
    })

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
    expect(within(popoverContent as HTMLElement).getByText(/^hus$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^\(hus\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^t-word$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByTestId("noun-translation-skeleton")).toBeInTheDocument()
  })

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
    screen.getByLabelText("backend-connection-status")

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
    screen.getByLabelText("backend-connection-status")

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
    screen.getByLabelText("backend-connection-status")
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
    screen.getByLabelText("backend-connection-status")
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

  it("keeps editor focus when opening popover and dismisses popover when typing", async () => {
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
      translationResponse: {
        status: "generated",
        source_word: "katten",
        lemma: "kat",
        english_translation: "cat",
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    expect(await screen.findByRole("button", { name: /add variation/i })).toBeInTheDocument()
    expect(getNotesEditor().contains(document.activeElement)).toBe(true)

    setNotesEditorText("katten x")
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /add variation/i })).not.toBeInTheDocument()
    })
  })

  it("adding from popover calls backend, re-analyzes, and shows success toast", async () => {
    vi.useRealTimers()
    let analyzeCallCount = 0
    const addBodies: string[] = []

    mockFetchImplementation({
      enrichTokenResponse: {
        query_surface: "kat",
        query_lemma: "kat",
        classification: "new",
        matched_lemma: null,
        matched_lemma_summary: null,
        query_pos_tag: null,
        query_morphology: null,
        resolved_surface: "kat",
        resolved_lemma: "kat",
        da_to_en_translation: null,
        en_to_da_translation: null,
        en_to_da_lemma: null,
        en_to_da_pos_tag: null,
        en_to_da_morphology: null,
        query_language: null,
        query_language_confidence: null,
        word_actions: [
          {
            action_type: "add_as_new",
            surface: "kat",
            lemma: "kat",
            translation_label: "kat",
            direction: "da_to_en",
            direction_label: "Danish -> English",
            pos_tag: null,
            morphology: null,
            show_lemma: false,
          },
        ],
      },
      analyzeHandler: async () => {
        analyzeCallCount += 1
        if (analyzeCallCount === 1) {
          return responseOf({
            tokens: [
              {
                surface_token: "kat",
                normalized_token: "kat",
                lemma_candidate: "kat",
                classification: "new",
                match_source: "none",
                matched_lemma: null,
                matched_surface_form: null,
              },
            ],
          })
        }
        return responseOf({
          tokens: [
            {
              surface_token: "kat",
              normalized_token: "kat",
              lemma_candidate: "kat",
              classification: "known",
              match_source: "exact",
              matched_lemma: "kat",
              matched_surface_form: "kat",
            },
          ],
        })
      },
      addWordHandler: async (_input, init) => {
        addBodies.push(String(init?.body ?? ""))
        return responseOf({
          status: "inserted",
          stored_lemma: "kat",
          stored_surface_form: "kat",
          source: "manual",
          message: "Added 'kat' to wordbank.",
        })
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kat ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    fireEvent.click(await screen.findByRole("button", { name: /add to wordbank/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    await waitFor(async () => {
      await Promise.resolve()
      await Promise.resolve()
      expect(analyzeCallCount).toBeGreaterThanOrEqual(2)
    })

    expect(addBodies).toHaveLength(1)
    expect(addBodies[0]).toBe(JSON.stringify({ surface_token: "kat", lemma_candidate: "kat" }))
    expect(vi.mocked(toast.success)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Added 'kat' to wordbank.")
  })

  it("shows error toast when popover add fails", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kat",
          normalized_token: "kat",
          lemma_candidate: "kat",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      addWordOk: false,
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kat ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    fireEvent.click(await screen.findByRole("button", { name: /add to wordbank/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("add word request failed")
  })


})
