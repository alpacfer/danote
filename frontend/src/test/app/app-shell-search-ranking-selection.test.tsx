import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

describe("App shell and search", () => {
  it("keeps exact-lemma open result above linked variation result for same query", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "lærer", variation_count: 1, english_translation: "teacher" },
          { lemma: "lære", variation_count: 3, english_translation: "learn" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "lære",
            display_lemma: "at lære",
            variation_count: 3,
            english_translation: "learn",
            match_surface: null,
            pos_tag: "VERB",
            morphology: "VerbForm=Inf",
          },
          {
            lemma: "lærer",
            display_lemma: "lærer",
            variation_count: 1,
            english_translation: "teacher",
            match_surface: null,
            query_cor_ids: ["COR.49032.110.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
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
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(1)
    })
    const options = within(commandDialog).getAllByRole("option")
    const topItem = options[0]
    expect(topItem).toHaveTextContent(/^lærer/i)
    expect(within(topItem).queryByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(topItem).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
  })

  it("command search marks only meaning-matched COR options as variations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lære", variation_count: 3, english_translation: "learn" }],
      },
      searchWordbankResponse: {
        items: [],
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

    const verbLemma = await within(commandDialog).findByText(/^at lære$/i, { selector: "em" })
    const nounLemma = await within(commandDialog).findByText(/^lærer$/i, { selector: "em" })
    const verbItem = verbLemma.closest("[cmdk-item]")
    const nounItem = nounLemma.closest("[cmdk-item]")

    expect(verbItem).toBeTruthy()
    expect(nounItem).toBeTruthy()
    expect(within(verbItem as HTMLElement).getByTestId("search-add-variation-label")).toBeInTheDocument()
    expect(within(nounItem as HTMLElement).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    expect(within(verbItem as HTMLElement).getByTestId("search-add-icon")).toBeInTheDocument()
    expect(within(nounItem as HTMLElement).getByTestId("search-add-icon")).toBeInTheDocument()
    expect(verbItem && nounItem
      ? (verbItem.compareDocumentPosition(nounItem) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
      : false).toBe(true)
  })

  it("shows saved lemmas only for exact queries and keeps non-legacy badges", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "ulykke", variation_count: 2, english_translation: "accident" }],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "ulykke",
            display_lemma: "ulykke",
            variation_count: 2,
            english_translation: "accident",
            match_surface: "ulykker",
            query_cor_ids: ["COR.700.112.01"],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Plur|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "ulykker",
        groups: [
          {
            lemma: "ulykke",
            gloss: "accident",
            pos_tag: "NOUN",
            variants: [
              {
                cor_id: "COR.700.112.01",
                form: "ulykker",
                lemma: "ulykke",
                gloss: "accidents",
                lemma_translation: "accident",
                gram_raw: "sb.fk.pl.ubest",
                norm: "N",
                lemma_idx: 700,
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
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)

    fireEvent.change(searchInput, { target: { value: "ulykk" } })
    await waitFor(() => {
      expect(within(commandDialog).queryByTestId("search-open-icon")).not.toBeInTheDocument()
    })
    expect(await within(commandDialog).findByText(/no results found\./i)).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^ulykke$/i, { selector: "strong" })).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "ulykker" } })
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-variation-label")).not.toBeInTheDocument()
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0].getAttribute("data-value")?.startsWith("wordbank-ulykke")).toBe(true)
    })
    expect(await within(commandDialog).findByText(/^Noun$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^n-word$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Indefinite$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^NOUN$/)).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: "ulykke" } })
    expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0].getAttribute("data-value")?.startsWith("wordbank-ulykke")).toBe(true)
    })
  })
})
