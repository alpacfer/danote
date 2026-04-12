import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"
import {
  cloneContractFixture,
  morHomographWordPageContractFixture,
  teacherQueuedSearchAddResponseContractFixture,
  teacherQueuedWordPageContractFixture,
  teacherSectionedWordPageContractFixture,
  teacherVerifiedWordPageContractFixture,
} from "@/test/app/wordbank-contract-fixtures"

describe("App shell and search", () => {
  it("request-shape: command search uses local COR endpoint, renders grouped variants, and adds selected variant", async () => {
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
    }, { timeout: 10_000 })

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

  it("request-shape: multi-word search switches to sentence mode, hides other groups, and saving refreshes both sentencebank and wordbank", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentencebankResponse: { items: [] },
      phraseTranslationResponse: {
        status: "generated",
        source_text: "jeg elsker dansk",
        english_translation: "i love danish",
      },
      verifySentenceResponse: {
        is_valid: true,
        errors: [],
        corrected_text: null,
        language: "da",
      },
      addSentenceResponse: {
        status: "inserted",
        id: 99,
        source_text: "jeg elsker dansk",
        english_translation: "i love danish",
        created_at: "2026-04-11T10:00:00.000Z",
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
        message: 'Added "jeg elsker dansk" to sentencebank.',
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const initialSentencebankGetCount = fetchSpy.mock.calls.filter(
      ([input, init]) => String(input).endsWith("/api/sentencebank/sentences") && !init?.method,
    ).length
    const initialWordbankGetCount = fetchSpy.mock.calls.filter(
      ([input, init]) => String(input).endsWith("/api/wordbank/lemmas") && !init?.method,
    ).length

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "jeg elsker dansk" } })

    expect(await within(commandDialog).findByText(/^jeg elsker dansk$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^i love danish$/i)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^Sentence$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Wordbank$/i)).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Notes$/i)).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Pages$/i)).not.toBeInTheDocument()

    const sentenceOption = await within(commandDialog).findByRole("option")
    await waitFor(() => {
      expect(sentenceOption).not.toHaveAttribute("aria-disabled", "true")
    })
    fireEvent.click(sentenceOption)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) =>
          String(input).endsWith("/api/wordbank/phrase-translation") && init?.method === "POST"),
      ).toBe(true)
      expect(
        fetchSpy.mock.calls.some(([input, init]) =>
          String(input).endsWith("/api/sentencebank/sentences") && init?.method === "POST"),
      ).toBe(true)
      expect(fetchSpy.mock.calls.filter(
        ([input, init]) => String(input).endsWith("/api/sentencebank/sentences") && !init?.method,
      ).length).toBeGreaterThan(initialSentencebankGetCount)
      expect(fetchSpy.mock.calls.filter(
        ([input, init]) => String(input).endsWith("/api/wordbank/lemmas") && !init?.method,
      ).length).toBeGreaterThan(initialWordbankGetCount)
    })

    expect(
      fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/resolve-query")),
    ).toBe(false)
    expect(
      fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/search/cor-form?")),
    ).toBe(false)
  })

  it("renderer-only: opening a newly added sectioned word keeps translation on the lemma and badges on the surface row only", async () => {
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
      lemmaDetailsResponse: cloneContractFixture(teacherSectionedWordPageContractFixture),
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
    const meaningCard = screen.getByTestId("wordbank-meaning-card-1")
    expect(screen.getByText(/^lærere$/i)).toBeInTheDocument()
    expect(screen.queryByTestId("wordbank-lemma-header-badges")).not.toBeInTheDocument()
    expect(screen.getAllByText(/^teacher$/i)).toHaveLength(1)
    expect(screen.getByText(/^Plural$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^No translation available\.$/i)).not.toBeInTheDocument()
    expect(meaningCard).toHaveAttribute("data-selected", "true")
    expect(meaningCard).not.toHaveClass("ring-2")
    expect(meaningCard).not.toHaveClass("border-primary/50")
  })

  it("request-shape: COR search save keeps lemma translation separate from gloss translation end to end", async () => {
    const savedSearchResponse = {
      items: [] as Array<{
        lemma: string
        display_lemma: string
        meaning_id: number
        meaning_key: string
        gloss: string | null
        gloss_translation: string | null
        cor_lemma_idx: number
        variation_count: number
        english_translation: string | null
        match_surface: string | null
        query_cor_ids: string[]
        pos_tag: string | null
        morphology: string | null
      }>,
    }
    let hasSavedMorMeaning = false
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: savedSearchResponse,
      corSearchFormResponse: {
        form: "mor",
        groups: [
          {
            lemma: "mor",
            gloss: "jordlag",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.MOR.SOIL.01",
                form: "mor",
                lemma: "mor",
                gloss: "jordlag",
                gloss_translation: "soil layer",
                lemma_translation: "mother",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 51047,
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
      },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = (url.searchParams.get("form") ?? "").trim().toLocaleLowerCase("da-DK")
        if (form !== "mor" || hasSavedMorMeaning) {
          return responseOf({ form, groups: [] })
        }
        return responseOf({
          form: "mor",
          groups: [
            {
              lemma: "mor",
              gloss: "jordlag",
              pos_tag: "NOUN",
              variants: [
                {
                  cor_id: "COR.MOR.SOIL.01",
                  form: "mor",
                  lemma: "mor",
                  gloss: "jordlag",
                  gloss_translation: "soil layer",
                  lemma_translation: "mother",
                  gram_raw: "sb.fk.sg.ubest",
                  norm: "N",
                  lemma_idx: 51047,
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
      addWordHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          search_seed?: {
            gloss?: string | null
            english_translation?: string | null
          }
        }
        if (body.search_seed?.gloss === "jordlag" && body.search_seed?.english_translation === "mother") {
          hasSavedMorMeaning = true
          savedSearchResponse.items = [
            {
              lemma: "mor",
              display_lemma: "mor",
              meaning_id: 2,
              meaning_key: "soil-layer",
              gloss: "jordlag",
              gloss_translation: "soil layer",
              cor_lemma_idx: 51047,
              variation_count: 1,
              english_translation: "mother",
              match_surface: null,
              query_cor_ids: ["COR.MOR.SOIL.01"],
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Sing|Definite=Ind",
            },
          ]
        }
        return responseOf({
          status: "inserted",
          stored_lemma: "mor",
          stored_surface_form: "mor",
          source: "manual",
          message: "Added 'mor' to wordbank.",
          meaning: {
            id: 2,
            meaning_key: "soil-layer",
            gloss: "jordlag",
            english_translation: "mother",
          },
          saved_snapshot: cloneContractFixture(morHomographWordPageContractFixture),
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "mor" } })

    const glossLine = await within(commandDialog).findByText(/^soil layer$/i)
    const corRow = glossLine.closest("[cmdk-item]")
    expect(corRow).toBeTruthy()
    fireEvent.click(corRow as HTMLElement)

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes")) {
            return false
          }
          const body = JSON.parse(String(init?.body ?? "{}")) as {
            search_seed?: {
              gloss?: string | null
              english_translation?: string | null
            }
          }
          return body.search_seed?.gloss === "jordlag" && body.search_seed?.english_translation === "mother"
        }),
      ).toBe(true)
    })

    expect(await screen.findByRole("heading", { name: /^mor$/i })).toBeInTheDocument()
    expect(screen.getByText(/^mother \(soil layer\)$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^mother, jordlag$/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const reopenedDialog = await screen.findByRole("dialog")
    const reopenedInput = within(reopenedDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(reopenedInput, { target: { value: "mor" } })

    expect(await within(reopenedDialog).findByText(/^mother \(soil layer\)$/i)).toBeInTheDocument()
    expect(within(reopenedDialog).queryByText(/^mother, jordlag$/i)).not.toBeInTheDocument()
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

  it("request-shape: opens the word page from saved snapshot before lemma details reload completes", async () => {
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
      addWordResponse: cloneContractFixture(teacherQueuedSearchAddResponseContractFixture),
      lemmaDetailsHandler: async () => {
        await new Promise((resolve) => window.setTimeout(resolve, 300))
        return responseOf(cloneContractFixture(teacherSectionedWordPageContractFixture))
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

  it("request-shape: auto-updates the word page when sidebar-search verification finishes in the background", async () => {
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
      addWordResponse: cloneContractFixture(teacherQueuedSearchAddResponseContractFixture),
      lemmaDetailsHandler: async () => {
        lemmaDetailsRequestCount += 1
        if (lemmaDetailsRequestCount === 1) {
          return responseOf(cloneContractFixture(teacherQueuedWordPageContractFixture))
        }
        return responseOf(cloneContractFixture(teacherVerifiedWordPageContractFixture))
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

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /show verification details/i })).toBeInTheDocument()
      expect(screen.queryByRole("button", { name: /verification is running/i })).not.toBeInTheDocument()
    }, { timeout: 6_000 })
  }, 15_000)

  it("request-shape: auto-updates the open word page when queued verification finishes from a stale saved snapshot", async () => {
    let lemmaDetailsRequestCount = 0
    const staleSavedSnapshot = cloneContractFixture(teacherSectionedWordPageContractFixture)
    staleSavedSnapshot.meaning_sections[0].english_translation = "placeholder translation"
    const verifiedWordPage = cloneContractFixture(teacherVerifiedWordPageContractFixture)
    verifiedWordPage.meaning_sections[0].english_translation = "classroom mentor"

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
        ...cloneContractFixture(teacherQueuedSearchAddResponseContractFixture),
        saved_snapshot: staleSavedSnapshot,
      },
      lemmaDetailsHandler: async () => {
        lemmaDetailsRequestCount += 1
        if (lemmaDetailsRequestCount === 1) {
          return responseOf(cloneContractFixture(staleSavedSnapshot))
        }
        return responseOf(cloneContractFixture(verifiedWordPage))
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

    await waitFor(() => {
      expect(screen.getByText(/^classroom mentor$/i)).toBeInTheDocument()
      expect(screen.queryByText(/^placeholder translation$/i)).not.toBeInTheDocument()
    }, { timeout: 6_000 })
  }, 15_000)

  it("request-shape: keeps polling through Gemini auto-apply settling and updates the open word page without navigation", async () => {
    let lemmaDetailsRequestCount = 0
    const staleSavedSnapshot = cloneContractFixture(teacherSectionedWordPageContractFixture)
    staleSavedSnapshot.meaning_sections[0].english_translation = "placeholder translation"

    const flaggedBeforeAutoApply = cloneContractFixture(teacherSectionedWordPageContractFixture)
    flaggedBeforeAutoApply.meaning_sections[0].english_translation = "placeholder translation"
    flaggedBeforeAutoApply.meaning_sections[0].verification = {
      status: "flagged",
      provider: "gemini",
      reviewer_role: "Professional Danish Language Expert",
      message: "Review needed.",
      composed_word_count: null,
      stored_surface_form: "lærere",
      requested_at: "2026-04-11T12:00:00.000Z",
      completed_at: new Date().toISOString(),
      problem: "The translation is outdated.",
      change_to_implement: "Replace it with the reviewed translation.",
      suggested_actions: [
        {
          action_type: "fix_translation",
          english_translation: "classroom mentor",
          reason: "Use the reviewed translation.",
        },
      ],
    }

    const verifiedWordPage = cloneContractFixture(teacherVerifiedWordPageContractFixture)
    verifiedWordPage.meaning_sections[0].english_translation = "classroom mentor"

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
        ...cloneContractFixture(teacherQueuedSearchAddResponseContractFixture),
        saved_snapshot: staleSavedSnapshot,
      },
      lemmaDetailsHandler: async () => {
        lemmaDetailsRequestCount += 1
        if (lemmaDetailsRequestCount === 1) {
          return responseOf(cloneContractFixture(staleSavedSnapshot))
        }
        if (lemmaDetailsRequestCount <= 3) {
          return responseOf(cloneContractFixture(flaggedBeforeAutoApply))
        }
        return responseOf(cloneContractFixture(verifiedWordPage))
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
    expect(screen.getByText(/^placeholder translation$/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/^classroom mentor$/i)).toBeInTheDocument()
      expect(screen.queryByText(/^placeholder translation$/i)).not.toBeInTheDocument()
    }, { timeout: 6_000 })
  }, 15_000)
})
