import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor } from "@/test/app-test-helpers"

function expectToAppearBefore(first: HTMLElement, second: HTMLElement) {
  expect(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
}

function buildVariant(args: {
  corId: string
  lemma: string
  form?: string
  gloss: string
  posTag: string
  morphology: string
  gramRaw: string
  lemmaIdx: number
}) {
  return {
    cor_id: args.corId,
    form: args.form ?? args.lemma,
    lemma: args.lemma,
    gloss: args.gloss,
    gram_raw: args.gramRaw,
    lemma_idx: args.lemmaIdx,
    gram_code: 0,
    variation: 0,
    pos_tag: args.posTag,
    morphology: args.morphology,
    features: {},
    extra_tags: [],
    lemma_translation: args.gloss,
    saveable_translation: args.gloss,
  }
}

function buildOwnerDetails(args: {
  lemma?: string
  englishTranslation?: string | null
  meaningKey?: string
  status: "queued" | "ready" | "empty" | "error"
  message?: string | null
  items: Array<{
    id: number
    relation_type: "compound_component" | "compound_host"
    lemma: string
    english_translation?: string | null
    pos_tag?: string | null
    saved_match: {
      status: "unsaved" | "saved_lemma" | "saved_variation"
      target_lemma?: string | null
      target_meaning_id?: number | null
    }
    display_variant?: ReturnType<typeof buildVariant> | null
    candidate_variants?: Array<ReturnType<typeof buildVariant>>
  }>
}) {
  return {
    lemma: args.lemma ?? "legeplads",
    english_translation: args.englishTranslation ?? "playground",
    is_sectioned: true,
    meaning_sections: [
      {
        id: 1,
        meaning_key: args.meaningKey ?? "playground",
        gloss: args.meaningKey ?? "playground",
        english_translation: args.englishTranslation ?? "playground",
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        surface_forms: [],
      },
    ],
    related_words: {
      status: args.status,
      message: args.message,
      items: args.items,
    },
    surface_forms: [],
  }
}

describe("App wordbank related words", () => {
  it("renderer-only: renders the Composition section after meaning cards and polls queued related words until they are ready", async () => {
    let detailRequests = 0
    let releaseReadyResponse: (() => void) | null = null

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "legeplads", variation_count: 0 }],
      },
      lemmaDetailsHandler: async (input) => {
        if (!String(input).endsWith("/api/wordbank/lemmas/legeplads")) {
          throw new Error(`Unexpected lemma details request: ${String(input)}`)
        }
        detailRequests += 1
        if (detailRequests === 1) {
          return responseOf(buildOwnerDetails({
            status: "queued",
            message: "Finding related compound words.",
            items: [],
          }))
        }
        await new Promise<void>((resolve) => {
          releaseReadyResponse = resolve
        })
        return responseOf(buildOwnerDetails({
          status: "ready",
          items: [
            {
              id: 1,
              relation_type: "compound_component",
              lemma: "lege",
              english_translation: "to play",
              pos_tag: "VERB",
              saved_match: { status: "unsaved" },
              display_variant: buildVariant({
                corId: "COR.LEGE.LEM",
                lemma: "lege",
                gloss: "play",
                posTag: "VERB",
                morphology: "VerbForm=Inf|Voice=Act",
                gramRaw: "vb.inf.akt",
                lemmaIdx: 11,
              }),
              candidate_variants: [],
            },
          ],
        }))
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /legeplads/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    expect(screen.queryByRole("heading", { name: /^composition$/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/finding related compound words/i)).not.toBeInTheDocument()

    expect(releaseReadyResponse).not.toBeNull()
    ;(releaseReadyResponse as unknown as () => void)()

    await waitFor(() => {
      expect(detailRequests).toBeGreaterThanOrEqual(2)
      const relatedHeading = screen.getByRole("heading", { name: /^composition$/i })
      const header = document.getElementById("wordbank-lemma-header")
      expectToAppearBefore(meaningCard, relatedHeading)
      expect(header?.querySelector('[data-slot="separator"]')).toBeNull()
      expect(relatedHeading).toHaveClass("font-section-title", "text-xl", "tracking-normal")
      const compositionSection = relatedHeading.closest("section")
      expect(compositionSection?.querySelector(".danote-composition-shelf")).toBeNull()
      expect(compositionSection?.querySelector("[data-material='related']")).toHaveAttribute("data-paper-stock")
      expect(screen.getByText(/^at lege$/i)).toBeInTheDocument()
      expect(screen.getByText(/^Verb$/i)).toHaveClass("bg-material-grammar", "font-lexical", "rounded-sm")
      expect(screen.queryByText(/^Infinitive$/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/^Active$/i)).not.toBeInTheDocument()
    }, { timeout: 4_000 })
  }, 60_000)

  it("request-shape: unique related cards save through add-word and keep the current word page open", async () => {
    let relatedSaved = false
    let capturedBody: Record<string, unknown> | null = null

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "legeplads", variation_count: 0 }],
      },
      lemmaDetailsHandler: async (input) => {
        if (!String(input).endsWith("/api/wordbank/lemmas/legeplads")) {
          throw new Error(`Unexpected lemma details request: ${String(input)}`)
        }
        return responseOf(buildOwnerDetails({
          status: "ready",
          items: [
            {
              id: 1,
              relation_type: "compound_component",
              lemma: "lege",
              english_translation: "to play",
              pos_tag: "VERB",
              saved_match: relatedSaved
                ? { status: "saved_lemma", target_lemma: "lege", target_meaning_id: null }
                : { status: "unsaved" },
              display_variant: buildVariant({
                corId: "COR.LEGE.LEM",
                lemma: "lege",
                gloss: "play",
                posTag: "VERB",
                morphology: "VerbForm=Inf|Voice=Act",
                gramRaw: "vb.inf.akt",
                lemmaIdx: 11,
              }),
              candidate_variants: [],
            },
          ],
        }))
      },
      addWordHandler: async (_input, init) => {
        capturedBody = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>
        relatedSaved = true
        return responseOf({
          status: "inserted",
          stored_lemma: "lege",
          stored_surface_form: "lege",
          source: "manual",
          message: "Added 'lege' to wordbank.",
          queued_pronunciation_forms: [],
          queued_verification_targets: [],
          saved_snapshot: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /legeplads/i }))
    fireEvent.click(await screen.findByRole("button", { name: /add composition component lege/i }))

    await waitFor(() => {
      expect(capturedBody).toEqual({
        surface_token: "lege",
        lemma_candidate: "lege",
        cor_id: "COR.LEGE.LEM",
        pos_tag: "VERB",
        morphology: "VerbForm=Inf|Voice=Act",
        search_seed: {
          lemma: "lege",
          surface: "lege",
          cor_id: "COR.LEGE.LEM",
          cor_lemma_idx: 11,
          meaning_key: "play",
          gloss: "play",
          english_translation: "to play",
          pos_tag: "VERB",
          morphology: "VerbForm=Inf|Voice=Act",
          target_meaning_id: null,
        },
      })
    }, { timeout: 5_000 })

    expect(screen.getByRole("heading", { name: /^legeplads$/i })).toBeInTheDocument()
    const openButton = await screen.findByRole("button", { name: /open lege in wordbank/i }, { timeout: 5_000 })
    expect(openButton).toBeInTheDocument()
  })

  it("request-shape: ambiguous related cards expand inline and save the selected COR candidate", async () => {
    let capturedBody: Record<string, unknown> | null = null

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "legeplads", variation_count: 0 }],
      },
      lemmaDetailsResponse: buildOwnerDetails({
        status: "ready",
        items: [
          {
            id: 2,
            relation_type: "compound_component",
            lemma: "plads",
            english_translation: "space",
            pos_tag: "NOUN",
            saved_match: { status: "unsaved" },
            display_variant: null,
            candidate_variants: [
              buildVariant({
                corId: "COR.PLADS.SPACE.LEM",
                lemma: "plads",
                gloss: "space",
                posTag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                gramRaw: "sb.fk.sg.ubest",
                lemmaIdx: 12,
              }),
              buildVariant({
                corId: "COR.PLADS.SQUARE.LEM",
                lemma: "plads",
                gloss: "square",
                posTag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                gramRaw: "sb.fk.sg.ubest",
                lemmaIdx: 13,
              }),
            ],
          },
        ],
      }),
      addWordHandler: async (_input, init) => {
        capturedBody = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>
        return responseOf({
          status: "inserted",
          stored_lemma: "plads",
          stored_surface_form: "plads",
          source: "manual",
          message: "Added 'plads' to wordbank.",
          queued_pronunciation_forms: [],
          queued_verification_targets: [],
          saved_snapshot: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /legeplads/i }))
    fireEvent.click(await screen.findByRole("button", { name: /choose composition match for plads/i }))

    const squareButton = screen.getByText(/^square$/i).closest("button")
    expect(squareButton).not.toBeNull()
    fireEvent.click(squareButton as HTMLElement)

    await waitFor(() => {
      expect(capturedBody).toEqual({
        surface_token: "plads",
        lemma_candidate: "plads",
        cor_id: "COR.PLADS.SQUARE.LEM",
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        search_seed: {
          lemma: "plads",
          surface: "plads",
          cor_id: "COR.PLADS.SQUARE.LEM",
          cor_lemma_idx: 13,
          meaning_key: "square",
          gloss: "square",
          english_translation: "space",
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          target_meaning_id: null,
        },
      })
    })
  })

  it("renderer-only: eye actions open saved variation targets on the correct word page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "legefar", variation_count: 0 },
          { lemma: "fader", variation_count: 1 },
        ],
      },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (url.endsWith("/api/wordbank/lemmas/legefar")) {
          return responseOf(buildOwnerDetails({
            lemma: "legefar",
            englishTranslation: "playfather",
            meaningKey: "playfather",
            status: "ready",
            items: [
              {
                id: 3,
                relation_type: "compound_component",
                lemma: "far",
                english_translation: "father",
                pos_tag: "NOUN",
                saved_match: {
                  status: "saved_variation",
                  target_lemma: "fader",
                  target_meaning_id: 2,
                },
                display_variant: buildVariant({
                  corId: "COR.FAR.LEM",
                  lemma: "far",
                  gloss: "father",
                  posTag: "NOUN",
                  morphology: "Gender=Com|Number=Sing|Definite=Ind",
                  gramRaw: "sb.fk.sg.ubest",
                  lemmaIdx: 14,
                }),
                candidate_variants: [],
              },
            ],
          }))
        }
        if (url.endsWith("/api/wordbank/lemmas/fader")) {
          return responseOf({
            lemma: "fader",
            english_translation: "father",
            is_sectioned: true,
            meaning_sections: [
              {
                id: 2,
                meaning_key: "father",
                gloss: "father",
                english_translation: "father",
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                surface_forms: [{ form: "far", has_pronunciation: false }],
              },
            ],
            surface_forms: [],
          })
        }
        throw new Error(`Unexpected lemma details request: ${url}`)
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /legefar/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open far in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^fader$/i })).toBeInTheDocument()
    expect(screen.getByTestId("wordbank-meaning-card-2")).toBeInTheDocument()
  })

  it("renderer-only: compound_host reverse links are hidden — Composition only shows decomposition", async () => {
    // "Composition" is decomposition-only. compound_host links ("this lemma is a
    // constituent of these other saved compounds") are conceptually "related" /
    // "synonyms-adjacent" and are intentionally hidden until a real Related
    // surface exists. See the wordbank bug fix that renamed the section to
    // Composition.
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lege", variation_count: 0 }],
      },
      lemmaDetailsResponse: buildOwnerDetails({
        lemma: "lege",
        englishTranslation: null,
        meaningKey: "play",
        status: "ready",
        items: [
          {
            id: 9,
            relation_type: "compound_host",
            lemma: "legeplads",
            english_translation: "playground",
            pos_tag: "NOUN",
            saved_match: { status: "saved_lemma", target_lemma: "legeplads", target_meaning_id: null },
            display_variant: buildVariant({
              corId: "COR.LEGEPLADS.LEM",
              lemma: "legeplads",
              gloss: "playground",
              posTag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              gramRaw: "sb.fk.sg.ubest",
              lemmaIdx: 10,
            }),
            candidate_variants: [],
          },
        ],
      }),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /^lege$/i }))

    // The page must render (the heading below must exist), but with only a
    // compound_host item the Composition section has no decomposition rows.
    expect(await screen.findByRole("heading", { name: /^lege$/i })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /^composition$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open legeplads in wordbank/i })).not.toBeInTheDocument()
  })
})
