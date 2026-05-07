import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, within } from "@/test/app-test-helpers"

describe("App wordbank HV questions", () => {
  it("shows built-in references in an empty wordbank", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(await screen.findByRole("button", { name: /personal pronouns/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /possessive pronouns/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /question words/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /numbers/i })).toBeInTheDocument()
    expect(screen.queryByText(/no saved lemmas yet/i)).not.toBeInTheDocument()
  })

  it("generates examples from the HV card context menu", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
      staticExamplePreviewHandler: async (_input, init) => {
        expect(String(init?.body ?? "")).toBe(JSON.stringify({ stored_lemma: "hvor" }))
        return responseOf({
          source_text: "hvor bor du",
          english_translation: "Where do you live?",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /question words/i }))
    expect(await screen.findByText(/^hvor$/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /generate example/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /see examples/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/no sentences yet/i)).not.toBeInTheDocument()
    expect(screen.getAllByText(/place, time, manner & reason/i).length).toBeGreaterThan(0)

    const hvorCard = screen.getByText(/^hvor$/i).closest("[data-slot='context-menu-trigger']")
    expect(hvorCard).not.toBeNull()
    fireEvent.contextMenu(hvorCard as HTMLElement)
    fireEvent.click(await screen.findByRole("menuitem", { name: /generate example/i }))

    expect(await screen.findByRole("dialog", { name: /generated example/i })).toBeInTheDocument()
    expect(fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/sentencebank/static-example-preview"))).toBe(true)
  })

  it("opens matching examples in a dialog and links them to sentence pages", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
      sentencebankResponse: {
        items: [
          {
            id: 21,
            source_text: "hvor bor du",
            english_translation: "Where do you live?",
            created_at: "2026-05-04T08:00:00.000Z",
            has_pronunciation: false,
            tokens: [
              { token_index: 0, surface_form: "hvor", save_status: "saved", stored_lemma: "hvor", lexeme_id: 1, meaning_id: null, pos_tag: "ADV", morphology: "PronType=Int", gloss: null, english_translation: "where", gloss_translation: null },
              { token_index: 1, surface_form: "bor", save_status: "unsaved", stored_lemma: null, lexeme_id: null, meaning_id: null, pos_tag: null, morphology: null, gloss: null, english_translation: null, gloss_translation: null },
            ],
          },
          {
            id: 22,
            source_text: "hvor er stationen",
            english_translation: "Where is the station?",
            created_at: "2026-05-04T08:01:00.000Z",
            has_pronunciation: false,
            tokens: [
              { token_index: 0, surface_form: "hvor", save_status: "saved", stored_lemma: "hvor", lexeme_id: 1, meaning_id: null, pos_tag: "ADV", morphology: "PronType=Int", gloss: null, english_translation: "where", gloss_translation: null },
            ],
          },
          {
            id: 23,
            source_text: "hvor går vi hen",
            english_translation: "Where are we going?",
            created_at: "2026-05-04T08:02:00.000Z",
            has_pronunciation: false,
            tokens: [
              { token_index: 0, surface_form: "hvor", save_status: "saved", stored_lemma: "hvor", lexeme_id: 1, meaning_id: null, pos_tag: "ADV", morphology: "PronType=Int", gloss: null, english_translation: "where", gloss_translation: null },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /question words/i }))
    fireEvent.click(await screen.findByRole("button", { name: /see examples/i }))

    const dialog = await screen.findByRole("dialog", { name: /hvor examples/i })
    expect(within(dialog).queryByText(/saved sentence/i)).not.toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: /hvor bor du/i })).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: /hvor er stationen/i })).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: /hvor går vi hen/i })).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole("button", { name: /hvor går vi hen/i }))
    expect(await screen.findByText(/where are we going/i)).toBeInTheDocument()
  })
})
