import { fireEvent, mockFetchImplementation, renderApp, screen } from "@/test/app-test-helpers"

describe("App sentencebank", () => {
  it("shows saved sentences in sentencebank list (no token cards)", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Jeg",
                stored_lemma: "jeg",
                lexeme_id: 11,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                english_translation: "i",
                gloss_translation: null,
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))

    expect(await screen.findByText(/jeg elsker dansk/i)).toBeInTheDocument()
    expect(screen.getByText(/i love danish/i)).toBeInTheDocument()
    // token buttons not shown in list
    expect(screen.queryByRole("button", { name: /^jeg$/i })).not.toBeInTheDocument()
  })

  it("clicking sentence in list shows sentence page with token cards", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Jeg",
                stored_lemma: "jeg",
                lexeme_id: 11,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                english_translation: "i",
                gloss_translation: null,
              },
              {
                token_index: 1,
                surface_form: "elsker",
                stored_lemma: "elske",
                lexeme_id: 12,
                meaning_id: 3,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                english_translation: "love",
                gloss_translation: "love",
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    await screen.findByText(/jeg elsker dansk/i)

    // click the sentence card to open sentence page
    fireEvent.click(screen.getByRole("button", { name: /jeg elsker dansk/i }))

    expect(screen.getByRole("button", { name: /jeg/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /elsker/i })).toBeInTheDocument()
  })

  it("clicking token on sentence page opens wordbank word page", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "elsker",
                stored_lemma: "elske",
                lexeme_id: 12,
                meaning_id: 3,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                english_translation: "love",
                gloss_translation: "love",
              },
            ],
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "elske",
        english_translation: "love",
        pos_tag: "VERB",
        morphology: "VerbForm=Inf|Voice=Act",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 3,
            meaning_key: "love",
            gloss: "love",
            english_translation: "love",
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            surface_forms: [],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    await screen.findByText(/jeg elsker dansk/i)

    // open sentence page first
    fireEvent.click(screen.getByRole("button", { name: /jeg elsker dansk/i }))

    // now click token to go to wordbank
    fireEvent.click(await screen.findByRole("button", { name: /elsker/i }))

    expect(await screen.findByRole("heading", { name: /^elske$/i })).toBeInTheDocument()
    expect(screen.getByText(/^love$/i)).toBeInTheDocument()
  })
})
