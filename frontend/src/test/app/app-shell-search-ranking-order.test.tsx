import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("shows variation only for the saved homograph meaning linked to the query form", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      searchWordbankResponse: {
        items: [],
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
                cor_id: "COR.BOG.BOOK.1",
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
            lemma: "bog",
            gloss: "beechmast",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.BOG.BEECHMAST.1",
                form: "bogen",
                lemma: "bog",
                gloss: "beechmast",
                lemma_translation: "beechmast",
                gram_raw: "sb.fk.sg.best",
                norm: "N",
                lemma_idx: 124,
                gram_code: 211,
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
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "bogen" } })

    const savedVariationRow = (await within(commandDialog).findByText(/^book$/i)).closest("[cmdk-item]")
    const beechmastRow = (await within(commandDialog).findByText(/^beechmast$/i)).closest("[cmdk-item]")

    expect(savedVariationRow).toBeTruthy()
    expect(beechmastRow).toBeTruthy()
    expect(within(savedVariationRow as HTMLElement).getByTestId("search-add-variation-label")).toBeInTheDocument()
    expect(within(savedVariationRow as HTMLElement).getByTestId("search-add-icon")).toBeInTheDocument()
    expect(within(beechmastRow as HTMLElement).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect(within(beechmastRow as HTMLElement).getByTestId("search-add-icon")).toBeInTheDocument()
  })

  it("opens the selected saved meaning section from search", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: null }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "bog",
            display_lemma: "bog",
            meaning_id: 1,
            meaning_key: "book",
            gloss: "book",
            cor_lemma_idx: 123,
            variation_count: 2,
            english_translation: "book",
            match_surface: "bog",
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
          },
          {
            lemma: "bog",
            display_lemma: "bog",
            meaning_id: 2,
            meaning_key: "swamp",
            gloss: "swamp",
            cor_lemma_idx: 124,
            variation_count: 2,
            english_translation: "swamp",
            match_surface: "moser",
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: null,
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            surface_forms: [{ form: "bogen", has_pronunciation: false }],
          },
          {
            id: 2,
            meaning_key: "swamp",
            gloss: "swamp",
            english_translation: "swamp",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            surface_forms: [{ form: "moser", has_pronunciation: false }],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "moser" } })

    let swampOption: HTMLElement | undefined
    await waitFor(() => {
      swampOption = within(commandDialog)
        .getAllByRole("option")
        .find((option) => option.textContent?.toLocaleLowerCase("da-DK").includes("swamp"))
      expect(swampOption).toBeTruthy()
    })
    fireEvent.click(swampOption as HTMLElement)

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    const selectedSection = document.getElementById("wordbank-meaning-2")
    expect(selectedSection).toHaveAttribute("data-selected", "true")
    expect(selectedSection).toHaveTextContent(/swamp/i)
  })

  it("shows standard saved-lemma row with consistent from-lemma text and badges", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            query_cor_ids: ["COR.999.110.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbarhed",
        groups: [
          {
            lemma: "sigtbarhed",
            gloss: "visibility",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.999.110.01",
                form: "sigtbarhed",
                lemma: "sigtbarhed",
                gloss: "visibility",
                lemma_translation: "visibility",
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
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })

    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(await within(commandDialog).findByRole("option", { name: /sigtbarhed/i })).toBeInTheDocument()
    expect(within(commandDialog).getByText(/\bfrom\b/i)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^sigtbarhed$/i, { selector: "em" })).toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-metadata-badge")).length).toBeGreaterThan(0)
  })

  it("hides saved prefix matches until the query is exact", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            query_cor_ids: ["COR.302.110.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbar",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "sigtbar" } })
    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-open-icon")).not.toBeInTheDocument()
    })
    expect(within(commandDialog).queryByText(/^sigtbarhed$/i, { selector: "strong" })).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })
    expect(await within(commandDialog).findByText(/^sigtbarhed$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).getByText(/\bfrom\b/i)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^sigtbarhed$/i, { selector: "em" })).toBeInTheDocument()
    expect((await within(commandDialog).findAllByTestId("search-metadata-badge")).length).toBeGreaterThan(0)
  })

  it("prioritizes already-saved exact match above add-variation candidates", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" },
          { lemma: "sigtbar", variation_count: 1, english_translation: "visible" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "sigtbar",
            display_lemma: "sigtbar",
            variation_count: 1,
            english_translation: "visible",
            match_surface: null,
            pos_tag: "ADJ",
            morphology: "Degree=Pos",
          },
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sigtbarhed",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sigtbarhed",
        groups: [
          {
            lemma: "sigtbar",
            gloss: "visible",
            pos_tag: "ADJ",
            variants: [
              {
                cor_id: "COR.301.110.01",
                form: "sigtbarhed",
                lemma: "sigtbar",
                gloss: "visible",
                lemma_translation: "visible",
                gram_raw: "adj.sg.ubest.fk",
                norm: "N",
                lemma_idx: 301,
                gram_code: 110,
                variation: 1,
                pos_tag: "ADJ",
                morphology: "Degree=Pos",
                features: { Degree: "Pos" },
                extra_tags: [],
              },
            ],
          },
          {
            lemma: "sigtbarhed",
            gloss: "visibility",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.302.110.01",
                form: "sigtbarhed",
                lemma: "sigtbarhed",
                gloss: "visibility",
                lemma_translation: "visibility",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 302,
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
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "sigtbarhed" } })

    let topItem: HTMLElement | null = null
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      topItem = options[0] ?? null
      expect(topItem).not.toBeNull()
      expect(topItem?.getAttribute("data-value")?.startsWith("wordbank-sigtbarhed")).toBe(true)
    })
    const selectedTopItem = topItem as unknown as HTMLElement
    expect(selectedTopItem).toHaveAttribute("data-value")
    expect(within(selectedTopItem).queryByTestId("search-open-icon")).toBeInTheDocument()
  })

  it("renders mixed English translated COR and fallback results under one heading", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      enSearchFormResponse: {
        form: "candle",
        groups: [
          {
            lemma: "candle",
            pos_ud: "NOUN",
            pos_raw: "noun",
            danish_translation: "lys",
            meaning_description: "wax light",
            senses: [
              {
                pos_ud: "NOUN",
                sense_idx: 0,
                gloss: "A piece of wax with a wick inside that you burn to get light.",
                danish_translation: "lys",
                examples: [],
              },
            ],
          },
          {
            lemma: "candle",
            pos_ud: "VERB",
            pos_raw: "verb",
            danish_translation: "genlyse",
            meaning_description: "inspect eggs",
            senses: [
              {
                pos_ud: "VERB",
                sense_idx: 0,
                gloss: "To watch the growth of something growing inside an egg, using a bright light source.",
                danish_translation: "genlyse",
                examples: [],
              },
            ],
          },
        ],
      },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = url.searchParams.get("form")
        if (form === "lys") {
          return new Response(JSON.stringify({
            form: "lys",
            groups: [
              {
                lemma: "lys",
                gloss: null,
                pos_tag: "NOUN",
                variants: [
                  {
                    cor_id: "COR.LYS.120.01",
                    form: "lys",
                    lemma: "lys",
                    gloss: null,
                    lemma_translation: "candle",
                    saveable_translation: "candle",
                    gram_raw: "sb.itk.sg.ubest",
                    norm: "N",
                    lemma_idx: 120,
                    gram_code: 120,
                    variation: 1,
                    pos_tag: "NOUN",
                    morphology: "Gender=Neut|Number=Sing|Definite=Ind",
                    features: { Gender: "Neut", Number: "Sing", Definite: "Ind" },
                    extra_tags: [],
                  },
                ],
              },
            ],
          }), { status: 200, headers: { "Content-Type": "application/json" } })
        }
        return new Response(JSON.stringify({ form: form ?? "", groups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    fireEvent.click(within(commandDialog).getByRole("radio", { name: /^Search in English$/i }))
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "candle" } })

    expect(await within(commandDialog).findByText(/^lys$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^genlyse$/i, { selector: "strong" })).toBeInTheDocument()
    await waitFor(() => {
      expect(within(commandDialog).getAllByText(/^From the dictionary$/i)).toHaveLength(1)
    })
    expect(within(commandDialog).queryByText(/To watch the growth/i)).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/\+1 more sense/i)).not.toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^wax light$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^inspect eggs$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Verb$/i)).toBeInTheDocument()
  })

  it("keeps direct Danish COR results visible in Danish mode when the same query is also an English word", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "bog",
        groups: [
          {
            lemma: "bog",
            gloss: "til læsning",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.BOG.BOOK",
                form: "bog",
                lemma: "bog",
                gloss: "til læsning",
                gloss_translation: "for reading",
                lemma_translation: "book",
                saveable_translation: "book",
                gram_raw: "sb.fk.sg.ubest",
                norm: "N",
                lemma_idx: 123,
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
      enSearchFormResponse: {
        form: "bog",
        groups: [
          {
            lemma: "bog",
            pos_ud: "NOUN",
            pos_raw: "noun",
            danish_translation: "mose",
            meaning_description: "wet marshy land area",
            senses: [
              {
                pos_ud: "NOUN",
                sense_idx: 0,
                gloss: "A bog is large wet area with many plants.",
                danish_translation: "mose",
                examples: [],
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
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "bog" } })

    expect(await within(commandDialog).findByText(/^bog$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^book \(for reading\)$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^mose$/i, { selector: "strong" })).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^In your notebook$/i)).not.toBeInTheDocument()
  })

  it("renders English surface-form translations through matching Danish COR forms", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      enSearchFormResponse: {
        form: "dogs",
        groups: [
          {
            lemma: "dog",
            form: "dogs",
            pos_ud: "NOUN",
            pos_raw: "noun",
            danish_translation: "hunde",
            meaning_description: "plural animals",
            senses: [
              {
                pos_ud: "NOUN",
                sense_idx: 0,
                gloss: "Plural of dog.",
                danish_translation: "hunde",
                examples: [],
              },
            ],
          },
        ],
      },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = url.searchParams.get("form")
        if (form === "hunde") {
          return new Response(JSON.stringify({
            form: "hunde",
            groups: [
              {
                lemma: "hund",
                gloss: null,
                pos_tag: "NOUN",
                variants: [
                  {
                    cor_id: "COR.HUND.PL",
                    form: "hunde",
                    lemma: "hund",
                    gloss: null,
                    lemma_translation: "dogs",
                    saveable_translation: "dogs",
                    gram_raw: "sb.fk.pl.ubest",
                    norm: "N",
                    lemma_idx: 200,
                    gram_code: 120,
                    variation: 1,
                    pos_tag: "NOUN",
                    morphology: "Gender=Com|Number=Plur|Definite=Ind",
                    features: { Gender: "Com", Number: "Plur", Definite: "Ind" },
                    extra_tags: [],
                  },
                ],
              },
            ],
          }), { status: 200, headers: { "Content-Type": "application/json" } })
        }
        return new Response(JSON.stringify({ form: form ?? "", groups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    fireEvent.click(within(commandDialog).getByRole("radio", { name: /^Search in English$/i }))
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "dogs" } })

    const row = (await within(commandDialog).findByText(/^hunde$/i, { selector: "strong" })).closest("[cmdk-item]")

    expect(row).toBeTruthy()
    expect(row).toHaveTextContent(/from hund/i)
    expect(row).not.toHaveTextContent(/from dogs/i)
  })

  it("keeps translated English rows visible when wordbank search returns an unrelated corrected hit", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      wordbankSearchHandler: async () => responseOf({
        did_you_mean: "with",
        items: [
          {
            lemma: "postkort",
            display_lemma: "postkort",
            meaning_id: 200,
            meaning_key: "postcard",
            gloss: "card for mail",
            cor_lemma_idx: 54842,
            variation_count: 1,
            english_translation: "postcard",
            match_surface: null,
            matched_via: "english_gloss",
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Neut|Number=Sing|Definite=Ind",
          },
        ],
      }),
      enSearchFormResponse: {
        form: "fish",
        groups: [
          {
            lemma: "fish",
            form: "fish",
            pos_ud: "NOUN",
            pos_raw: "noun",
            danish_translation: "fisk",
            meaning_description: "aquatic animal or food",
            senses: [],
          },
          {
            lemma: "fish",
            form: "fish",
            pos_ud: "VERB",
            pos_raw: "verb",
            danish_translation: "fiske",
            meaning_description: "catch in the water",
            senses: [],
          },
        ],
      },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = url.searchParams.get("form") ?? ""
        if (form === "fisk") {
          return responseOf({
            form,
            groups: [
              {
                lemma: "fisk",
                gloss: null,
                pos_tag: "NOUN",
                variants: [
                  {
                    cor_id: "COR.FISK.NOUN",
                    form: "fisk",
                    lemma: "fisk",
                    gloss: null,
                    lemma_translation: "fish",
                    saveable_translation: "fish",
                    gram_raw: "sb.fk.sg.ubest",
                    norm: "N",
                    lemma_idx: 42931,
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
        if (form === "fiske") {
          return responseOf({
            form,
            groups: [
              {
                lemma: "fiske",
                gloss: null,
                pos_tag: "VERB",
                variants: [
                  {
                    cor_id: "COR.FISKE.VERB",
                    form: "fiske",
                    lemma: "fiske",
                    gloss: null,
                    lemma_translation: "fish",
                    saveable_translation: "fish",
                    gram_raw: "vb.inf.akt",
                    norm: "N",
                    lemma_idx: 34173,
                    gram_code: 200,
                    variation: 1,
                    pos_tag: "VERB",
                    morphology: "VerbForm=Inf|Voice=Act",
                    features: { VerbForm: "Inf", Voice: "Act" },
                    extra_tags: [],
                  },
                ],
              },
            ],
          })
        }
        return responseOf({ form, groups: [] })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    fireEvent.click(within(commandDialog).getByRole("radio", { name: /^Search in English$/i }))
    fireEvent.change(within(commandDialog).getByRole("textbox", { name: /command search/i }), { target: { value: "fish" } })

    expect(await within(commandDialog).findByText(/^fisk$/i, { selector: "strong" })).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^fiske$/i, { selector: "strong" })).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^postkort$/i, { selector: "strong" })).not.toBeInTheDocument()
  })

  it("shows exact-count translated English skeletons after COR candidates resolve", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      enSearchFormResponse: {
        form: "run",
        groups: [
          { lemma: "run", pos_ud: "VERB", pos_raw: "verb", danish_translation: "løbe", senses: [] },
          { lemma: "run", pos_ud: "NOUN", pos_raw: "noun", danish_translation: "løb", senses: [] },
          { lemma: "run", pos_ud: "NOUN", pos_raw: "noun", danish_translation: "række", senses: [] },
        ],
      },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = url.searchParams.get("form") ?? ""
        const includeTranslations = url.searchParams.get("include_translations") !== "false"
        if (form === "run") {
          return responseOf({ form, groups: [] })
        }
        if (includeTranslations) {
          return new Promise<Response>(() => {})
        }
        return responseOf({
          form,
          groups: [
            {
              lemma: form,
              gloss: form,
              pos_tag: form === "løbe" ? "VERB" : "NOUN",
              variants: [
                {
                  cor_id: `COR.${form}`,
                  form,
                  lemma: form,
                  gloss: form,
                  lemma_translation: null,
                  saveable_translation: null,
                  gram_raw: form === "løbe" ? "vb.inf.akt" : "sb.fk.sg.ubest",
                  norm: "N",
                  lemma_idx: form.length,
                  gram_code: 110,
                  variation: 1,
                  pos_tag: form === "løbe" ? "VERB" : "NOUN",
                  morphology: null,
                  features: {},
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
    fireEvent.click(within(commandDialog).getByRole("radio", { name: /^Search in English$/i }))
    fireEvent.change(within(commandDialog).getByRole("textbox", { name: /command search/i }), { target: { value: "run" } })

    expect(await within(commandDialog).findAllByTestId("search-pending-skeleton")).toHaveLength(1)
    expect(await within(commandDialog).findAllByTestId("search-en-skeleton")).toHaveLength(3)
    expect(within(commandDialog).queryByText(/^løbe$/i, { selector: "strong" })).not.toBeInTheDocument()
  })

  it("shows search skeletons immediately while the search flow is still resolving", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      wordbankSearchHandler: async () => new Promise<Response>(() => {}),
      corSearchFormHandler: async () => new Promise<Response>(() => {}),
      enSearchFormHandler: async () => new Promise<Response>(() => {}),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    fireEvent.change(within(commandDialog).getByRole("textbox", { name: /command search/i }), { target: { value: "zztest" } })

    expect(await within(commandDialog).findAllByTestId("search-pending-skeleton")).toHaveLength(1)
    expect(within(commandDialog).queryByText(/^Nothing found for/i)).not.toBeInTheDocument()
  })

  it("does not guess translated English skeletons while English lookup is still resolving", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormResponse: {
        form: "shit",
        groups: [
          {
            lemma: "shit",
            gloss: null,
            pos_tag: "INTJ",
            variants: [
              {
                cor_id: "COR.SHIT.INTJ",
                form: "shit",
                lemma: "shit",
                gloss: null,
                lemma_translation: "shit",
                saveable_translation: "shit",
                gram_raw: "udråbsord",
                norm: "N",
                lemma_idx: 111,
                gram_code: 1,
                variation: 1,
                pos_tag: "INTJ",
                morphology: null,
                features: {},
                extra_tags: [],
              },
            ],
          },
        ],
      },
      enSearchFormHandler: async () => new Promise<Response>(() => {}),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "shit" } })

    await waitFor(() => {
      expect(within(commandDialog).queryAllByTestId("search-en-skeleton")).toHaveLength(0)
      expect(within(commandDialog).queryByText(/^shit$/i, { selector: "strong" })).not.toBeInTheDocument()
    })
  })
})
