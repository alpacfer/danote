import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("hides the second line for saved-word search results without a gloss", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
          {
            lemma: "kat",
            display_lemma: "kat",
            variation_count: 1,
            english_translation: null,
            match_surface: null,
          },
        ],
      },
      corSearchFormResponse: {
        form: "kat",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "kat" } })

    expect(await within(commandDialog).findByText(/^kat$/i, { selector: "strong" })).toBeInTheDocument()

    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-translation-skeleton")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/^no translation available\.$/i)).not.toBeInTheDocument()
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/translation")),
      ).toBe(false)
    })
  })

  it("shows saved-word rows as translation plus gloss translation without raw gloss fallback", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
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
            query_cor_ids: ["COR.MOR.SOIL.LEM"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "mor",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "mor" } })

    expect(await within(commandDialog).findByText(/^mother \(soil layer\)$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^mother, jordlag$/i)).not.toBeInTheDocument()
  })

  it("omits raw gloss from saved-word translation lines when gloss translation is missing", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
          {
            lemma: "mor",
            display_lemma: "mor",
            meaning_id: 2,
            meaning_key: "soil-layer",
            gloss: "jordlag",
            gloss_translation: null,
            cor_lemma_idx: 51047,
            variation_count: 1,
            english_translation: "mother",
            match_surface: null,
            query_cor_ids: ["COR.MOR.SOIL.LEM"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "mor",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "mor" } })

    expect(await within(commandDialog).findByText(/^mother$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^mother, jordlag$/i)).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^jordlag$/i)).not.toBeInTheDocument()
  })

  it("hides the second line for COR search results without a gloss", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "kattens",
        groups: [
          {
            lemma: "kat",
            gloss: null,
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.777.111.01",
                form: "kattens",
                lemma: "kat",
                gloss: null,
                lemma_translation: null,
                gram_raw: "sb.fk.sg.best.gen",
                norm: "N",
                lemma_idx: 777,
                gram_code: 111,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def|Case=Gen",
                features: { Gender: "Com", Number: "Sing", Definite: "Def", Case: "Gen" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "kattens" } })

    expect(await within(commandDialog).findByText(/^kattens$/i, { selector: "strong" })).toBeInTheDocument()

    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-translation-skeleton")).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/^no translation available\.$/i)).not.toBeInTheDocument()
      expect(within(commandDialog).queryByText(/the cat's/i)).not.toBeInTheDocument()
      expect(
        fetchSpy.mock.calls.some(([input]) => String(input).includes("/api/wordbank/translation")),
      ).toBe(false)
    })
  })

  it("keeps COR rows saveable when only a gloss fallback is available", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "bil",
        groups: [
          {
            lemma: "bil",
            gloss: "car",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.999.110.01",
                form: "bil",
                lemma: "bil",
                gloss: "car",
                gloss_translation: "car",
                lemma_translation: "car",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 999,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "bile",
            gloss: "køre i bil",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.36439.209.01",
                form: "bil",
                lemma: "bile",
                gloss: "køre i bil",
                gloss_translation: "go by car",
                lemma_translation: null,
                saveable_translation: "go by car",
                lemma_translation_provider: "deepl_translator",
                lemma_translation_status: "gloss_fallback",
                lemma_translation_reason: "gloss_fallback_used",
                gram_raw: "vb.imp",
                norm: "N",
                lemma_idx: 36439,
                gram_code: 209,
                variation: 1,
                pos_tag: "VERB",
                morphology: "Mood=Imp|VerbForm=Fin",
                features: { Mood: "Imp", VerbForm: "Fin" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bil" } })

    await within(commandDialog).findAllByText(/^bil$/i, { selector: "strong" })
    const verbLemma = await within(commandDialog).findByText(/^at bile$/i, { selector: "em" })
    const verbRow = verbLemma.closest("[cmdk-item]")
    expect(verbRow).toBeTruthy()
    expect(verbRow).not.toHaveTextContent(/\(to bile\)/i)
    expect(within(commandDialog).queryByText(/translation required before saving\./i)).not.toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^go by car$/i)).toBeInTheDocument()
  })

  it("keeps translation skeletons visible on selected COR results while translations load", async () => {
    let resolveFullPayload: ((value: Response) => void) | null = null
    const fullPayloadPromise = new Promise<Response>((resolve) => {
      resolveFullPayload = resolve
    })
    const corSearchFormHandler = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost")
      const includeTranslations = url.searchParams.get("include_translations") !== "false"
      if (!includeTranslations) {
        return responseOf({
          form: "lærer",
          groups: [
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
                  lemma_translation: null,
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
                  lemma_translation: null,
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
              ],
            },
          ],
        })
      }
      return fullPayloadPromise
    })

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormHandler,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    const selectedOption = await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("data-selected", "true")
      const selectedSkeletons = within(options[0]).getAllByTestId("search-translation-skeleton")
      expect(selectedSkeletons.length).toBeGreaterThan(0)
      return options[0]
    })

    const selectedSkeletons = within(selectedOption).getAllByTestId("search-translation-skeleton")
    for (const skeleton of selectedSkeletons) {
      expect(skeleton.className).toContain("group-data-[selected=true]/search-item:bg-accent-foreground/20")
    }
    expect(within(commandDialog).queryByText(/^waiting for translation\.\.\.$/i)).not.toBeInTheDocument()

    fireEvent.keyDown(searchInput, { key: "ArrowDown" })

    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("aria-disabled", "true")
      expect(options[1]).toHaveAttribute("aria-disabled", "true")
      expect(options[0]).toHaveAttribute("data-selected", "true")
      const selectedSkeletonsAfterArrow = within(options[0]).getAllByTestId("search-translation-skeleton")
      expect(selectedSkeletonsAfterArrow.length).toBeGreaterThan(0)
    })

    resolveFullPayload?.(responseOf({
      form: "lærer",
      groups: [
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
          ],
        },
      ],
    }))

    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-translation-skeleton")).not.toBeInTheDocument()
    })
  })

  it("keeps showing other add alternatives when an exact saved form exists", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1, english_translation: "teacher" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "lærer",
            display_lemma: "lærer",
            variation_count: 1,
            english_translation: "teacher",
            match_surface: null,
            query_cor_ids: ["COR.49032.110.01"],
          },
        ],
      },
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
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    expect((await within(commandDialog).findAllByText(/^lærer$/i)).length).toBeGreaterThan(0)
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-add-icon")).length).toBeGreaterThan(0)
  })

  it("shows eye icon for already-saved variation and still keeps alternative COR entries", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            variation_count: 2,
            english_translation: "book",
            match_surface: "bogen",
            query_cor_ids: ["COR.123.111.01"],
          },
        ],
      },
      corSearchFormResponse: {
        form: "bogen",
        groups: [
          {
            lemma: "bog",
            gloss: "book",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.123.111.01",
                form: "bogen",
                lemma: "bog",
                gloss: "book",
                lemma_translation: "book",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 123,
                gram_code: 111,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                features: { Gender: "Com", Number: "Sing", Definite: "Def" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "boge",
            gloss: "arc",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.456.111.01",
                form: "bogen",
                lemma: "boge",
                gloss: "arc",
                lemma_translation: "arc",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 456,
                gram_code: 111,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                features: { Gender: "Com", Number: "Sing", Definite: "Def" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bogen" } })

    expect((await within(commandDialog).findAllByText(/^bogen$/i)).length).toBeGreaterThan(0)
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect(await within(commandDialog).findAllByTestId("search-add-icon")).toHaveLength(1)
    expect(await within(commandDialog).findByText(/^boge$/i, { selector: "em" })).toBeInTheDocument()
  })

  it("hides only the saved COR id and keeps homonym alternatives with same lemma and form", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "mus", variation_count: 1, english_translation: "mouse" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "mus",
            display_lemma: "mus",
            variation_count: 1,
            english_translation: "mouse",
            match_surface: "mus",
            query_cor_ids: ["COR.111.110.01"],
          },
        ],
      },
      corSearchFormResponse: {
        form: "mus",
        groups: [
          {
            lemma: "mus",
            gloss: "mouse-animal",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.111.110.01",
                form: "mus",
                lemma: "mus",
                gloss: "mouse-animal",
                lemma_translation: "mouse",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 111,
                gram_code: 110,
                variation: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
              {
                cor_id: "COR.111.110.02",
                form: "mus",
                lemma: "mus",
                gloss: "mussel-food",
                lemma_translation: "mussel",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 111,
                gram_code: 110,
                variation: 2,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
                extra_tags: [],
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "mus" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(await within(commandDialog).findAllByTestId("search-add-icon")).toHaveLength(1)
    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option")).toHaveLength(2)
    })
  })
})
