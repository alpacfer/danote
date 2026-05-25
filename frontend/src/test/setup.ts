import "@testing-library/jest-dom/vitest"
import { configure } from "@testing-library/dom"
import { toast } from "sonner"
import { afterEach, vi } from "vitest"

configure({ asyncUtilTimeout: 5000 })

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

afterEach(() => {
  vi.mocked(toast.success).mockReset()
  vi.mocked(toast.error).mockReset()
  vi.useRealTimers()
  vi.restoreAllMocks()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, "ResizeObserver", {
  writable: true,
  value: ResizeObserverMock,
})

class AudioMock {
  src = ""

  constructor(src?: string) {
    this.src = src ?? ""
  }

  play() {
    return Promise.resolve()
  }

  pause() {}
}

Object.defineProperty(globalThis, "Audio", {
  writable: true,
  value: AudioMock,
})

Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
  writable: true,
  value: () => {},
})
