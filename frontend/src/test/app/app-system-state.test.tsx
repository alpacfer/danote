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
