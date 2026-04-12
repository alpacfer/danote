import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

function openSearch() {
  fireEvent.click(screen.getByRole("button", { name: /search/i }))
  return screen.findByRole("dialog")
}

function typeInSearch(dialog: HTMLElement, text: string) {
  const input = within(dialog).getByPlaceholderText(/search words and notes/i)
  fireEvent.change(input, { target: { value: text } })
}

describe("Sentence verification in search", () => {
  it("shows verification loading UI while verifying a sentence", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    expect(await within(dialog).findByTestId("sentence-verification-skeleton")).toBeInTheDocument()
    expect(within(dialog).getByRole("option")).toHaveAttribute("aria-disabled", "true")
  })

  it("enables save after successful verification", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      verifySentenceResponse: {
        is_valid: true,
        errors: [],
        corrected_text: null,
        language: "da",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    await waitFor(() => {
      expect(within(dialog).getByRole("option")).not.toHaveAttribute("aria-disabled", "true")
    })
  })

  it("does not enter sentence mode for multi-word queries over 50 chars", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "et meget langt eksempel på en sætning med mange ord her")

    expect(within(dialog).queryByText(/^Sentence$/i)).not.toBeInTheDocument()
    expect(within(dialog).queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()
    expect(within(dialog).queryByTestId("sentence-verification-skeleton")).not.toBeInTheDocument()
  })

  it("shows corrected sentence when verification finds errors", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      verifySentenceResponse: {
        is_valid: false,
        errors: [{ start: 7, end: 11, message: "typo" }],
        corrected_text: "jeg er glad",
        language: "da",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glat")

    expect(await within(dialog).findByText("Corrected:")).toBeInTheDocument()
    expect(within(dialog).getByText("jeg er glad")).toBeInTheDocument()
  })

  it("saves the corrected sentence text when verification returns a correction", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      verifySentenceResponse: {
        is_valid: false,
        errors: [{ start: 7, end: 11, message: "typo" }],
        corrected_text: "jeg er glad",
        language: "da",
      },
      addSentenceResponse: {
        status: "inserted",
        id: 99,
        source_text: "jeg er glad",
        english_translation: null,
        created_at: "2026-04-12T10:00:00.000Z",
        message: 'Added "jeg er glad" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glat")

    const item = await within(dialog).findByRole("option")
    await waitFor(() => {
      expect(item).not.toHaveAttribute("aria-disabled", "true")
    })
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

  it("falls back to a savable sentence when verification fails", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      verifySentenceOk: false,
      phraseTranslationResponse: {
        status: "generated",
        source_text: "jeg er glad",
        english_translation: "i am happy",
      },
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

    const item = await within(dialog).findByRole("option")
    await waitFor(() => {
      expect(item).not.toHaveAttribute("aria-disabled", "true")
    })
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
})
