import { act, fireEvent, render, screen, within } from "@testing-library/react"
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

    return { ok: false, status: 404 } as Response
  })
}

function switchToDetectedWordsTab() {
  const notesTab = screen.getByRole("tab", { name: /notes/i })
  const detectedWordsTab = screen.getByRole("tab", { name: /detected words/i })
  fireEvent.mouseDown(detectedWordsTab)
  fireEvent.click(detectedWordsTab)
  expect(detectedWordsTab).toHaveAttribute("aria-selected", "true")
  expect(notesTab).toHaveAttribute("aria-selected", "false")
}

describe("App shell", () => {
  it("renders header, tabs, and backend status badge", async () => {
    mockFetchImplementation()

    render(<App />)

    expect(screen.getByText(/danote/i)).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /notes/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /detected words/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/notes text/i)).toBeInTheDocument()
    const statusBadge = await screen.findByLabelText("backend-connection-status")
    expect(statusBadge).toHaveTextContent(/connected/i)
  })

  it("switches tabs correctly", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByText(/connected/i)

    const notesTab = screen.getByRole("tab", { name: /notes/i })
    const detectedWordsTab = screen.getByRole("tab", { name: /detected words/i })

    expect(notesTab).toHaveAttribute("aria-selected", "true")
    expect(detectedWordsTab).toHaveAttribute("aria-selected", "false")

    fireEvent.mouseDown(detectedWordsTab)
    fireEvent.click(detectedWordsTab)

    expect(detectedWordsTab).toHaveAttribute("aria-selected", "true")
    expect(notesTab).toHaveAttribute("aria-selected", "false")
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

    const textarea = screen.getByLabelText(/notes text/i)
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

  it("renders legend badges", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    expect(screen.getByText(/^known$/i)).toBeInTheDocument()
    expect(screen.getByText(/^variation$/i)).toBeInTheDocument()
    expect(screen.getByText(/^new$/i)).toBeInTheDocument()
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

    const textarea = screen.getByLabelText(/notes text/i)
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
    const textarea = screen.getByLabelText(/notes text/i)

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

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")
    expect(within(panel).getByText(/^bogen$/i)).toBeInTheDocument()
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

    const textarea = screen.getByLabelText(/notes text/i)
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

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")
    expect(within(panel).getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)

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

    expect(within(panel).queryByText(/^første$/i)).not.toBeInTheDocument()
    expect(within(panel).getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)
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

    fireEvent.change(screen.getByLabelText(/notes text/i), {
      target: { value: "Jeg kan godt lide bogen " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")

    expect((within(panel).getAllByText(/^kan$/i)).length).toBeGreaterThanOrEqual(1)
    expect(within(panel).getByText(/^bogen$/i)).toBeInTheDocument()
    expect((within(panel).getAllByText(/^kat$/i)).length).toBeGreaterThanOrEqual(1)

    expect(within(panel).getByText(/^known$/i)).toBeInTheDocument()
    expect(within(panel).getByText(/^variation$/i)).toBeInTheDocument()
    expect(within(panel).getByText(/^new$/i)).toBeInTheDocument()

    expect(within(panel).getByText(/^exact$/i)).toBeInTheDocument()
    expect(within(panel).getByText(/^lemma$/)).toBeInTheDocument()
    expect(within(panel).getByText(/^none$/i)).toBeInTheDocument()
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

    fireEvent.change(screen.getByLabelText(/notes text/i), {
      target: { value: "kan kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")
    expect(within(panel).getAllByRole("button", { name: /^add$/i })).toHaveLength(1)
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

    fireEvent.change(screen.getByLabelText(/notes text/i), {
      target: { value: "kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")
    fireEvent.click(within(panel).getByRole("button", { name: /^add$/i }))

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

    fireEvent.change(screen.getByLabelText(/notes text/i), {
      target: { value: "kat " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    switchToDetectedWordsTab()
    const panel = screen.getByRole("tabpanel")
    fireEvent.click(within(panel).getByRole("button", { name: /^add$/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("add word request failed")
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

    const textarea = screen.getByLabelText(/notes text/i)

    fireEvent.change(textarea, {
      target: { value: "test " },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    switchToDetectedWordsTab()
    expect(screen.getByText(/loading detected words/i)).toBeInTheDocument()

    fail = true
    fireEvent.mouseDown(screen.getByRole("tab", { name: /notes/i }))
    fireEvent.click(screen.getByRole("tab", { name: /notes/i }))
    const notesTextarea = screen.getByLabelText(/notes text/i)
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
