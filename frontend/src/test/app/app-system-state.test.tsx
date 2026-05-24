import { act, fireEvent, mockFetchImplementation, renderApp, responseOf, screen, toast, vi, waitFor, within } from "@/test/app-test-helpers"
import userEvent from "@testing-library/user-event"

async function openDeveloperSection(user = userEvent.setup()) {
  fireEvent.click(screen.getByRole("button", { name: /search/i }))
  const commandDialog = await screen.findByRole("dialog")
  const searchInput = within(commandDialog).getByRole("textbox", { name: /command search/i })
  await user.type(searchInput, "chochito")
  fireEvent.click(await within(commandDialog).findByText(/^Developer$/))
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })
}

describe("App system state", () => {
  it("renders offline status when health check fails", async () => {
    mockFetchImplementation({ healthOk: false })

    renderApp()

    expect(await screen.findByText(/offline/i)).toBeInTheDocument()
  })

  it("renders degraded status when backend health is degraded", async () => {
    mockFetchImplementation({ healthStatus: "degraded" })

    renderApp()

    expect(await screen.findByText(/degraded/i)).toBeInTheDocument()
  })

  it("shows developer status without NLP model controls", async () => {
    mockFetchImplementation({
      healthResponse: {
        status: "ok",
        service: "backend",
        apis: {
          backend: { status: "ok", active: true, configured: true },
          azure_translator: { status: "ok", active: true, configured: true },
          azure_speech: {
            status: "inactive",
            active: false,
            configured: false,
            message: "Provider 'azure' is not selected.",
          },
        },
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await openDeveloperSection()

    expect(screen.queryByRole("combobox", { name: /nlp model picker/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/backend default remains/i)).not.toBeInTheDocument()
    expect(screen.getByLabelText("api-status-list")).toBeInTheDocument()
    expect(screen.getByText("Backend API")).toBeInTheDocument()
    expect(screen.getByText("Azure Translator API")).toBeInTheDocument()
    expect(screen.getByText("Azure Speech API")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /apply runtime api keys/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /test gemini/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /delete db \+ clear cache/i })).not.toBeInTheDocument()
  })

  it("tests Gemini from developer options and shows inline result", async () => {
    const user = userEvent.setup()

    mockFetchImplementation({
      healthResponse: {
        status: "ok",
        service: "backend",
        apis: {
          backend: { status: "ok", active: true, configured: true },
          azure_translator: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
          azure_speech: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
          gemini: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
        },
      },
      geminiProbeResponse: {
        status: "ok",
        probe_input: "bogen",
        result_text: "the book",
        provider: "gemini_word_translation",
        message: "Gemini probe completed successfully.",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await openDeveloperSection(user)
    await user.click(screen.getByRole("tab", { name: /probes/i }))
    fireEvent.click(await screen.findByRole("button", { name: /test gemini/i }))

    expect(await screen.findByLabelText("gemini-probe-result")).toHaveTextContent(/the book/i)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Gemini probe completed successfully.")
    expect(screen.queryByLabelText("api-status-list")).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /status/i }))
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/gemini/i)
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/^ok$|ok/i)
  })

  it("tests DeepL and Speech from developer options and updates API status", async () => {
    const user = userEvent.setup()

    mockFetchImplementation({
      healthResponse: {
        status: "ok",
        service: "backend",
        apis: {
          backend: { status: "ok", active: true, configured: true },
          deepl_translator: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
          azure_translator: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
          azure_speech: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
          gemini: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
        },
      },
      translationProbeResponse: {
        status: "ok",
        probe_input: "bogen",
        result_text: "the book",
        provider: "deepl_translator",
        message: "DeepL Translator probe completed successfully.",
      },
      speechProbeResponse: {
        status: "error",
        probe_input: "bogen",
        result_text: null,
        provider: "azure_speech_tts",
        message: "Azure Speech probe failed.",
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await openDeveloperSection(user)
    await user.click(screen.getByRole("tab", { name: /probes/i }))
    fireEvent.click(await screen.findByRole("button", { name: /test deepl/i }))
    fireEvent.click(screen.getByRole("button", { name: /test azure speech/i }))

    expect(await screen.findByLabelText("translation-probe-result")).toHaveTextContent(/the book/i)
    expect(await screen.findByLabelText("speech-probe-result")).toHaveTextContent(/probe failed/i)
    expect(screen.getByLabelText("translation-probe-result")).toHaveTextContent(/DeepL Translator probe completed successfully./i)
    expect(screen.getByLabelText("speech-probe-result")).toHaveTextContent(/Azure Speech probe failed./i)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("DeepL Translator probe completed successfully.")
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("Azure Speech probe failed.")
    expect(screen.queryByLabelText("api-status-list")).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /status/i }))
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent("DeepL API")
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent("Azure Speech API")
  })

  it("deletes complete db from developer options", async () => {
    const user = userEvent.setup()
    const resetMethods: Array<string | undefined> = []
    vi.spyOn(window, "confirm").mockReturnValue(true)
    mockFetchImplementation({
      resetDbHandler: async (_input, init) => {
        resetMethods.push(init?.method)
        return responseOf({ status: "reset", message: "Database reset complete." })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await openDeveloperSection(user)
    await user.click(screen.getByRole("tab", { name: /database/i }))
    fireEvent.click(await screen.findByRole("button", { name: /delete db \+ clear cache/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(resetMethods).toEqual(["DELETE"])
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Database reset complete.")
  })

  it("shows only the active developer tab content", async () => {
    const user = userEvent.setup()

    mockFetchImplementation({
      healthResponse: {
        status: "ok",
        service: "backend",
        apis: {
          backend: { status: "ok", active: true, configured: true },
          azure_translator: { status: "ok", active: true, configured: true },
          azure_speech: { status: "ok", active: true, configured: true },
          gemini: { status: "inactive", active: false, configured: false, message: "Not checked yet." },
        },
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    await openDeveloperSection(user)

    expect(screen.getByLabelText("api-status-list")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /apply runtime api keys/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /test gemini/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /delete db \+ clear cache/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /api keys/i }))
    expect(await screen.findByRole("button", { name: /apply runtime api keys/i })).toBeInTheDocument()
    expect(screen.queryByLabelText("api-status-list")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /test gemini/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /delete db \+ clear cache/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /probes/i }))
    expect(await screen.findByRole("button", { name: /test gemini/i })).toBeInTheDocument()
    expect(screen.queryByLabelText("api-status-list")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /apply runtime api keys/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /delete db \+ clear cache/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole("tab", { name: /database/i }))
    expect(await screen.findByRole("button", { name: /delete db \+ clear cache/i })).toBeInTheDocument()
    expect(screen.queryByLabelText("api-status-list")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /apply runtime api keys/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /test gemini/i })).not.toBeInTheDocument()
  })

  it("invalidates cached COR search translations after runtime API key updates", async () => {
    const user = userEvent.setup()
    let useUpdatedSearchTranslations = false
    const corSearchFormHandler = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost")
      const includeTranslations = url.searchParams.get("include_translations") !== "false"
      const partialPayload = {
        form: "bil",
        groups: [
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
      }
      const staleFullPayload = {
        form: "bil",
        groups: [
          {
            lemma: "bile",
            gloss: "køre i bil",
            pos_tag: "VERB",
            variants: [
              {
                ...partialPayload.groups[0].variants[0],
                gloss_translation: "go by car",
                lemma_translation: null,
                saveable_translation: null,
                lemma_translation_status: "missing",
                lemma_translation_reason: "gemini_missing",
              },
            ],
          },
        ],
      }
      const updatedFullPayload = {
        form: "bil",
        groups: [
          {
            lemma: "bile",
            gloss: "køre i bil",
            pos_tag: "VERB",
            variants: [
              {
                ...partialPayload.groups[0].variants[0],
                gloss_translation: "go by car",
                lemma_translation: "to drive",
                saveable_translation: "to drive",
                lemma_translation_provider: "gemini_word_translation",
                lemma_translation_status: "gemini",
                lemma_translation_reason: "gemini_ok",
              },
            ],
          },
        ],
      }

      if (!includeTranslations) {
        return responseOf(partialPayload)
      }
      return responseOf(useUpdatedSearchTranslations ? updatedFullPayload : staleFullPayload)
    })

    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: { items: [] },
      corSearchFormHandler,
      developerApiKeysHandler: async () => {
        useUpdatedSearchTranslations = true
        return responseOf({
          status: "updated",
          message: "Runtime API keys updated.",
          configured: {},
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    let commandDialog = await screen.findByRole("dialog")
    let searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    await user.type(searchInput, "bil")

    expect(await within(commandDialog).findByText(/translation required before saving\./i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/\(to drive\)/i)).not.toBeInTheDocument()

    fireEvent.keyDown(commandDialog, { key: "Escape" })
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250))
    })

    await openDeveloperSection(user)
    await user.click(screen.getByRole("tab", { name: /api keys/i }))
    fireEvent.change(await screen.findByLabelText(/gemini api key/i), { target: { value: "updated-gemini-key" } })
    fireEvent.click(screen.getByRole("button", { name: /apply runtime api keys/i }))

    await waitFor(() => {
      expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Runtime API keys updated.")
    })
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250))
    })

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    commandDialog = await screen.findByRole("dialog")
    searchInput = within(commandDialog).getByPlaceholderText(/search words/i)
    await user.clear(searchInput)
    await user.type(searchInput, "bil")

    expect(await within(commandDialog).findByText(/to drive \(go by car\)/i)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/translation required before saving\./i)).not.toBeInTheDocument()

    const bilFetchCalls = corSearchFormHandler.mock.calls.filter(([input]) => {
      const url = new URL(String(input), "http://localhost")
      return url.pathname === "/api/wordbank/search/cor-form" && url.searchParams.get("form") === "bil"
    })
    expect(bilFetchCalls).toHaveLength(4)
  })

})
