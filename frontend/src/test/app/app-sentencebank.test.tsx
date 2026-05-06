import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor } from "@/test/app-test-helpers"

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

    expect(screen.getByText(/^jeg$/i).closest("button")).toBeInTheDocument()
    expect(screen.getByText(/^elsker$/i).closest("button")).toBeInTheDocument()
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
    fireEvent.click((await screen.findByText(/^elsker$/i)).closest("button") as HTMLButtonElement)

    expect(await screen.findByRole("heading", { name: /^elske$/i })).toBeInTheDocument()
    expect(screen.getByText(/^love$/i)).toBeInTheDocument()
  })

  it("clicking a pronoun token opens the shared pronouns page", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "du", variation_count: 1 }],
      },
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Du elsker dansk",
            english_translation: "you love danish",
            created_at: "2026-05-03T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Du",
                stored_lemma: "du",
                lexeme_id: 11,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs|Case=Nom|Person=2|Number=Sing",
                english_translation: "you",
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
    fireEvent.click(await screen.findByRole("button", { name: /du elsker dansk/i }))
    fireEvent.click((await screen.findByText(/^du$/i)).closest("button") as HTMLButtonElement)

    expect(await screen.findByRole("heading", { name: /personal pronouns/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /possessive pronouns/i })).toBeInTheDocument()
    expect(screen.getAllByText(/^du$/i).length).toBeGreaterThan(0)
    expect(fetchSpy.mock.calls.some(([input]) => String(input).includes("__pronouns_personal_possessive"))).toBe(false)
  })

  it("clicking an hv token opens the shared question words page with related sentences", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "hvor", variation_count: 1 }],
      },
      sentencebankResponse: {
        items: [
          {
            id: 2,
            source_text: "Hvor bor du?",
            english_translation: "where do you live?",
            created_at: "2026-05-03T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Hvor",
                stored_lemma: "hvor",
                lexeme_id: 12,
                meaning_id: null,
                pos_tag: "ADV",
                morphology: "PronType=Int",
                english_translation: "where",
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
    fireEvent.click(await screen.findByRole("button", { name: /hvor bor du/i }))
    fireEvent.click((await screen.findByText(/^hvor$/i)).closest("button") as HTMLButtonElement)

    expect(await screen.findByRole("heading", { name: /place, time, manner and reason/i })).toBeInTheDocument()
    expect(screen.getAllByText(/^hvor$/i).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: /see examples/i }))
    expect(await screen.findByText(/where do you live/i)).toBeInTheDocument()
    expect(fetchSpy.mock.calls.some(([input]) => String(input).includes("__hv_questions"))).toBe(false)
  })

  it("clicking an unsaved sentence token saves it through the sentence-token flow", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmaDetailsResponse: {
        lemma: "læse",
        english_translation: null,
        is_sectioned: true,
        pos_tag: "VERB",
        morphology: "VerbForm=Inf",
        surface_forms: [],
        meaning_sections: [
          {
            id: 30,
            meaning_key: "read",
            gloss: "read",
            english_translation: "read",
            pos_tag: "VERB",
            morphology: "VerbForm=Inf",
            surface_forms: [{ form: "læser", has_pronunciation: false }],
          },
        ],
      },
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg læser en bog",
            english_translation: "i am reading a book",
            created_at: "2026-05-03T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "læser",
                save_status: "unsaved",
                lemma_candidate: "læse",
                stored_lemma: null,
                lexeme_id: null,
                meaning_id: null,
                pos_tag: "VERB",
                morphology: "Mood=Ind|Tense=Pres",
                english_translation: null,
                gloss_translation: null,
              },
            ],
          },
        ],
      },
      saveSentenceTokenHandler: async (input, init) => {
        expect(String(input)).toContain("/api/sentencebank/sentences/1/tokens/0/save")
        expect(init?.method).toBe("POST")
        return responseOf({
          id: 1,
          source_text: "Jeg læser en bog",
          english_translation: "i am reading a book",
          created_at: "2026-05-03T12:00:00.000Z",
          tokens: [
            {
              token_index: 0,
              surface_form: "læser",
              save_status: "saved",
              lemma_candidate: "læse",
              stored_lemma: "læse",
              lexeme_id: 12,
              meaning_id: 30,
              pos_tag: "VERB",
              morphology: "Mood=Ind|Tense=Pres",
              gloss: "read",
              english_translation: "read",
              gloss_translation: null,
            },
          ],
          saved_token: {
            token_index: 0,
            surface_form: "læser",
            save_status: "saved",
            lemma_candidate: "læse",
            stored_lemma: "læse",
            lexeme_id: 12,
            meaning_id: 30,
            pos_tag: "VERB",
            morphology: "Mood=Ind|Tense=Pres",
            gloss: "read",
            english_translation: "read",
            gloss_translation: null,
          },
          message: "Added læser to wordbank.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /jeg læser en bog/i }))
    fireEvent.click((await screen.findByText(/^læser$/i)).closest("button") as HTMLButtonElement)

    await waitFor(() => {
      expect(fetchSpy.mock.calls.some(([input, init]) => (
        String(input).endsWith("/api/sentencebank/sentences/1/tokens/0/save") && init?.method === "POST"
      ))).toBe(true)
    })
    expect(await screen.findByRole("heading", { name: /^læse$/i })).toBeInTheDocument()
  })

  it("hovering a token card underlines that word in the sentence text", async () => {
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
    fireEvent.click(await screen.findByRole("button", { name: /jeg elsker dansk/i }))

    const elskerButton = (await screen.findByText(/^elsker$/i)).closest("button") as HTMLButtonElement
    fireEvent.mouseEnter(elskerButton)

    const sentenceLine = screen.getByRole("button", { name: /^listen to jeg elsker dansk$/i })
    expect(Array.from(sentenceLine.querySelectorAll("span.underline")).map((element) => element.textContent)).toEqual(["elsker"])

    fireEvent.mouseLeave(elskerButton)
    expect(sentenceLine.querySelector("span.underline")).toBeNull()
  })

  it("request-shape: plays sentence pronunciation from the sentence page header", async () => {
    const fetchSpy = mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            has_pronunciation: true,
            tokens: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /jeg elsker dansk/i }))
    fireEvent.click(await screen.findByRole("button", { name: /^listen to jeg elsker dansk$/i }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/sentencebank/pronunciation?sentence_id=1"),
        undefined,
      )
    })
  })

  it("request-shape: regenerates sentence pronunciation from the sentence header context menu", async () => {
    const fetchSpy = mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            has_pronunciation: true,
            tokens: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /jeg elsker dansk/i }))

    const listenButton = await screen.findByRole("button", { name: /^listen to jeg elsker dansk$/i })
    fireEvent.contextMenu(listenButton)
    fireEvent.click(await screen.findByRole("menuitem", { name: /regenerate audio/i }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/sentencebank/sentences/pronunciation"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            sentence_id: 1,
            force: true,
          }),
        }),
      )
    })
  })

  it("interaction: sentence header context menu can say the sentence slowly", async () => {
    const originalAudio = globalThis.Audio
    const createdAudio: Array<{ playbackRate: number }> = []

    class SlowAudioMock {
      src = ""
      playbackRate = 1

      constructor(src?: string) {
        this.src = src ?? ""
        createdAudio.push(this)
      }

      play() {
        return Promise.resolve()
      }

      pause() {}
    }

    Object.defineProperty(globalThis, "Audio", {
      writable: true,
      value: SlowAudioMock,
    })

    try {
      mockFetchImplementation({
        sentencebankResponse: {
          items: [
            {
              id: 1,
              source_text: "Jeg elsker dansk",
              english_translation: "i love danish",
              created_at: "2026-02-28T12:00:00.000Z",
              has_pronunciation: true,
              tokens: [],
            },
          ],
        },
      })

      renderApp()
      await screen.findByLabelText("backend-connection-status")

      fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
      fireEvent.click(await screen.findByRole("button", { name: /jeg elsker dansk/i }))

      const listenButton = await screen.findByRole("button", { name: /^listen to jeg elsker dansk$/i })
      fireEvent.contextMenu(listenButton)
      fireEvent.click(await screen.findByRole("menuitem", { name: /say slowly/i }))

      await waitFor(() => {
        expect(createdAudio).toHaveLength(1)
      })
      expect(createdAudio[0]?.playbackRate).toBe(0.7)
    } finally {
      Object.defineProperty(globalThis, "Audio", {
        writable: true,
        value: originalAudio,
      })
    }
  })
})
