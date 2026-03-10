import { act, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, vi } from "@/test/app-test-helpers"

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
})
