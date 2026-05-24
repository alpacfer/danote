import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"
import userEvent from "@testing-library/user-event"

describe("App wordbank pinned pages", () => {
  it("shows only grouped built-in references in an empty wordbank", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(await screen.findByRole("button", { name: /open pronouns reference/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /open hv questions reference/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /open prepositions reference/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /open conjunctions reference/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /open numbers & time reference/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open function words reference/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open articles reference/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open personal pronouns reference/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open question words reference/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/no saved lemmas yet/i)).not.toBeInTheDocument()
  })

  it("renders the HV Questions page with simplified word cards", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open hv questions reference/i }))
    expect(await screen.findByRole("heading", { name: /^hv questions$/i })).toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: /people & things/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: /choice/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: /place, time, manner & reason/i })).not.toBeInTheDocument()

    const hvorCard = await screen.findByRole("button", { name: /open hvor in wordbank/i })
    expect(within(hvorCard).queryByRole("button", { name: /listen to hvor/i })).not.toBeInTheDocument()
    expect(within(hvorCard).getByText(/^where$/i)).toBeInTheDocument()
    expect(within(hvorCard).getByText(/^HV Word$/)).toBeInTheDocument()
    expect(within(hvorCard).queryByText(/^Adverb$/i)).not.toBeInTheDocument()
    expect(within(hvorCard).queryByText(/^Interrogative$/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /generate example/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /see examples/i })).not.toBeInTheDocument()
  })

  it("no longer renders a question_words tab on the Pronouns page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    expect(await screen.findByRole("heading", { name: /^pronouns$/i })).toBeInTheDocument()
    expect(screen.queryByRole("tab", { name: /question words/i })).not.toBeInTheDocument()
  })

  it("opens a normal word page from a pinned word card", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/hvor")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "hvor",
          english_translation: "where",
          pos_tag: "ADV",
          morphology: "PronType=Int",
          reference_links: [
            {
              page_id: "hv_questions",
              page_title: "HV Questions",
              tab_id: "hv_place_time_manner",
              tab_title: "Place, Time, Manner & Reason",
              sentinel: "__pinned_hv_questions_place_time_manner",
            },
          ],
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [
            {
              form: "hvor",
              has_pronunciation: true,
              lemma: "hvor",
              lemma_translation: "where",
            },
          ],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open hv questions reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open hvor in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^hvor$/i })).toBeInTheDocument()
    expect(screen.queryByTestId("wordbank-pinned-home-card")).not.toBeInTheDocument()
    expect(fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/lemmas/hvor"))).toBe(true)
  })

  it("clicks the HV Word badge on a word page to land on the HV Questions pinned page", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/hvor")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "hvor",
          english_translation: "where",
          pos_tag: "ADV",
          morphology: "PronType=Int",
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [{ form: "hvor", has_pronunciation: true }],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open hv questions reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open hvor in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^hvor$/i })).toBeInTheDocument()
    const headerBadges = await screen.findByTestId("wordbank-lemma-header-badges")
    const hvBadge = within(headerBadges).getByText(/^HV Word$/)
    expect(within(headerBadges).queryByText(/^Adverb$/i)).not.toBeInTheDocument()
    fireEvent.click(hvBadge)
    expect(await screen.findByRole("heading", { name: /^hv questions$/i })).toBeInTheDocument()
  })

  it("clicks the Pronoun badge on a word page to land on the Pronouns pinned page", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/du")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "du",
          english_translation: "you",
          pos_tag: "PRON",
          morphology: "PronType=Prs|Case=Nom|Person=2|Number=Sing",
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [{ form: "du", has_pronunciation: true }],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open du in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^du$/i })).toBeInTheDocument()
    const headerBadges = await screen.findByTestId("wordbank-lemma-header-badges")
    fireEvent.click(within(headerBadges).getByText(/^Pronoun$/))
    expect(await screen.findByRole("heading", { name: /^pronouns$/i })).toBeInTheDocument()
  })

  it("clicks the Preposition badge to land on the Prepositions pinned page", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/p%C3%A5")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "på",
          english_translation: "on / at",
          pos_tag: "ADP",
          morphology: null,
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [{ form: "på", has_pronunciation: true }],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(await screen.findByRole("button", { name: /open prepositions reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open på in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^på$/i })).toBeInTheDocument()
    const headerBadges = await screen.findByTestId("wordbank-lemma-header-badges")
    fireEvent.click(within(headerBadges).getByText(/^Preposition$/))
    expect(await screen.findByRole("heading", { name: /^prepositions$/i })).toBeInTheDocument()
  })

  it("clicks the Conjunction badge to land on the Conjunctions pinned page", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/og")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "og",
          english_translation: "and",
          pos_tag: "CCONJ",
          morphology: null,
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [{ form: "og", has_pronunciation: true }],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(await screen.findByRole("button", { name: /open conjunctions reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open og in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^og$/i })).toBeInTheDocument()
    const headerBadges = await screen.findByTestId("wordbank-lemma-header-badges")
    fireEvent.click(within(headerBadges).getByText(/^Conjunction$/))
    expect(await screen.findByRole("heading", { name: /^conjunctions$/i })).toBeInTheDocument()
  })

  it("opens saved built-in search results as word pages", async () => {
    const user = userEvent.setup()
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      wordbankSearchHandler: async () => responseOf({
        items: [{
          lemma: "hvor",
          display_lemma: "hvor",
          english_translation: "where",
          variation_count: 1,
          match_surface: null,
          query_cor_ids: [],
          pos_tag: "ADV",
          morphology: "PronType=Int",
        }],
      }),
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/hvor")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf({
          lemma: "hvor",
          english_translation: "where",
          pos_tag: "ADV",
          morphology: "PronType=Int",
          is_sectioned: false,
          meaning_sections: [],
          surface_forms: [{ form: "hvor", has_pronunciation: true }],
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await user.keyboard("{Meta>}k{/Meta}")
    const input = screen.getByRole("textbox", { name: /command search/i })
    await user.type(input, "hvor")
    await screen.findByRole("option", { name: /hvor/i })
    fireEvent.keyDown(input, { key: "Enter" })

    expect(await screen.findByRole("heading", { name: /^hvor$/i })).toBeInTheDocument()
    expect(fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/lemmas/hvor"))).toBe(true)
    expect(screen.queryByRole("heading", { name: /^pronouns$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /^hv questions$/i })).not.toBeInTheDocument()
  })

  it("maps legacy built-in sentinels to grouped pages and default tabs", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open numbers & time reference/i }))
    expect(await screen.findByRole("heading", { name: /numbers & time/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /cardinal numbers/i })).toHaveAttribute("data-state", "active")

    fireEvent.click(screen.getByRole("button", { name: /^wordbank$/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open prepositions reference/i }))
    expect(await screen.findByRole("heading", { name: /^prepositions$/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /^wordbank$/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open conjunctions reference/i }))
    expect(await screen.findByRole("heading", { name: /^conjunctions$/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.queryByText(/forming larger numbers/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/word-order notes/i)).not.toBeInTheDocument()
    })
  })

  it("replaces pinned tab state instead of adding tab-level history entries", async () => {
    const user = userEvent.setup()
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    await user.click(screen.getByRole("tab", { name: /possessive/i }))
    expect(screen.getByRole("tab", { name: /possessive/i })).toHaveAttribute("data-state", "active")
    await user.click(screen.getByRole("tab", { name: /demonstrative/i }))
    expect(screen.getByRole("tab", { name: /demonstrative/i })).toHaveAttribute("data-state", "active")

    window.history.back()
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /^pronouns$/i })).not.toBeInTheDocument()
    })
    expect(await screen.findByRole("button", { name: /open pronouns reference/i })).toBeInTheDocument()

    window.history.forward()
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /demonstrative/i })).toHaveAttribute("data-state", "active")
    })
  })
})
