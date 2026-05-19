import { fireEvent, render, screen } from "@testing-library/react"
import { type ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

import App from "@/App"
import { AccountSection } from "@/app/sections/account-section"

const authState = vi.hoisted(() => ({
  isLoaded: true,
  isSignedIn: false,
}))

vi.mock("@clerk/react", () => ({
  SignInButton: ({ children }: { children: ReactNode }) => <>{children}</>,
  SignOutButton: ({ children }: { children: ReactNode }) => <>{children}</>,
  UserButton: () => <button type="button">User menu</button>,
  useAuth: () => ({
    getToken: async () => "clerk-token",
    isLoaded: authState.isLoaded,
    isSignedIn: authState.isSignedIn,
  }),
  useUser: () => ({
    isLoaded: true,
    user: { primaryEmailAddress: { emailAddress: "user@example.com" } },
  }),
}))

vi.mock("@/app/chrome", () => ({
  AppSidebar: () => <aside>Sidebar</aside>,
}))

vi.mock("@/app/layout/section-content", () => ({
  SectionContent: () => <div>APP SHELL</div>,
}))

vi.mock("@/app/sections/sentencebank/generated-example-dialog", () => ({
  GeneratedExampleDialog: () => null,
}))

vi.mock("@/app/hooks/app/use-app-controller", () => ({
  useAppController: () => ({
    activeSection: "wordbank",
    status: "ok",
    lemmas: [],
    sentences: [],
    wordbankRefreshTick: 0,
    searchTranslationConfigVersion: 0,
    unreadWordbankNotificationCount: 0,
    selectWordbank: vi.fn(),
    selectSentencebank: vi.fn(),
    selectDeveloper: vi.fn(),
    selectAccount: vi.fn(),
    openWordbankLemma: vi.fn(),
    openWordbankLemmaRaw: vi.fn(),
    openWordbankMeaning: vi.fn(),
    openSentence: vi.fn(),
    addSentenceToSentencebank: vi.fn(),
    addWordFromSearch: vi.fn(),
    sectionProps: {
      wordbankSectionProps: {},
      sentencebankSectionProps: {},
      developerSectionProps: {},
    },
    generatedExamplePreview: null,
    isGeneratingExample: false,
    isSavingGeneratedExample: false,
    saveGeneratedExample: vi.fn(),
    regenerateExample: vi.fn(),
    discardGeneratedExample: vi.fn(),
  }),
}))

function ok(payload: unknown): Response {
  return { ok: true, status: 200, json: async () => payload } as Response
}

function guestStatus() {
  return {
    keys_configured: false,
    providers: {},
    missing: ["gemini", "deepl", "azure_translation", "azure_tts"],
    trial: {
      enabled: true,
      available: true,
      opted_in: true,
      keys_configured: false,
      limit: 20,
      used: 3,
      remaining: 17,
      resets_on: "2026-05-20",
    },
  }
}

describe("guest login", () => {
  it("starts a guest session from the signed-out screen and renders the app shell", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes("/api/guest/sessions")) {
        return ok({ token: "guest_test-token", auth_provider: "guest", trial: guestStatus().trial })
      }
      return ok({})
    }) as unknown as typeof fetch

    render(<App requiresAuth />)

    fireEvent.click(await screen.findByRole("button", { name: /continue as guest/i }))

    expect(await screen.findByText("APP SHELL")).toBeInTheDocument()
    expect(window.localStorage.getItem("danote.guest.browser-id.v1")).toBeTruthy()
    expect(window.sessionStorage.getItem("danote.guest.session-token.v1")).toBe("guest_test-token")
  })

  it("shows guest account state without the API-key form", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes("/api/account/me")) {
        return ok({
          id: 2,
          email: null,
          display_name: "Guest",
          auth_provider: "guest",
        })
      }
      if (url.includes("/api/account/status")) {
        return ok(guestStatus())
      }
      return ok({})
    }) as unknown as typeof fetch

    render(<AccountSection />)

    expect(await screen.findAllByText(/guest mode/i)).toHaveLength(2)
    expect(await screen.findByText(/17 of 20 searches remaining/i)).toBeInTheDocument()
    expect(screen.queryByText(/api keys/i)).not.toBeInTheDocument()
  })
})
