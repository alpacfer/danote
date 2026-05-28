import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, toast, vi, waitFor, within } from "@/test/app-test-helpers"

async function findCommandOptionByValue(commandDialog: HTMLElement, value: string) {
  let option: HTMLElement | undefined
  await waitFor(() => {
    option = within(commandDialog)
      .getAllByRole("option")
      .find((item) => item.getAttribute("data-value") === value)
    expect(option).toBeTruthy()
  })
  return option as HTMLElement
}

describe("App shell and search", () => {
  it("keeps untranslated COR results visible and shows toast when Azure translations fail", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormHandler: async (input) => {
        const url = String(input)
        const parsed = new URL(url, "http://localhost")
        const includeTranslations = parsed.searchParams.get("include_translations") !== "false"
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
                    cor_id: "COR.49032.210.01",
                    form: "lærer",
                    lemma: "lære",
                    gloss: "learn",
                    gloss_translation: null,
                    lemma_translation: null,
                    gram_raw: "vb.prs.akt",
                    norm: "V",
                    lemma_idx: 49032,
                    gram_code: 210,
                    variation: 1,
                    pos_tag: "VERB",
                    morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                    features: { Tense: "Pres", VerbForm: "Fin", Voice: "Act" },
                    extra_tags: [],
                  },
                ],
              },
            ],
          })
        }
        return {
          ok: false,
          status: 503,
          json: async () => ({ detail: "Azure translation is unavailable." }),
        } as Response
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    await findCommandOptionByValue(commandDialog, "cor-variant-COR.49032.210.01")
    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith("Azure translation is unavailable.")
    })
    expect(await findCommandOptionByValue(commandDialog, "cor-variant-COR.49032.210.01")).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^learn$/i)).not.toBeInTheDocument()
  })

  it("shows a backend connectivity message when adding from search hits a network failure", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.49032.210.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.prs.akt",
                norm: "V",
                lemma_idx: 49032,
                gram_code: 210,
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
      addWordHandler: async () => {
        throw new TypeError("Failed to fetch")
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    fireEvent.click(await findCommandOptionByValue(commandDialog, "cor-variant-COR.49032.210.01"))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "Could not add word to wordbank. Could not reach the backend at http://127.0.0.1:8000. Check that it is running and try again.",
      )
    })
  })

  it("shows backend error details when adding from search returns an API error", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      corSearchFormResponse: {
        form: "lærer",
        groups: [
          {
            lemma: "lære",
            gloss: "learn",
            pos_tag: "VERB",
            variants: [
              {
                cor_id: "COR.49032.210.01",
                form: "lærer",
                lemma: "lære",
                gloss: "learn",
                lemma_translation: "to learn",
                gram_raw: "vb.prs.akt",
                norm: "V",
                lemma_idx: 49032,
                gram_code: 210,
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
      addWordHandler: async () => ({
        ok: false,
        status: 409,
        json: async () => ({ detail: "The word 'lærer' is already saved as a variation." }),
      } as Response),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
    fireEvent.change(searchInput, { target: { value: "lærer" } })

    fireEvent.click(await findCommandOptionByValue(commandDialog, "cor-variant-COR.49032.210.01"))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith("The word 'lærer' is already saved as a variation.")
    })
  })
})
