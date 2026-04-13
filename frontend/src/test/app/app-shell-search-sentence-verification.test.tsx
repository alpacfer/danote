import { act, fireEvent, mockFetchImplementation, renderApp, responseOf, screen, vi, waitFor, within } from "@/test/app-test-helpers"

function openSearch() {
  fireEvent.click(screen.getByRole("button", { name: /search/i }))
  return screen.findByRole("dialog")
}

function typeInSearch(dialog: HTMLElement, text: string) {
  const input = within(dialog).getByPlaceholderText(/search words and notes/i)
  fireEvent.change(input, { target: { value: text } })
}

function getSentenceOption(dialog: HTMLElement) {
  return within(dialog).getByRole("option")
}

describe("Sentence verification in search", () => {
  it("shows verification loading UI while verifying a sentence", async () => {
    const resolvers: Array<() => void> = []
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async () => {
        await new Promise<void>((resolve) => {
          resolvers.push(resolve)
        })
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: "jeg er glad",
          english_translation: "I am happy",
          is_valid: true,
          errors: [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    expect(await within(dialog).findByRole("option")).toHaveAttribute("aria-disabled", "true")
    expect(within(dialog).getByTestId("sentence-search-translation-skeleton")).toBeInTheDocument()
    resolvers.forEach((resolve) => resolve())
  })

  it("shows fast preview result immediately then replaces it with the full result", async () => {
    const previewModes: boolean[] = []
    let resolveFullPreview: (() => void) | null = null

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { fast?: boolean }
        previewModes.push(Boolean(body.fast))
        if (body.fast) {
          return responseOf({
            status: "preview",
            query_language: "da",
            source_text: "jeg er glad",
            english_translation: "I am happy",
            is_valid: true,
            errors: [],
            message: null,
          })
        }
        await new Promise<void>((resolve) => {
          resolveFullPreview = resolve
        })
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: "jeg er glad",
          english_translation: "I am happy",
          is_valid: true,
          errors: [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(previewModes).toContain(true)
      expect(previewModes).toContain(false)
      const option = getSentenceOption(dialog)
      expect(within(option).getByText(/^jeg er glad$/i)).toBeInTheDocument()
      expect(within(option).getByText("I am happy")).toBeInTheDocument()
    })
    expect(within(dialog).queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()

    resolveFullPreview?.()

    await waitFor(() => {
      expect(within(dialog).queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()
    })
  })

  it("enables save after successful verification and shows the sentence above the translation", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentencebankResponse: {
        items: [
          {
            id: 90,
            source_text: "jeg er glad",
            english_translation: "i am happy",
            created_at: "2026-04-12T10:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "jeg",
                stored_lemma: "jeg",
                lexeme_id: 1,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                gloss: null,
                english_translation: "i",
                gloss_translation: null,
              },
            ],
          },
        ],
      },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })
    const option = getSentenceOption(dialog)
    expect(within(option).getByText(/^jeg er glad$/i)).toBeInTheDocument()
    expect(within(option).getByText("I am happy")).toBeInTheDocument()
    expect(within(option).queryByText("EN→DA")).not.toBeInTheDocument()
    expect(within(option).queryByText("Auto-translated from English")).not.toBeInTheDocument()
  })

  it("does not enter sentence mode for multi-word queries over 100 chars", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(
      dialog,
      "et meget langt eksempel på en sætning med mange ord her som fortsætter langt ud over den nye grænse for søgning",
    )

    expect(within(dialog).queryByText(/^Sentence$/i)).not.toBeInTheDocument()
    expect(within(dialog).queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()
    expect(within(dialog).queryByTestId("sentence-verification-skeleton")).not.toBeInTheDocument()
  })

  it("shows a characters remaining indicator for sentence-length searches", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    const counter = await within(dialog).findByTestId("sentence-search-character-counter")
    expect(counter).toHaveTextContent("11/100")
    expect(counter).toHaveAttribute("title", "89 characters remaining")
  })

  it("underlines the typo in the input and shows only the correction plus corrected translation in the card", async () => {
    const previewRequests: string[] = []
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { source_text?: string }
        const sourceText = body.source_text ?? ""
        previewRequests.push(sourceText)
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: sourceText === "Jeg er glat" ? "Jeg er glad" : sourceText,
          english_translation: sourceText === "Jeg er glat" ? "I am happy" : "I am slick",
          is_valid: sourceText !== "Jeg er glat",
          errors: sourceText === "Jeg er glat" ? [{ start: 7, end: 11, message: "typo" }] : [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "Jeg er glat")

    await waitFor(() => {
      expect(previewRequests).toContain("Jeg er glat")
    })

    const overlay = await within(dialog).findByTestId("sentence-search-input-overlay")
    const option = getSentenceOption(dialog)
    expect(within(overlay).getByText("glat")).toHaveClass("underline")
    expect(within(option).getByText("Jeg er glad")).toBeInTheDocument()
    expect(await within(option).findByText("I am happy")).toBeInTheDocument()
    expect(within(option).queryByText(/^Jeg er glat$/i)).not.toBeInTheDocument()
    expect(within(option).queryByText("Corrected:")).not.toBeInTheDocument()
  })

  it("sends capitalization-preserving sentence text to sentence preview", async () => {
    const previewRequests: string[] = []

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { source_text?: string }
        previewRequests.push(body.source_text ?? "")
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: body.source_text ?? "",
          english_translation: "I am happy",
          is_valid: true,
          errors: [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "Jeg er glad")

    await waitFor(() => {
      expect(previewRequests).toContain("Jeg er glad")
    })
  })

  it("expands typo underline spans to the full word in the input", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: false,
        errors: [{ start: 8, end: 10, message: "partial typo span" }],
        message: null,
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glat")

    const overlay = await within(dialog).findByTestId("sentence-search-input-overlay")
    expect(within(overlay).getByText("glat")).toHaveClass("underline")
  })

  it("does not show an underline when capitalization-only findings have already been filtered out", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "i am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })

    const option = getSentenceOption(dialog)
    expect(within(dialog).queryByTestId("sentence-search-input-overlay")).not.toBeInTheDocument()
    expect(within(option).getByText(/^jeg er glad$/i)).toBeInTheDocument()
    expect(within(option).getByText("i am happy")).toBeInTheDocument()
  })

  it("saves the corrected sentence text when verification returns a correction", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "Jeg er glad",
        english_translation: null,
        is_valid: false,
        errors: [{ start: 7, end: 11, message: "typo" }],
        message: null,
      },
      addSentenceResponse: {
        status: "inserted",
        id: 99,
        source_text: "Jeg er glad",
        english_translation: null,
        created_at: "2026-04-12T10:00:00.000Z",
        message: 'Added "Jeg er glad" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "Jeg er glat")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })
    const item = getSentenceOption(dialog)
    fireEvent.click(item)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/sentencebank/sentences") || init?.method !== "POST") {
            return false
          }
          const body = JSON.parse(String(init.body ?? "{}")) as { source_text?: string }
          return body.source_text === "Jeg er glad"
        }),
      ).toBe(true)
    })
  })

  it("shows the generated translation on the pending sentence page while the saved sentence is still loading", async () => {
    let resolveAddSentence: (() => void) | null = null

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentencebankResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
      addSentenceHandler: async () => {
        await new Promise<void>((resolve) => {
          resolveAddSentence = resolve
        })
        return responseOf({
          status: "inserted",
          id: 91,
          source_text: "jeg er glad",
          english_translation: "I am happy",
          created_at: "2026-04-12T10:00:00.000Z",
          tokens: [],
          message: 'Added "jeg er glad" to sentencebank.',
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })
    expect(await within(dialog).findByText("I am happy")).toBeInTheDocument()

    fireEvent.click(getSentenceOption(dialog))

    expect(await screen.findByText("I am happy")).toBeInTheDocument()
    expect(screen.queryByTestId("sentence-page-translation-skeleton")).not.toBeInTheDocument()

    await act(async () => {
      resolveAddSentence?.()
    })
  })

  it("falls back to a savable sentence when verification fails", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewOk: false,
      addSentenceResponse: {
        status: "inserted",
        id: 77,
        source_text: "jeg er glad",
        english_translation: null,
        created_at: "2026-04-12T10:00:00.000Z",
        message: 'Added "jeg er glad" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })
    const item = getSentenceOption(dialog)
    fireEvent.click(item)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/sentencebank/sentences") || init?.method !== "POST") {
            return false
          }
          const body = JSON.parse(String(init.body ?? "{}")) as { source_text?: string }
          return body.source_text === "jeg er glad"
        }),
      ).toBe(true)
    })
  })

  it("pressing Enter once saves the selected sentence result", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
      addSentenceResponse: {
        status: "inserted",
        id: 88,
        source_text: "jeg er glad",
        english_translation: "I am happy",
        created_at: "2026-04-12T10:00:00.000Z",
        message: 'Added "jeg er glad" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    const input = within(dialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(input, { target: { value: "jeg er glad" } })

    await waitFor(() => {
      const option = getSentenceOption(dialog)
      expect(option).toHaveAttribute("data-selected", "true")
      expect(option).not.toHaveAttribute("aria-disabled", "true")
    })

    fireEvent.keyDown(input, { key: "Enter" })

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.filter(
          ([request, init]) =>
            String(request).endsWith("/api/sentencebank/sentences")
            && init?.method === "POST",
        ),
      ).toHaveLength(1)
    })
  })

  it("closes search immediately while sentence save continues in the background", async () => {
    let resolveAddSentence: ((response: Response) => void) | null = null
    const addSentenceStarted = vi.fn()
    let hasSavedSentence = false

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentencebankHandler: async () => responseOf({
        items: hasSavedSentence ? [
          {
            id: 90,
            source_text: "jeg er glad",
            english_translation: "I am happy",
            created_at: "2026-04-12T10:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "jeg",
                stored_lemma: "jeg",
                lexeme_id: 1,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                gloss: null,
                english_translation: "i",
                gloss_translation: null,
              },
            ],
          },
        ] : [],
      }),
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "da",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
      addSentenceHandler: async () => {
        addSentenceStarted()
        return await new Promise<Response>((resolve) => {
          resolveAddSentence = resolve
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    const input = within(dialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(input, { target: { value: "jeg er glad" } })

    await waitFor(() => {
      const option = getSentenceOption(dialog)
      expect(option).toHaveAttribute("data-selected", "true")
      expect(option).not.toHaveAttribute("aria-disabled", "true")
    })

    fireEvent.keyDown(input, { key: "Enter" })

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    expect(addSentenceStarted).toHaveBeenCalledTimes(1)
    hasSavedSentence = true

    resolveAddSentence?.(responseOf({
      status: "inserted",
      id: 90,
      source_text: "jeg er glad",
      english_translation: "I am happy",
      created_at: "2026-04-12T10:00:00.000Z",
      tokens: [
        {
          token_index: 0,
          surface_form: "jeg",
          stored_lemma: "jeg",
          lexeme_id: 1,
          meaning_id: null,
          pos_tag: "PRON",
          morphology: "PronType=Prs",
          gloss: null,
          english_translation: "i",
          gloss_translation: null,
        },
      ],
      message: 'Added "jeg er glad" to sentencebank.',
    }))

    expect(await screen.findByText(/^jeg er glad$/i)).toBeInTheDocument()
  })

  it("shows translated-from-English icon, no raw-input underline, and saves the Danish preview", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "en",
        source_text: "jeg er glad",
        english_translation: "I am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
      addSentenceResponse: {
        status: "inserted",
        id: 120,
        source_text: "jeg er glad",
        english_translation: "I am happy",
        created_at: "2026-04-12T10:00:00.000Z",
        message: 'Added "jeg er glad" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "I am happy")

    expect(await within(dialog).findByLabelText("Translated from English")).toBeInTheDocument()
    expect(within(dialog).queryByText("EN→DA")).not.toBeInTheDocument()
    expect(within(dialog).queryByText("Auto-translated from English")).not.toBeInTheDocument()
    expect(within(dialog).queryByTestId("sentence-search-input-overlay")).not.toBeInTheDocument()

    fireEvent.click(getSentenceOption(dialog))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/sentencebank/sentences") || init?.method !== "POST") {
            return false
          }
          const body = JSON.parse(String(init.body ?? "{}")) as { source_text?: string }
          return body.source_text === "jeg er glad"
        }),
      ).toBe(true)
    })
  })

  it("preserves lowercase first-word casing for corrected english previews", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "ready",
        query_language: "en",
        source_text: "jeg er glad",
        english_translation: "i am happy",
        is_valid: true,
        errors: [],
        message: null,
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "i am hapy")

    await waitFor(() => {
      expect(getSentenceOption(dialog)).not.toHaveAttribute("aria-disabled", "true")
    })
    const option = getSentenceOption(dialog)
    expect(within(option).getByText("i am happy")).toBeInTheDocument()
    expect(within(option).queryByText("I am happy")).not.toBeInTheDocument()
  })

  it("shows a blocked English preview message and disables save", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewResponse: {
        status: "blocked",
        query_language: "en",
        source_text: null,
        english_translation: null,
        is_valid: false,
        errors: [],
        message: "Could not translate this English sentence to Danish.",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "I am happy")

    expect(await within(dialog).findByText("Could not translate this English sentence to Danish.")).toBeInTheDocument()
    const option = await within(dialog).findByRole("option")
    expect(option).toHaveAttribute("aria-disabled", "true")
    expect(within(option).getByText("Could not translate this English sentence to Danish.")).toBeInTheDocument()
  })
})
