import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("command search uses local COR endpoint, renders grouped variants, and adds selected variant", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.110.01",
                form: "lærer",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
              {
                cor_id: "COR.49032.112.01",
                form: "lærere",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.30686.203.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.præs.akt",
                norm: "N",
                lemma_idx: 30686,
                gram_code: 203,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordResponse: {
        status: "inserted",
        stored_lemma: "lære",
        stored_surface_form: "lærer",
        source: "manual",
        message: "Added 'lære' to wordbank.",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    expect((await within(commandDialog).findAllByText(/teacher/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/learn/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Noun$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Verb$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^n-word$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Singular$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Present$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Indefinite$/i)).length).toBeGreaterThan(0)
    expect((await within(commandDialog).findAllByText(/^Active$/i)).length).toBeGreaterThan(0)
    const verbLemma = await within(commandDialog).findByText(/^at lære$/i, { selector: "em" })
    expect(verbLemma).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/\(to learn\)/i)).toBeInTheDocument()
    expect(screen.queryByText(/lære \(verb\)/i)).not.toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-add-icon")).length).toBeGreaterThan(0)
    expect(screen.queryByText(/english -> danish/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/danish -> english/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/add variation/i)).not.toBeInTheDocument()

    const verbVariant = verbLemma.closest("[cmdk-item]")
    expect(verbVariant).toBeTruthy()
    expect(verbVariant).toHaveTextContent(/from\s+at lære/i)
    fireEvent.click(verbVariant as HTMLElement)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes")) {
            return false
          }
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          surface_token?: string
          lemma_candidate?: string
          cor_id?: string
          pos_tag?: string
          morphology?: string
          search_seed?: {
            lemma?: string
            surface?: string
            cor_id?: string
            cor_lemma_idx?: number
            meaning_key?: string
            gloss?: string | null
            english_translation?: string | null
            pos_tag?: string | null
            morphology?: string | null
            target_meaning_id?: number | null
          }
        }
        return (
          body.surface_token === "lærer"
          && body.lemma_candidate === "lære"
          && body.cor_id === "COR.30686.203.01"
          && body.pos_tag === "VERB"
          && body.morphology === "Tense=Pres|VerbForm=Fin|Voice=Act"
          && body.search_seed?.lemma === "lære"
          && body.search_seed?.surface === "lærer"
          && body.search_seed?.cor_id === "COR.30686.203.01"
          && body.search_seed?.cor_lemma_idx === 30686
          && body.search_seed?.meaning_key === "learn"
          && body.search_seed?.gloss === "learn"
          && body.search_seed?.english_translation === "to learn"
          && body.search_seed?.pos_tag === "VERB"
          && body.search_seed?.morphology === "Tense=Pres|VerbForm=Fin|Voice=Act"
        )
      }),
    ).toBe(true)
  }, 10_000)

  expect(
      fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/resolve-query")),
    ).toBe(false)
    expect(
      fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/lexemes/verify")),
    ).toBe(false)
    expect(
      fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/lexemes/pronunciation")),
    ).toBe(false)
  })

  it("opening a newly added sectioned word keeps translation on the lemma and badges on the surface row only", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærere",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.112.01",
                form: "lærere",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordResponse: {
        status: "inserted",
        stored_lemma: "lærer",
        stored_surface_form: "lærere",
        source: "manual",
        message: "Added 'lærer' to wordbank.",
        meaning: {
          id: 1,
          meaning_key: "teacher",
          gloss: "teacher",
          english_translation: "teacher",
        },
      },
      lemmaDetailsResponse: {
        lemma: "lærer",
        english_translation: "teacher",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "teacher",
            gloss: "teacher",
            english_translation: "teacher",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            surface_forms: [
              {
                form: "lærere",
                english_translation: null,
                gloss: "teacher",
                gloss_translation: "teacher",
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                gram_raw: "sb.fk.pl.ubest",
                has_pronunciation: false,
              },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærere" } })

    fireEvent.click(await within(commandDialog).findByText(/^lærere$/i))

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    expect(screen.getByText(/^lærere$/i)).toBeInTheDocument()
    expect(screen.queryByTestId("wordbank-lemma-header-badges")).not.toBeInTheDocument()
    expect(screen.getAllByText(/^teacher$/i)).toHaveLength(1)
    expect(screen.getByText(/^Plural$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^No translation available\.$/i)).not.toBeInTheDocument()
  })

  it("command search debounces local COR requests and caches repeated queries", async () => {
    let corRequestCount = 0
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormHandler: async (input) => {
        corRequestCount += 1
        const url = new URL(String(input), "http://localhost")
        const form = (url.searchParams.get("form") ?? "").toLocaleLowerCase("da-DK")
        return responseOf({
          form,
          groups: [
            {
              lemma: form || "house",
              gloss: null,
              pos_tag: "NOUN",
              variants: [
                {
                  cor_id: `COR.${corRequestCount}.110.01`,
                  form: form || "house",
                  lemma: form || "house",
                  gram_raw: "sb.fk.sg.ubest",
                  norm: "N",
                  lemma_idx: corRequestCount,
                  gram_code: 110,
                  variation: 1,
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Sing|Definite=Ind",
                  features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                  extra_tags: [],
                },
              ],
            },
          ],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)

    fireEvent.change(searchInput, { target: { value: "h" } })
    fireEvent.change(searchInput, { target: { value: "ho" } })
    fireEvent.change(searchInput, { target: { value: "house" } })

    await waitFor(() => {
      expect(corRequestCount).toBe(2)
    })

    fireEvent.change(searchInput, { target: { value: "home" } })
    await waitFor(() => {
      expect(corRequestCount).toBe(4)
    })

    fireEvent.change(searchInput, { target: { value: "house" } })
    await waitFor(() => {
      expect(corRequestCount).toBe(4)
    })
  })

  it("opens the word page from saved snapshot before lemma details reload completes", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærere",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.112.01",
                form: "lærere",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordResponse: {
        status: "inserted",
        stored_lemma: "lærer",
        stored_surface_form: "lærere",
        source: "manual",
        message: "Added 'lærer' to wordbank.",
        meaning: {
          id: 1,
          meaning_key: "teacher",
          gloss: "teacher",
          english_translation: "teacher",
        },
        saved_snapshot: {
          lemma: "lærer",
          english_translation: "teacher",
          is_sectioned: true,
          meaning_sections: [
            {
              id: 1,
              meaning_key: "teacher",
              gloss: "teacher",
              english_translation: "teacher",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              surface_forms: [
                {
                  form: "lærere",
                  gloss: "teacher",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  has_pronunciation: false,
                },
              ],
            },
          ],
          surface_forms: [],
        },
      },
      lemmaDetailsHandler: async () => {
        await new Promise((resolve) => window.setTimeout(resolve, 300))
        return responseOf({
          lemma: "lærer",
          english_translation: "teacher",
          is_sectioned: true,
          meaning_sections: [
            {
              id: 1,
              meaning_key: "teacher",
              gloss: "teacher",
              english_translation: "teacher",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              surface_forms: [
                {
                  form: "lærere",
                  gloss: "teacher",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  has_pronunciation: false,
                },
              ],
            },
          ],
          surface_forms: [],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærere" } })

    fireEvent.click(await within(commandDialog).findByText(/^lærere$/i))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    expect(screen.getByText(/^lærere$/i)).toBeInTheDocument()
  })

  it("auto-updates the word page when sidebar-search verification finishes in the background", async () => {
    let lemmaDetailsRequestCount = 0
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærere",
        groups: [
          {
            lemma: "lærer",
            gloss: "teacher",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.49032.112.01",
                form: "lærere",
                lemma: "lærer",
                gloss: "teacher",
                lemma_translation: "teacher",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 49032,
                gram_code: 112,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
      addWordResponse: {
        status: "inserted",
        stored_lemma: "lærer",
        stored_surface_form: "lærere",
        source: "manual",
        message: "Added 'lærer' to wordbank.",
        meaning: {
          id: 1,
          meaning_key: "teacher",
          gloss: "teacher",
          english_translation: "teacher",
        },
        saved_snapshot: {
          lemma: "lærer",
          english_translation: "teacher",
          is_sectioned: true,
          meaning_sections: [
            {
              id: 1,
              meaning_key: "teacher",
              gloss: "teacher",
              english_translation: "teacher",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              verification: {
                status: "queued",
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                message: "Word verification queued.",
                composed_word_count: null,
                stored_surface_form: "lærere",
                requested_at: "2026-03-13T12:00:00.000Z",
                suggested_actions: [],
              },
              surface_forms: [
                {
                  form: "lærere",
                  gloss: "teacher",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  has_pronunciation: false,
                },
              ],
            },
          ],
          surface_forms: [],
        },
      },
      lemmaDetailsHandler: async () => {
        lemmaDetailsRequestCount += 1
        if (lemmaDetailsRequestCount === 1) {
          return responseOf({
            lemma: "lærer",
            english_translation: "teacher",
            is_sectioned: true,
            meaning_sections: [
              {
                id: 1,
                meaning_key: "teacher",
                gloss: "teacher",
                english_translation: "teacher",
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                verification: {
                  status: "queued",
                  provider: "gemini",
                  reviewer_role: "Professional Danish Language Expert",
                  message: "Word verification queued.",
                  composed_word_count: null,
                  stored_surface_form: "lærere",
                  requested_at: "2026-03-13T12:00:00.000Z",
                  suggested_actions: [],
                },
                surface_forms: [
                  {
                    form: "lærere",
                    gloss: "teacher",
                    pos_tag: "NOUN",
                    morphology: "Gender=Com|Number=Plur|Definite=Ind",
                    has_pronunciation: false,
                  },
                ],
              },
            ],
            surface_forms: [],
          })
        }
        return responseOf({
          lemma: "lærer",
          english_translation: "teacher",
          is_sectioned: true,
          meaning_sections: [
            {
              id: 1,
              meaning_key: "teacher",
              gloss: "teacher",
              english_translation: "teacher",
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
              verification: {
                status: "verified",
                provider: "gemini",
                reviewer_role: "Professional Danish Language Expert",
                message: "Verification passed.",
                composed_word_count: null,
                stored_surface_form: "lærere",
                requested_at: "2026-03-13T12:00:00.000Z",
                completed_at: "2026-03-13T12:00:03.000Z",
                suggested_actions: [],
              },
              surface_forms: [
                {
                  form: "lærere",
                  gloss: "teacher",
                  pos_tag: "NOUN",
                  morphology: "Gender=Com|Number=Plur|Definite=Ind",
                  has_pronunciation: false,
                },
              ],
            },
          ],
          surface_forms: [],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærere" } })
    fireEvent.click(await within(commandDialog).findByText(/^lærere$/i))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/gemini verification queued/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByLabelText(/gemini verification passed/i)).toBeInTheDocument()
      expect(screen.queryByLabelText(/gemini verification queued/i)).not.toBeInTheDocument()
    }, { timeout: 6_000 })
  }, 15_000)
})
