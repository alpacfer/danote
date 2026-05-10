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
    expect(screen.getByRole("button", { name: /open function words reference/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /open numbers & time reference/i })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open personal pronouns reference/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /open question words reference/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/no saved lemmas yet/i)).not.toBeInTheDocument()
  })

  it("renders grouped tabs with simplified word cards", async () => {
    const user = userEvent.setup()
    mockFetchImplementation({
      lemmasResponse: {
        items: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    expect(await screen.findByRole("heading", { name: /^pronouns$/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /personal/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /possessive/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /question words/i })).toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /question words/i }))
    const hvorCard = await screen.findByRole("button", { name: /open hvor in wordbank/i })
    expect(within(hvorCard).getByRole("button", { name: /listen to hvor/i })).toBeInTheDocument()
    expect(within(hvorCard).getByText(/^where$/i)).toBeInTheDocument()
    expect(within(hvorCard).getByText(/^Adverb$/i)).toBeInTheDocument()
    expect(within(hvorCard).getByText(/^Interrogative$/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /generate example/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /see examples/i })).not.toBeInTheDocument()
  })

  it("opens a normal word page from a pinned word card", async () => {
    const user = userEvent.setup()
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

    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    await user.click(screen.getByRole("tab", { name: /question words/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open hvor in wordbank/i }))

    expect(await screen.findByRole("heading", { name: /^hvor$/i })).toBeInTheDocument()
    expect(screen.getByTestId("wordbank-pinned-home-card")).toHaveTextContent("Pronouns: Question Words")
    expect(fetchSpy.mock.calls.some(([input]) => String(input).endsWith("/api/wordbank/lemmas/hvor"))).toBe(true)
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
    fireEvent.click(await screen.findByRole("button", { name: /open function words reference/i }))
    expect(await screen.findByRole("heading", { name: /function words/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /articles/i })).toHaveAttribute("data-state", "active")

    await waitFor(() => {
      expect(screen.queryByText(/forming larger numbers/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/word-order notes/i)).not.toBeInTheDocument()
    })
  })

  it("restores pinned tab state with browser back and forward", async () => {
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
    await user.click(screen.getByRole("tab", { name: /question words/i }))
    expect(screen.getByRole("tab", { name: /question words/i })).toHaveAttribute("data-state", "active")

    window.history.back()
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /possessive/i })).toHaveAttribute("data-state", "active")
    })

    window.history.forward()
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /question words/i })).toHaveAttribute("data-state", "active")
    })
  })
})
