import { act, fireEvent, mockFetchImplementation, renderApp, responseOf, screen, setNotesEditorText, toast, vi } from "@/test/app-test-helpers"

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

  it("shows NLP model picker in developer options", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))

    const modelPicker = screen.getByRole("combobox", { name: /nlp model picker/i })
    expect(modelPicker).toBeInTheDocument()
    expect(modelPicker).toHaveTextContent("da_dacy_small_trf-0.2.0")

    expect(screen.getByText(/backend default remains/i)).toBeInTheDocument()
    expect(screen.getByLabelText("api-status-list")).toBeInTheDocument()
    expect(screen.getByText("Backend API")).toBeInTheDocument()
    expect(screen.getByText("Azure Translator API")).toBeInTheDocument()
    expect(screen.getByText("Azure Speech API")).toBeInTheDocument()
  })

  it("tests Gemini from developer options and shows inline result", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))
    fireEvent.click(screen.getByRole("button", { name: /test gemini/i }))

    expect(await screen.findByLabelText("gemini-probe-result")).toHaveTextContent(/the book/i)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Gemini probe completed successfully.")
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/gemini/i)
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/^ok$|ok/i)
  })

  it("tests DeepL and Speech from developer options and updates API status", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))
    fireEvent.click(screen.getByRole("button", { name: /test deepl/i }))
    fireEvent.click(screen.getByRole("button", { name: /test azure speech/i }))

    expect(await screen.findByLabelText("translation-probe-result")).toHaveTextContent(/the book/i)
    expect(await screen.findByLabelText("speech-probe-result")).toHaveTextContent(/probe failed/i)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("DeepL Translator probe completed successfully.")
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("Azure Speech probe failed.")
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent("DeepL API")
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent("Azure Speech API")
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/DeepL Translator probe completed successfully./i)
    expect(screen.getByLabelText("api-status-list")).toHaveTextContent(/Azure Speech probe failed./i)
  })

  it("deletes complete db from developer options", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))
    fireEvent.click(screen.getByRole("button", { name: /delete complete db/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(resetMethods).toEqual(["DELETE"])
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Database reset complete.")
  })

  it("renders analysis error state", async () => {
    vi.useFakeTimers()
    let fail = false

    mockFetchImplementation({
      analyzeHandler: async () => {
        if (fail) {
          throw new Error("backend unavailable")
        }
        return new Promise<Response>(() => {})
      },
    })

    renderApp()
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("test ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()

    fail = true
    setNotesEditorText("test2 ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByRole("alert")).toHaveTextContent(/backend unavailable/i)
  })
})
