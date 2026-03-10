import { act, fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, toast, vi, waitFor } from "@/test/app-test-helpers"

describe("App playground", () => {
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
