import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, screen, setNotesEditorText, vi, waitFor } from "@/test/app-test-helpers"

describe("App wordbank", () => {
  it("variation cards show translated gloss instead of raw Danish gloss", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        surface_forms: [
          {
            form: "bogen",
            lemma: "bog",
            lemma_translation: "book",
            gloss: "til læsning",
            gloss_translation: "for reading",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Def",
            has_pronunciation: true,
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.getByText(/\(book, for reading\)/i)).toBeInTheDocument()
    expect(screen.queryByText(/\(book, til læsning\)/i)).not.toBeInTheDocument()
  })

  it("does not render an empty-variation message when there are no saved variations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lære", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "lære",
        english_translation: "learn",
        is_sectioned: false,
        pos_tag: "VERB",
        morphology: "VerbForm=Inf",
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lære/i }))

    expect(await screen.findByRole("heading", { name: /^lære$/i })).toBeInTheDocument()
    expect(screen.queryByText(/no saved variations for this lemma/i)).not.toBeInTheDocument()
  })

  it("defers loading the full wordbank list until the wordbank section opens", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(
      fetchSpy.mock.calls.filter(([input]) => String(input).endsWith("/api/wordbank/lemmas")),
    ).toHaveLength(0)

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))

    await screen.findByRole("button", { name: /bog/i })
    expect(
      fetchSpy.mock.calls.filter(([input]) => String(input).endsWith("/api/wordbank/lemmas")),
    ).toHaveLength(1)
  })

  it("regenerates pronunciation from the word page action", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        surface_forms: [{ form: "bogen", has_pronunciation: true }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const regenerateButton = await screen.findByRole("button", { name: /regenerate audio/i })
    expect(screen.getByRole("button", { name: /show verification error info/i })).toBeDisabled()
    fireEvent.click(regenerateButton)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/lexemes/pronunciation"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            stored_lemma: "bog",
            stored_surface_form: "bog",
            force: true,
          }),
        }),
      )
    })
  })

  it("keeps the lemma pronunciation action playable when the only saved form is hidden from details", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "kone", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "kone",
        english_translation: "wife",
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing",
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /kone/i }))

    const listenButton = await screen.findByRole("button", { name: /listen to kone/i })
    expect(listenButton).toBeEnabled()
    fireEvent.click(listenButton)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/pronunciation?form=kone"),
        undefined,
      )
    })
  })

  it("shows verification error info on the word page and in notifications", async () => {
    vi.useRealTimers()

    const fetchSpy = mockFetchImplementation({
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
      lemmasResponse: {
        items: [{ lemma: "kat", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "kat",
        english_translation: "cat",
        surface_forms: [{ form: "kat", has_pronunciation: true }],
      },
      verifyWordResponse: {
        stored_lemma: "kat",
        stored_surface_form: "kat",
        verification: {
          status: "error",
          provider: "gemini",
          reviewer_role: "Professional Danish Language Expert",
          message: "Verification task failed: Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY.",
          composed_word_count: null,
          problem: "Stored POS and translation are inconsistent for this entry.",
          change_to_implement: "Update POS to NOUN and translation to 'cat'.",
          suggested_changes: {
            lemma_pos_tag: "NOUN",
            lemma_morphology: "Gender=Com|Number=Sing",
            surface_pos_tag: "NOUN",
            surface_morphology: "Definite=Def|Number=Sing",
            lexeme_translation: "cat",
          },
        },
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("kat ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    }, { timeout: 3_000 })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })
    fireEvent.click(await screen.findByRole("button", { name: /add to wordbank/i }))

    const notificationsButton = await screen.findByRole("button", { name: /show notifications \(1 unread\)/i })
    fireEvent.click(notificationsButton)
    const notificationList = await screen.findByLabelText("notification-list")
    expect(notificationList).toHaveTextContent("ERROR kat:")
    expect(notificationList).toHaveTextContent("Change:")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /kat/i }))
    const infoButton = await screen.findByRole("button", { name: /show verification error info/i })
    expect(infoButton).toBeEnabled()
    fireEvent.click(infoButton)

    expect(await screen.findByText("Verification Error")).toBeInTheDocument()
    expect(screen.getByText("Problem")).toBeInTheDocument()
    expect(screen.getByText("Change to implement")).toBeInTheDocument()
    expect(screen.getByText(/stored pos and translation are inconsistent/i)).toBeInTheDocument()
    expect(screen.getByText(/update pos to noun and translation to 'cat'/i)).toBeInTheDocument()
    expect(screen.getByText(/specific fields to change/i)).toBeInTheDocument()
    expect(screen.getByText(/lemma pos: noun/i)).toBeInTheDocument()
    expect(screen.getByText(/lemma morphology: gender=com\|number=sing/i)).toBeInTheDocument()
    expect(screen.getByText(/lemma translation: cat/i)).toBeInTheDocument()

    const applyButton = screen.getByRole("button", { name: /apply gemini changes/i })
    expect(applyButton).toBeEnabled()
    fireEvent.click(applyButton)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/lexemes/apply-verification-changes"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            stored_lemma: "kat",
            stored_surface_form: "kat",
            meaning_id: null,
            suggested_changes: {
              lemma_pos_tag: "NOUN",
              lemma_morphology: "Gender=Com|Number=Sing",
              surface_pos_tag: "NOUN",
              surface_morphology: "Definite=Def|Number=Sing",
              lexeme_translation: "cat",
            },
            provider: "gemini",
          }),
        }),
      )
    })
  }, 15_000)
})
