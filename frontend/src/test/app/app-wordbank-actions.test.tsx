import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, vi, waitFor, within } from "@/test/app-test-helpers"
import {
  bogVariationGlossWordPageContractFixture,
  cloneContractFixture,
  teacherSectionedWordPageContractFixture,
} from "@/test/app/wordbank-contract-fixtures"

describe("App wordbank", () => {
  it("contract-backed: noun word pages prefer the paradigm table once a saved slot exists", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    const table = screen.getByRole("table")
    expect(within(table).getByText(/^singular$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^definite$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^bogen$/i)).toBeInTheDocument()
    expect(screen.queryByText(/\(book, til læsning\)/i)).not.toBeInTheDocument()
  }, 10_000)

  it("renderer-only: does not render an empty-variation message when there are no saved variations", async () => {
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

  it("renderer-only: defers loading the full wordbank list until the wordbank section opens", async () => {
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

  it("request-shape: regenerates pronunciation from the lemma word context menu", async () => {
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

    const listenButton = await screen.findByRole("button", { name: /^listen to bog$/i })
    const verificationButton = screen.getByRole("button", { name: /show verification details/i })
    fireEvent.click(verificationButton)

    expect(await screen.findByText(/no verification records yet/i)).toBeInTheDocument()
    expect(screen.getByText(/waiting to run/i)).toBeInTheDocument()

    fireEvent.contextMenu(listenButton)
    fireEvent.click(await screen.findByRole("menuitem", { name: /regenerate audio/i }))

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

  it("request-shape: non-sectioned lemma word context menu keeps the root rethink action", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
      rethinkCategoriesHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          stored_lemma?: string
          stored_surface_form?: string | null
          meaning_id?: number | null
        }
        if (body.stored_lemma !== "bog" || body.stored_surface_form !== null || body.meaning_id !== null) {
          throw new Error("Unexpected rethink-categories payload.")
        }
        return responseOf({
          status: "updated",
          stored_lemma: "bog",
          stored_surface_form: null,
          meaning_id: null,
          applied_categories: ["Food", "Household Objects"],
          message: "Updated categories for 'bog'.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const listenButton = await screen.findByRole("button", { name: /^listen to bog$/i })
    fireEvent.contextMenu(listenButton)

    expect(await screen.findByRole("menuitem", { name: /regenerate audio/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("menuitem", { name: /rethink categories/i }))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes/rethink-categories")) {
            return false
          }
          return String(init?.body ?? "") === JSON.stringify({
            stored_lemma: "bog",
            stored_surface_form: null,
            meaning_id: null,
          })
        }),
      ).toBe(true)
    })
  })

  it("renderer-only: shows verification progress in the unified popover while Gemini is still processing", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "kat", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "kat",
        english_translation: "cat",
        verification: {
          status: "queued",
          provider: "gemini",
          reviewer_role: "Professional Danish Language Expert",
          message: "Verification queued.",
          composed_word_count: null,
          stored_surface_form: "kat",
          requested_at: "2026-03-13T12:00:00.000Z",
          suggested_actions: [],
        },
        surface_forms: [{ form: "kat", has_pronunciation: true }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /kat/i }))

    const verificationButton = await screen.findByRole("button", { name: /verification is running/i })
    fireEvent.click(verificationButton)

    expect(await screen.findByText("Verification")).toBeInTheDocument()
    expect(screen.getByText(/gemini is verifying this word page/i)).toBeInTheDocument()
    expect(screen.getByText(/1 running/i)).toBeInTheDocument()
    expect(screen.getByText(/requested/i)).toBeInTheDocument()
    expect(screen.getByText("Verification").closest("[data-slot='popover-content']")).toHaveClass(
      "h-[32rem]",
      "overflow-y-auto",
    )
  })

  it("renderer-only: keeps the lemma pronunciation action playable when the only saved form is hidden from details", async () => {
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

  it("request-shape: regenerates pronunciation for a specific meaning-row word from its context menu", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            surface_forms: [{ form: "bogen", has_pronunciation: true }],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const listenButton = await screen.findByRole("button", { name: /listen to bogen/i })
    fireEvent.contextMenu(listenButton)
    fireEvent.click(await screen.findByRole("menuitem", { name: /regenerate audio/i }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/lexemes/pronunciation"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            stored_lemma: "bog",
            stored_surface_form: "bogen",
            force: true,
          }),
        }),
      )
    })
  })

  it("request-shape: right-clicking a meaning card rethinks categories and refreshes the badges", async () => {
    let lemmaDetails = cloneContractFixture(teacherSectionedWordPageContractFixture)
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsHandler: async () => responseOf(lemmaDetails),
      rethinkCategoriesHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          stored_lemma?: string
          stored_surface_form?: string | null
          meaning_id?: number | null
        }
        if (body.stored_lemma !== "lærer" || body.stored_surface_form !== null || body.meaning_id !== 1) {
          throw new Error("Unexpected rethink-categories payload.")
        }
        lemmaDetails = {
          ...lemmaDetails,
          meaning_sections: [
            {
              ...lemmaDetails.meaning_sections![0],
              categories: ["People", "School", "Work", "Education", "Culture", "Community"],
            },
          ],
        }
        return responseOf({
          status: "updated",
          stored_lemma: "lærer",
          stored_surface_form: null,
          meaning_id: 1,
          applied_categories: ["People", "School", "Work", "Education", "Culture", "Community"],
          message: "Updated categories for 'lærer'.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    fireEvent.contextMenu(meaningCard)
    fireEvent.click(await screen.findByRole("menuitem", { name: /rethink categories/i }))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes/rethink-categories")) {
            return false
          }
          return String(init?.body ?? "") === JSON.stringify({
            stored_lemma: "lærer",
            stored_surface_form: null,
            meaning_id: 1,
          })
        }),
      ).toBe(true)
    })

    await waitFor(() => {
      expect(screen.getByTestId("wordbank-meaning-category-badges-1")).toHaveTextContent("Community")
    })
  })

  it("request-shape: noun meaning cards can complete variations and refresh to show only non-lemma variations", async () => {
    let lemmaDetails = {
      lemma: "bog",
      english_translation: null,
      is_sectioned: true,
      meaning_sections: [
        {
          id: 1,
          meaning_key: "book",
          gloss: "book",
          english_translation: "book",
          verification: {
            status: "verified",
            provider: "gemini",
            reviewer_role: "Professional Danish Language Expert",
            message: "Verified.",
            requested_at: "2026-03-15T10:00:00Z",
            completed_at: "2026-03-15T10:00:05Z",
          },
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          surface_forms: [
            {
              form: "bøger",
              verification: {
                status: "verified",
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                message: "Verified.",
                requested_at: "2026-03-15T10:00:00Z",
                completed_at: "2026-03-15T10:00:05Z",
              },
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Plur|Definite=Ind",
              has_pronunciation: false,
            },
          ],
        },
      ],
      surface_forms: [],
    }
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsHandler: async () => responseOf(lemmaDetails),
      completeVariationsHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          stored_lemma?: string
          meaning_id?: number
        }
        if (body.stored_lemma !== "bog" || body.meaning_id !== 1) {
          throw new Error("Unexpected complete-variations payload.")
        }
        lemmaDetails = {
          ...lemmaDetails,
          meaning_sections: [
            {
              ...lemmaDetails.meaning_sections[0],
              surface_forms: [
                {
                  form: "bogen",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Sing|Definite=Def",
                  has_pronunciation: false,
                },
                {
                  form: "bøger",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  has_pronunciation: false,
                },
                {
                  form: "bøgerne",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Def",
                  has_pronunciation: false,
                },
              ],
            },
          ],
          surface_forms: [
            {
              form: "bog",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              has_pronunciation: false,
            },
          ],
        }
        return responseOf({
          status: "updated",
          stored_lemma: "bog",
          meaning_id: 1,
          added_surface_forms: ["bogen", "bøgerne"],
          queued_pronunciation_forms: ["bogen", "bøgerne"],
          queued_verification_targets: [{ meaning_id: 1, stored_surface_form: null }],
          message: "Completed noun variations for 'bog'.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    fireEvent.contextMenu(meaningCard)
    fireEvent.click(await screen.findByRole("menuitem", { name: /complete variations/i }))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes/complete-variations")) {
            return false
          }
          return String(init?.body ?? "") === JSON.stringify({
            stored_lemma: "bog",
            meaning_id: 1,
          })
        }),
      ).toBe(true)
    })

    await waitFor(() => {
      expect(screen.getByText(/^bøgerne$/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/^bogen$/i)).toBeInTheDocument()
    expect(screen.getByText(/^bøger$/i)).toBeInTheDocument()
  })

  it("request-shape: adjective meaning cards can complete variations and render the agreement table with shared plural cells", async () => {
    let lemmaDetails = {
      lemma: "stor",
      english_translation: null,
      is_sectioned: true,
      meaning_sections: [
        {
          id: 1,
          meaning_key: "large",
          gloss: "large",
          english_translation: "large",
          verification: {
            status: "verified",
            provider: "gemini",
            reviewer_role: "Professional Danish Language Expert",
            message: "Verified.",
            requested_at: "2026-03-15T10:00:00Z",
            completed_at: "2026-03-15T10:00:05Z",
          },
          pos_tag: "ADJ",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          gram_raw: "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl",
          surface_forms: [
            {
              form: "stort",
              verification: {
                status: "verified",
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                message: "Verified.",
                requested_at: "2026-03-15T10:00:00Z",
                completed_at: "2026-03-15T10:00:05Z",
              },
              pos_tag: "ADJ",
              morphology: "Gender=Neut|Number=Sing|Definite=Ind",
              has_pronunciation: false,
            },
          ],
        },
      ],
      surface_forms: [
        {
          form: "stor",
          pos_tag: "ADJ",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          gram_raw: "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl",
          has_pronunciation: false,
        },
      ],
    }
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "stor", variation_count: 1 }],
      },
      lemmaDetailsHandler: async () => responseOf(lemmaDetails),
      completeVariationsHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          stored_lemma?: string
          meaning_id?: number
        }
        if (body.stored_lemma !== "stor" || body.meaning_id !== 1) {
          throw new Error("Unexpected complete-variations payload.")
        }
        lemmaDetails = {
          ...lemmaDetails,
          meaning_sections: [
            {
              ...lemmaDetails.meaning_sections[0],
              surface_forms: [
                {
                  form: "store",
                  pos_tag: "ADJ",
                  morphology: "Number=Sing|Definite=Def",
                  gram_raw: "adj.sg.best | adj.pl",
                  has_pronunciation: false,
                },
                {
                  form: "stort",
                  pos_tag: "ADJ",
                  morphology: "Gender=Neut|Number=Sing|Definite=Ind",
                  has_pronunciation: false,
                },
              ],
            },
          ],
        }
        return responseOf({
          status: "updated",
          stored_lemma: "stor",
          meaning_id: 1,
          added_surface_forms: ["store"],
          queued_pronunciation_forms: ["store"],
          queued_verification_targets: [{ meaning_id: 1, stored_surface_form: null }],
          message: "Completed adjective variations for 'stor'.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /stor/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    fireEvent.contextMenu(meaningCard)
    fireEvent.click(await screen.findByRole("menuitem", { name: /complete variations/i }))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes/complete-variations")) {
            return false
          }
          return String(init?.body ?? "") === JSON.stringify({
            stored_lemma: "stor",
            meaning_id: 1,
          })
        }),
      ).toBe(true)
    })

    await screen.findByText(/^n-word:$/i)
    expect(screen.getAllByText(/^t-word:$/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/^store$/i).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/^stort$/i)).toBeInTheDocument()
  })

  it("renderer-only: non-paradigm meaning cards do not expose complete variations in the context menu", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lære", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "lære",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "learn",
            gloss: "learn",
            english_translation: "learn",
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
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lære/i }))

    fireEvent.contextMenu(await screen.findByTestId("wordbank-meaning-card-1"))
    expect(await screen.findByRole("menuitem", { name: /rethink categories/i })).toBeInTheDocument()
    expect(screen.queryByRole("menuitem", { name: /complete variations/i })).not.toBeInTheDocument()
  })

  it("request-shape: completion review shows one fix-variations apply button for the meaning", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "mor", variation_count: 3 }],
      },
      lemmaDetailsResponse: {
        lemma: "mor",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "person",
            gloss: "person",
            english_translation: "mother",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            verification: {
              status: "flagged",
              provider: "gemini",
              reviewer_role: "Professional Danish Language Expert",
              message: "Review needed.",
              composed_word_count: 1,
              stored_surface_form: null,
              requested_at: "2026-03-15T10:55:00.000Z",
              completed_at: "2026-03-15T10:57:00.000Z",
              problem: "The plural surface forms provided for the noun 'mor' are incorrect.",
              change_to_implement: "Replace the completed variation set with the correct plural forms.",
              suggested_actions: [
                {
                  action_type: "fix_variations",
                  reason: "Replace the saved variation set with the reviewed noun forms for this meaning.",
                  singular_indefinite_forms: ["mor"],
                  singular_definite_forms: ["moren"],
                  plural_indefinite_forms: ["mødre"],
                  plural_definite_forms: ["mødrene"],
                },
              ],
            },
            surface_forms: [
              { form: "morer", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Ind", has_pronunciation: false },
              { form: "morerne", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Def", has_pronunciation: false },
            ],
          },
        ],
        surface_forms: [{ form: "mor", has_pronunciation: false }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /mor/i }))
    fireEvent.click(await screen.findByRole("button", { name: /show verification review details/i }))

    expect(await screen.findByText(/fix variations/i)).toBeInTheDocument()
    expect(screen.getAllByText(/replace the saved variation set with the reviewed noun forms/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/singular indefinite: mor\./i)).toBeInTheDocument()
    expect(screen.getByText(/plural indefinite: mødre\./i)).toBeInTheDocument()

    const applyButton = screen.getByRole("button", { name: /apply change/i })
    fireEvent.click(applyButton)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/lexemes/apply-verification-changes"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            stored_lemma: "mor",
            stored_surface_form: null,
            meaning_id: 1,
            action: {
              action_type: "fix_variations",
              reason: "Replace the saved variation set with the reviewed noun forms for this meaning.",
              singular_indefinite_forms: ["mor"],
              singular_definite_forms: ["moren"],
              plural_indefinite_forms: ["mødre"],
              plural_definite_forms: ["mødrene"],
            },
            provider: "gemini",
          }),
        }),
      )
    })
  }, 15_000)

  it("request-shape: shows verification error info on the word page and in notifications", async () => {
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
        verification: {
          status: "error",
          provider: "gemini",
          reviewer_role: "Professional Danish Language Expert",
          message: "Verification task failed: Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY.",
          composed_word_count: null,
          stored_surface_form: "kat",
          requested_at: "2026-03-13T12:00:00.000Z",
          completed_at: "2026-03-13T12:00:02.000Z",
          problem: "Stored POS and translation are inconsistent for this entry.",
          change_to_implement: "Update POS to NOUN and translation to 'cat'.",
          suggested_actions: [
            {
              action_type: "fix_translation",
              english_translation: "cat",
              reason: "The translation should be cat.",
            },
          ],
        },
        surface_forms: [{ form: "kat", has_pronunciation: true }],
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

    const notificationsButton = await screen.findByRole(
      "button",
      { name: /show notifications \(1 unread\)/i },
      { timeout: 5_000 },
    )
    fireEvent.click(notificationsButton)
    const notificationList = await screen.findByLabelText("notification-list")
    expect(notificationList).toHaveTextContent("Review needed for 'kat'.")
    expect(screen.getByRole("button", { name: /wordbank/i })).toHaveTextContent("1")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /kat/i }))
    expect(screen.getAllByRole("button", { name: /wordbank/i })[0]).toHaveTextContent("1")
    const infoButton = await screen.findByRole("button", { name: /show verification review details/i })
    expect(infoButton).toBeEnabled()
    fireEvent.click(infoButton)

    expect(await screen.findByText("Verification")).toBeInTheDocument()
    expect(screen.getByText(/verification needs review/i)).toBeInTheDocument()
    expect(screen.getByText("Problem")).toBeInTheDocument()
    expect(screen.getByText("Change to implement")).toBeInTheDocument()
    expect(screen.getByText(/stored pos and translation are inconsistent/i)).toBeInTheDocument()
    expect(screen.getByText(/update pos to noun and translation to 'cat'/i)).toBeInTheDocument()
    expect(screen.getByText(/apply changes/i)).toBeInTheDocument()
    expect(screen.getByText(/fix translation/i)).toBeInTheDocument()
    expect(screen.getByText(/set translation to 'cat'/i)).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: /wordbank/i })[0]).not.toHaveTextContent("1")

    const applyButton = screen.getByRole("button", { name: /apply change/i })
    expect(applyButton).toBeEnabled()
    fireEvent.click(applyButton)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/wordbank/lexemes/apply-verification-changes"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            stored_lemma: "kat",
            stored_surface_form: null,
            meaning_id: null,
            action: {
              action_type: "fix_translation",
              english_translation: "cat",
              reason: "The translation should be cat.",
            },
            provider: "gemini",
          }),
        }),
      )
    })
  }, 15_000)

  it("starts Gemini verification after save, shows the spinner, and marks the word as verified after success", async () => {
    let verificationComplete = false

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
      lemmasResponse: {
        items: [{ lemma: "kat", variation_count: 1 }],
      },
      lemmaDetailsHandler: () => Promise.resolve(responseOf({
        lemma: "kat",
        english_translation: "cat",
        verification: verificationComplete
          ? {
              status: "verified" as const,
              provider: "gemini",
              reviewer_role: "Professional Danish Language Expert",
              message: "Verification passed.",
              composed_word_count: null,
              stored_surface_form: "kat",
              requested_at: "2026-03-13T12:00:00.000Z",
              completed_at: "2026-03-13T12:00:03.000Z",
              suggested_actions: [],
            }
          : {
              status: "queued" as const,
              provider: "gemini",
              reviewer_role: "Professional Danish Language Expert",
              message: "Verification queued.",
              composed_word_count: null,
              stored_surface_form: "kat",
              requested_at: "2026-03-13T12:00:00.000Z",
              suggested_actions: [],
            },
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Number=Sing",
        surface_forms: [{ form: "kat", has_pronunciation: true }],
      })),
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

    await screen.findByRole("button", { name: /word verification is running/i })

    verificationComplete = true

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /word verification is running/i }),
      ).not.toBeInTheDocument()
      expect(
        screen.getByRole("button", { name: /show notifications \(1 unread\)/i }),
      ).toBeEnabled()
    }, { timeout: 4_000 })

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /kat/i }))
    const verificationButton = await screen.findByRole("button", { name: /show verification details/i })
    fireEvent.click(verificationButton)

    expect(await screen.findByText("Verification")).toBeInTheDocument()
    expect(screen.getByText(/verification completed/i)).toBeInTheDocument()
    expect(screen.getAllByText(/1 verified/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/verification passed\./i)).toBeInTheDocument()
  }, 15_000)

  it("keeps one current-state notification per target for complete-variations reviews even after leaving the lemma page", async () => {
    vi.useRealTimers()
    let completionSettled = false
    let lemmaDetails = {
      lemma: "bog",
      english_translation: null,
      is_sectioned: true,
      meaning_sections: [
        {
          id: 1,
          meaning_key: "book",
          gloss: "book",
          english_translation: "book",
          verification: {
            status: "verified" as const,
            provider: "gemini",
            reviewer_role: "Professional Danish Language Expert",
            message: "Verified.",
            requested_at: "2026-03-15T10:00:00Z",
            completed_at: "2026-03-15T10:00:05Z",
          },
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          surface_forms: [
            {
              form: "bøger",
              verification: {
                status: "verified" as const,
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                message: "Verified.",
                requested_at: "2026-03-15T10:00:00Z",
                completed_at: "2026-03-15T10:00:05Z",
              },
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Plur|Definite=Ind",
              has_pronunciation: false,
            },
          ],
        },
      ],
      surface_forms: [],
    }

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsHandler: async () => responseOf(
        completionSettled
          ? {
              ...lemmaDetails,
              meaning_sections: [
                {
                  ...lemmaDetails.meaning_sections[0],
                  verification: {
                    status: "error" as const,
                    provider: "gemini",
                    reviewer_role: "Professional Danish Language Expert",
                    review_intent: "complete_variations",
                    message: "Review needed.",
                    requested_at: "2026-03-15T10:00:00Z",
                    completed_at: "2026-03-15T10:00:05Z",
                    problem: "Completed variations are incorrect.",
                    change_to_implement: "Replace the saved variation set with the reviewed noun forms.",
                    suggested_actions: [{ action_type: "fix_variations", reason: "Replace the saved variation set." }],
                  },
                },
              ],
            }
          : lemmaDetails,
      ),
      completeVariationsHandler: async () => {
        lemmaDetails = {
          ...lemmaDetails,
          meaning_sections: [
            {
              ...lemmaDetails.meaning_sections[0],
              verification: {
                status: "queued" as const,
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                review_intent: "complete_variations",
                message: "Word verification queued.",
                requested_at: "2026-03-15T10:00:00Z",
                suggested_actions: [],
              },
            },
          ],
        }
        return responseOf({
          status: "updated",
          stored_lemma: "bog",
          meaning_id: 1,
          added_surface_forms: ["bogen", "bøgerne"],
          queued_pronunciation_forms: ["bogen", "bøgerne"],
          queued_verification_targets: [{ meaning_id: 1, stored_surface_form: null }],
          message: "Completed noun variations for 'bog'.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    fireEvent.contextMenu(meaningCard)
    fireEvent.click(await screen.findByRole("menuitem", { name: /complete variations/i }))

    fireEvent.click(screen.getByRole("button", { name: /playground/i }))

    completionSettled = true

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /show notifications \(1 unread\)/i })).toBeEnabled()
    }, { timeout: 5_000 })

    fireEvent.click(screen.getByRole("button", { name: /show notifications \(1 unread\)/i }))
    const notificationList = await screen.findByLabelText("notification-list")
    expect(notificationList).toHaveTextContent("Review needed for 'book'.")
    expect(notificationList.querySelectorAll("li")).toHaveLength(1)
  }, 15_000)

  it("renderer-only: adjective completion review summarizes n-word and t-word slots", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "stor", variation_count: 2 }],
      },
      lemmaDetailsResponse: {
        lemma: "stor",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "large",
            gloss: "large",
            english_translation: "large",
            pos_tag: "ADJ",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            verification: {
              status: "flagged",
              provider: "gemini",
              reviewer_role: "Professional Danish Language Expert",
              message: "Review needed.",
              composed_word_count: 1,
              stored_surface_form: null,
              requested_at: "2026-03-15T10:55:00.000Z",
              completed_at: "2026-03-15T10:57:00.000Z",
              problem: "The adjective agreement set is incomplete.",
              change_to_implement: "Replace the completed variation set with the reviewed adjective forms.",
              suggested_actions: [
                {
                  action_type: "fix_variations",
                  reason: "Replace the saved variation set with the reviewed adjective forms for this meaning.",
                  singular_indefinite_n_word_forms: ["stor"],
                  singular_indefinite_t_word_forms: ["stort"],
                  singular_definite_forms: ["store"],
                  plural_indefinite_forms: ["store"],
                  plural_definite_forms: ["store"],
                },
              ],
            },
            surface_forms: [
              { form: "stort", pos_tag: "ADJ", morphology: "Gender=Neut|Number=Sing|Definite=Ind", has_pronunciation: false },
              { form: "store", pos_tag: "ADJ", morphology: "Number=Sing|Definite=Def", gram_raw: "adj.sg.best | adj.pl", has_pronunciation: false },
            ],
          },
        ],
        surface_forms: [{ form: "stor", pos_tag: "ADJ", morphology: "Gender=Com|Number=Sing|Definite=Ind", has_pronunciation: false }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /stor/i }))
    fireEvent.click(await screen.findByRole("button", { name: /show verification review details/i }))

    expect(await screen.findByText(/singular indefinite n-word: stor\./i)).toBeInTheDocument()
    expect(screen.getByText(/singular indefinite t-word: stort\./i)).toBeInTheDocument()
    expect(screen.getByText(/plural indefinite: store\./i)).toBeInTheDocument()
    expect(screen.getByText(/plural definite: store\./i)).toBeInTheDocument()
  })
})
