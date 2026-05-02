import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"
import userEvent from "@testing-library/user-event"

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

async function setSearchValue(user: ReturnType<typeof userEvent.setup>, input: HTMLElement, value: string) {
  await user.click(input)
  fireEvent.change(input, { target: { value } })
  await waitFor(() => {
    expect(input).toHaveValue(value)
  })
}

async function waitForSearchCloseCleanup() {
  await new Promise((resolve) => window.setTimeout(resolve, 250))
}

describe("App shell and search", () => {
  it("keeps added ulykker visible and selected across exact query transitions", async () => {
    const user = userEvent.setup()
    const lemmaItems: Array<{
      lemma: string
      variation_count: number
      english_translation?: string | null
    }> = []
    const searchItems: Array<{
      lemma: string
      display_lemma: string
      variation_count: number
      english_translation?: string | null
      match_surface?: string | null
      query_cor_ids?: string[]
      pos_tag?: string | null
      morphology?: string | null
    }> = []
    let addedCount = 0

    mockFetchImplementation({
      lemmasResponse: { items: lemmaItems },
      searchWordbankResponse: { items: searchItems },
      corSearchFormHandler: async (input) => {
        const url = new URL(String(input), "http://localhost")
        const form = (url.searchParams.get("form") ?? "").trim().toLocaleLowerCase("da-DK")
        if (form !== "ulykker") {
          return responseOf({ form, groups: [] })
        }
        return responseOf({
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
        })
      },
      addWordHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          surface_token?: string
          lemma_candidate?: string | null
        }
        if (body.surface_token === "ulykker" && body.lemma_candidate === "ulykke") {
          addedCount += 1
          if (lemmaItems.length === 0) {
            lemmaItems.push({
              lemma: "ulykke",
              variation_count: 2,
              english_translation: "accident",
            })
          }
          if (searchItems.length === 0) {
            searchItems.push({
              lemma: "ulykke",
              display_lemma: "ulykke",
              variation_count: 2,
              english_translation: "accident",
              match_surface: "ulykker",
              query_cor_ids: ["COR.700.112.01"],
              pos_tag: "NOUN",
              morphology: "Gender=Com|Number=Plur|Definite=Ind",
            })
          }
          return responseOf({
            status: "inserted",
            stored_lemma: "ulykke",
            stored_surface_form: "ulykker",
            source: "manual",
            message: "Added 'ulykke' to wordbank.",
          })
        }

        return responseOf({
          status: "exists",
          stored_lemma: body.lemma_candidate ?? "ulykke",
          stored_surface_form: body.surface_token ?? null,
          source: "manual",
          message: "Word already exists.",
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    let commandDialog = await screen.findByRole("dialog")
    let searchInput = within(commandDialog).getByPlaceholderText(/search words/i)

    await setSearchValue(user, searchInput, "ulykker")
    fireEvent.click(await findCommandOptionByValue(commandDialog, "cor-variant-COR.700.112.01"))

    await waitFor(() => {
      expect(addedCount).toBe(1)
    })
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    await waitForSearchCloseCleanup()

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    commandDialog = await screen.findByRole("dialog")
    searchInput = within(commandDialog).getByPlaceholderText(/search words/i)

    await setSearchValue(user, searchInput, "ulykker")
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
    }, { timeout: 5_000 })
    expect(await within(commandDialog).findByTestId("search-open-icon")).toBeInTheDocument()
    expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Noun$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^n-word$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await within(commandDialog).findByText(/^Indefinite$/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^NOUN$/)).not.toBeInTheDocument()

    await setSearchValue(user, searchInput, "ulykke")
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
      expect(options[0].getAttribute("data-value")?.startsWith("wordbank-ulykke")).toBe(true)
    }, { timeout: 5_000 })
    expect(within(commandDialog).queryByTestId("search-add-icon")).not.toBeInTheDocument()

    await setSearchValue(user, searchInput, "ulykker")
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
      expect(options[0]).toHaveAttribute("data-selected", "true")
    }, { timeout: 5_000 })

    await setSearchValue(user, searchInput, "ulykke")
    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(0)
    })
    await setSearchValue(user, searchInput, "ulykker")
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    }, { timeout: 5_000 })

    fireEvent.keyDown(window, { key: "k", ctrlKey: true })
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    await waitForSearchCloseCleanup()
    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    commandDialog = await screen.findByRole("dialog")
    searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    await setSearchValue(user, searchInput, "ulykker")
    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options.length).toBeGreaterThan(0)
      expect(options[0]).toHaveTextContent(/ulykk/i)
    })
  }, 20_000)

  it("resets selection to first result on each new search update", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "silde", variation_count: 1, english_translation: "herring" },
          { lemma: "sild", variation_count: 1, english_translation: "herring" },
          { lemma: "sigtbarhed", variation_count: 1, english_translation: "visibility" },
        ],
      },
      searchWordbankResponse: {
        items: [
          {
            lemma: "silde",
            display_lemma: "silde",
            variation_count: 1,
            english_translation: "herring",
            match_surface: "sild",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
          {
            lemma: "sild",
            display_lemma: "sild",
            variation_count: 1,
            english_translation: "herring",
            match_surface: null,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
          {
            lemma: "sigtbarhed",
            display_lemma: "sigtbarhed",
            variation_count: 1,
            english_translation: "visibility",
            match_surface: "sild",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "sild",
        groups: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    fireEvent.change(searchInput, { target: { value: "sild" } })

    await waitFor(() => {
      expect(within(commandDialog).getAllByRole("option").length).toBeGreaterThan(2)
    })

    fireEvent.keyDown(searchInput, { key: "ArrowDown" })
    fireEvent.keyDown(searchInput, { key: "ArrowDown" })

    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("data-selected", "false")
    })

    fireEvent.change(searchInput, { target: { value: "silde" } })

    await waitFor(() => {
      const options = within(commandDialog).getAllByRole("option")
      expect(options[0]).toHaveAttribute("data-selected", "true")
    })
  }, 20_000)
})
