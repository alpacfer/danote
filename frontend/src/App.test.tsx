import { act, fireEvent, render, screen } from "@testing-library/react"
import { vi } from "vitest"
import { toast } from "sonner"

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import App from "./App"

afterEach(() => {
  vi.mocked(toast.success).mockReset()
  vi.mocked(toast.error).mockReset()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

type AnalyzeToken = {
  surface_token: string
  normalized_token: string
  lemma_candidate: string | null
  classification: "known" | "variation" | "new"
  match_source: "exact" | "lemma" | "none"
  matched_lemma: string | null
  matched_surface_form: string | null
}

function responseOf(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response
}

function mockFetchImplementation(options?: {
  healthOk?: boolean
  healthStatus?: "ok" | "degraded"
  analyzeOk?: boolean
  analyzeTokens?: AnalyzeToken[]
  analyzeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  addWordOk?: boolean
  addWordResponse?: {
    status: "inserted" | "exists"
    stored_lemma: string
    stored_surface_form: string | null
    source: "manual"
    message: string
  }
  addWordHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmasOk?: boolean
  lemmasResponse?: {
    items: Array<{
      lemma: string
      variation_count: number
    }>
  }
  lemmaDetailsOk?: boolean
  lemmaDetailsResponse?: {
    lemma: string
    surface_forms: string[]
  }
  resetDbOk?: boolean
  resetDbResponse?: {
    status: "reset"
    message: string
  }
  resetDbHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
}) {
  const healthOk = options?.healthOk ?? true
  const healthStatus = options?.healthStatus ?? "ok"
  const analyzeOk = options?.analyzeOk ?? true
  const analyzeTokens = options?.analyzeTokens ?? []
  const addWordOk = options?.addWordOk ?? true
  const addWordResponse = options?.addWordResponse ?? {
    status: "inserted" as const,
    stored_lemma: "kat",
    stored_surface_form: "kat",
    source: "manual" as const,
    message: "Added 'kat' to wordbank.",
  }
  const lemmasOk = options?.lemmasOk ?? true
  const lemmasResponse = options?.lemmasResponse ?? { items: [] }
  const lemmaDetailsOk = options?.lemmaDetailsOk ?? true
  const lemmaDetailsResponse = options?.lemmaDetailsResponse ?? { lemma: "bog", surface_forms: ["bogen"] }
  const resetDbOk = options?.resetDbOk ?? true
  const resetDbResponse = options?.resetDbResponse ?? { status: "reset" as const, message: "Database reset complete." }

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith("/api/health")) {
      if (!healthOk) {
        throw new Error("network down")
      }
      return responseOf({ status: healthStatus, service: "backend" })
    }

    if (url.endsWith("/api/analyze")) {
      if (options?.analyzeHandler) {
        return options.analyzeHandler(input, init)
      }
      if (!analyzeOk) {
        throw new Error("analyze request failed")
      }
      return responseOf({ tokens: analyzeTokens })
    }

    if (url.endsWith("/api/wordbank/lexemes")) {
      if (options?.addWordHandler) {
        return options.addWordHandler(input, init)
      }
      if (!addWordOk) {
        throw new Error("add word request failed")
      }
      return responseOf(addWordResponse)
    }

    if (url.endsWith("/api/wordbank/lemmas")) {
      if (!lemmasOk) {
        throw new Error("wordbank request failed")
      }
      return responseOf(lemmasResponse)
    }

    if (url.includes("/api/wordbank/lemmas/")) {
      if (!lemmaDetailsOk) {
        throw new Error("word details request failed")
      }
      return responseOf(lemmaDetailsResponse)
    }

    if (url.endsWith("/api/wordbank/database")) {
      if (options?.resetDbHandler) {
        return options.resetDbHandler(input, init)
      }
      if (!resetDbOk) {
        throw new Error("reset database request failed")
      }
      return responseOf(resetDbResponse)
    }

    return { ok: false, status: 404 } as Response
  })
}

describe("App shell", () => {
  it("renders header, cards, and backend status badge", async () => {
    mockFetchImplementation()

    render(<App />)

    expect(screen.getAllByText(/danote/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/detected words/i).length).toBeGreaterThan(0)
    expect(screen.getByPlaceholderText(/type lesson notes here.../i)).toBeInTheDocument()
    const statusBadge = await screen.findByLabelText("backend-connection-status")
    expect(statusBadge).toHaveTextContent(/connected/i)
  })

  it("renders sidebar navigation with playground and wordbank", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    expect(screen.getByRole("button", { name: /playground/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /wordbank/i })).toBeInTheDocument()
  })

  it("shows saved lemmas in wordbank and opens lemma details page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 2 },
          { lemma: "hus", variation_count: 1 },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        surface_forms: ["bogen", "bogens"],
      },
    })

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    const bogItem = await screen.findByRole("button", { name: /bog/i })
    expect(bogItem).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /hus/i })).toBeInTheDocument()

    fireEvent.click(bogItem)
    expect(await screen.findByRole("button", { name: /back to list/i })).toBeInTheDocument()
    expect(screen.getByText(/^bogen$/i)).toBeInTheDocument()
    expect(screen.getByText(/^bogens$/i)).toBeInTheDocument()
  })

  it("shows notes and detected words in one page", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByText(/connected/i)

    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/detected words/i).length).toBeGreaterThan(0)
  })

  it("renders offline status when health check fails", async () => {
    mockFetchImplementation({ healthOk: false })

    render(<App />)

    expect(await screen.findByText(/offline/i)).toBeInTheDocument()
  })

  it("renders degraded status when backend health is degraded", async () => {
    mockFetchImplementation({ healthStatus: "degraded" })

    render(<App />)

    expect(await screen.findByText(/degraded/i)).toBeInTheDocument()
  })

  it("textarea accepts typing and paste", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    const textarea = screen.getByPlaceholderText(/type lesson notes here.../i)
    fireEvent.change(textarea, { target: { value: "Jeg kan godt lide bogen" } })
    expect(textarea).toHaveValue("Jeg kan godt lide bogen")

    fireEvent.paste(textarea, {
      clipboardData: {
        getData: () => "linje 1\nlinje 2",
      },
    })
    fireEvent.change(textarea, { target: { value: "linje 1\nlinje 2" } })
    expect(textarea).toHaveValue("linje 1\nlinje 2")
  })

  it("renders detected words table headers", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    expect(screen.getByText(/^token$/i)).toBeInTheDocument()
    expect(screen.getByText(/^lemma$/i)).toBeInTheDocument()
    expect(screen.getByText(/^status$/i)).toBeInTheDocument()
  })

  it("debounce collapses rapid typing into one analyze call", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({ tokens: [] })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    const textarea = screen.getByPlaceholderText(/type lesson notes here.../i)
    fireEvent.change(textarea, { target: { value: "Jeg" } })
    fireEvent.change(textarea, { target: { value: "Jeg kan" } })
    fireEvent.change(textarea, { target: { value: "Jeg kan godt lide bogen " } })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    expect(analyzeBodies).toHaveLength(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
      await Promise.resolve()
    })
    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "Jeg kan godt lide bogen" }))
  })

  it("does not analyze unfinished trailing token until finalization", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({
          tokens: [
            {
              surface_token: "bogen",
              normalized_token: "bogen",
              lemma_candidate: "bog",
              classification: "variation",
              match_source: "lemma",
              matched_lemma: "bog",
              matched_surface_form: null,
            },
          ],
        })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")
    const textarea = screen.getByPlaceholderText(/type lesson notes here.../i)

    fireEvent.change(textarea, { target: { value: "b" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    fireEvent.change(textarea, { target: { value: "bo" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    fireEvent.change(textarea, { target: { value: "boge" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    fireEvent.change(textarea, { target: { value: "bogen" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(analyzeBodies).toHaveLength(0)

    fireEvent.change(textarea, { target: { value: "bogen " } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "bogen" }))

    expect(screen.getAllByText(/^bogen$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("stale responses do not overwrite newer results", async () => {
    vi.useFakeTimers()
    const resolvers: Array<(value: Response) => void> = []

    mockFetchImplementation({
      analyzeHandler: () =>
        new Promise<Response>((resolve) => {
          resolvers.push(resolve)
        }),
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    const textarea = screen.getByPlaceholderText(/type lesson notes here.../i)
    fireEvent.change(textarea, { target: { value: "første " } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    fireEvent.change(textarea, { target: { value: "anden " } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(resolvers).toHaveLength(2)

    await act(async () => {
      resolvers[1](
        responseOf({
          tokens: [
            {
              surface_token: "anden",
              normalized_token: "anden",
              lemma_candidate: "anden",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)

    await act(async () => {
      resolvers[0](
        responseOf({
          tokens: [
            {
              surface_token: "første",
              normalized_token: "første",
              lemma_candidate: "første",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.queryByText(/^første$/i)).not.toBeInTheDocument()
    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("renders detected rows and status mapping on success", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "bogen",
          normalized_token: "bogen",
          lemma_candidate: "bog",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "bog",
          matched_surface_form: null,
        },
        {
          surface_token: "kat",
          normalized_token: "kat",
          lemma_candidate: "kat",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    fireEvent.change(screen.getByPlaceholderText(/type lesson notes here.../i), {
      target: { value: "Jeg kan godt lide bogen " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(screen.getAllByText(/^kan$/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/^bogen$/i)).toBeInTheDocument()
    expect(screen.getAllByText(/^kat$/i).length).toBeGreaterThanOrEqual(1)

    expect(screen.getAllByText(/^known$/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/^variation$/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/^new$/i).length).toBeGreaterThanOrEqual(1)

    expect(screen.getByText(/^exact$/i)).toBeInTheDocument()
    expect(screen.getByText(/^lemma$/)).toBeInTheDocument()
    expect(screen.getByText(/^none$/i)).toBeInTheDocument()
  })

  it("shows Add action only for new rows", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "kat",
          normalized_token: "kat",
          lemma_candidate: "kat",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    fireEvent.change(screen.getByPlaceholderText(/type lesson notes here.../i), {
      target: { value: "kan kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(screen.getAllByRole("button", { name: /^add$/i })).toHaveLength(1)
  })

  it("clicking Add calls backend, re-analyzes, and shows success toast", async () => {
    vi.useFakeTimers()
    let analyzeCallCount = 0
    const addBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async () => {
        analyzeCallCount += 1
        if (analyzeCallCount === 1) {
          return responseOf({
            tokens: [
              {
                surface_token: "kat",
                normalized_token: "kat",
                lemma_candidate: "kat",
                classification: "new",
                match_source: "none",
                matched_lemma: null,
                matched_surface_form: null,
              },
            ],
          })
        }
        return responseOf({
          tokens: [
            {
              surface_token: "kat",
              normalized_token: "kat",
              lemma_candidate: "kat",
              classification: "known",
              match_source: "exact",
              matched_lemma: "kat",
              matched_surface_form: "kat",
            },
          ],
        })
      },
      addWordHandler: async (_input, init) => {
        addBodies.push(String(init?.body ?? ""))
        return responseOf({
          status: "inserted",
          stored_lemma: "kat",
          stored_surface_form: "kat",
          source: "manual",
          message: "Added 'kat' to wordbank.",
        })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    fireEvent.change(screen.getByPlaceholderText(/type lesson notes here.../i), {
      target: { value: "kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    fireEvent.click(screen.getByRole("button", { name: /^add$/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(addBodies).toHaveLength(1)
    expect(addBodies[0]).toBe(JSON.stringify({ surface_token: "kat", lemma_candidate: "kat" }))
    expect(vi.mocked(toast.success)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Added 'kat' to wordbank.")
    expect(analyzeCallCount).toBeGreaterThanOrEqual(2)
  })

  it("shows error toast when Add fails", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kat",
          normalized_token: "kat",
          lemma_candidate: "kat",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      addWordOk: false,
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    fireEvent.change(screen.getByPlaceholderText(/type lesson notes here.../i), {
      target: { value: "kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    fireEvent.click(screen.getByRole("button", { name: /^add$/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("add word request failed")
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

    render(<App />)
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

  it("renders loading and error states", async () => {
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

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    const textarea = screen.getByPlaceholderText(/type lesson notes here.../i)

    fireEvent.change(textarea, {
      target: { value: "test " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(screen.getByText(/loading detected words/i)).toBeInTheDocument()

    fail = true
    const notesTextarea = screen.getByPlaceholderText(/type lesson notes here.../i)
    fireEvent.change(notesTextarea, {
      target: { value: "test2 " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByRole("alert")).toHaveTextContent(/backend unavailable/i)
  })
})
