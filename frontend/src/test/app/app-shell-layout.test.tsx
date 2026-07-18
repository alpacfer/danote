import { afterEach } from "vitest"
import userEvent from "@testing-library/user-event"

import { MobileBottomNav } from "@/app/chrome/sidebar/mobile-bottom-nav"
import { ThemeToggleButton } from "@/app/chrome/theme-toggle-button"
import { ThemeProvider } from "@/components/theme-provider"
import { fireEvent, mockFetchImplementation, render, renderApp, screen, vi, waitFor, within } from "@/test/app-test-helpers"

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  })
}

afterEach(() => {
  setViewportWidth(1024)
  document.documentElement.classList.remove("dark", "light")
  window.localStorage.removeItem("theme")
})

describe("App shell layout normalization", () => {
  it("uses one shared ruled notebook sheet inside the main scroll viewport", async () => {
    mockFetchImplementation()

    renderApp()
    const status = await screen.findByLabelText("backend-connection-status")

    const main = status.closest("main")
    expect(main).not.toBeNull()
    const sheet = main?.querySelector("[data-notebook-sheet]")
    expect(sheet).toBeInTheDocument()
    expect(sheet).toHaveClass("danote-notebook-sheet")
    expect(sheet?.parentElement).toHaveClass("danote-notebook-viewport")
    expect(sheet?.querySelector("[data-notebook-content]")).toHaveClass("max-w-7xl")
    expect(main?.querySelectorAll("[data-notebook-sheet]")).toHaveLength(1)
  })

  it("keeps account access in the sidebar footer", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /open account/i }))

    expect(await screen.findByRole("heading", { name: /^account$/i })).toBeInTheDocument()
  })

  it("opens search from the mobile floating action button", async () => {
    setViewportWidth(390)
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const searchButton = await screen.findByRole("button", { name: /open search/i })
    fireEvent.click(searchButton)

    expect(await screen.findByRole("dialog")).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /open search/i })).not.toBeInTheDocument()
    })
  })

  it("closes search from the in-field cancel button", async () => {
    setViewportWidth(390)
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(await screen.findByRole("button", { name: /open search/i }))
    expect(await screen.findByRole("dialog")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /close search/i }))

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
    expect(await screen.findByRole("button", { name: /open search/i })).toBeInTheDocument()
  })

  it("navigates directly through the mobile bottom navigation menu", async () => {
    setViewportWidth(390)
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    // Verify the mobile bottom nav is displayed
    const bottomNav = screen.getByRole("button", { name: /sentences/i }).closest("[data-slot='mobile-bottom-nav']")
    expect(bottomNav).toBeInTheDocument()

    // Click on the Sentences button in the bottom nav
    fireEvent.click(screen.getByRole("button", { name: /sentences/i }))

    expect(await screen.findByText(/no saved sentences yet/i)).toBeInTheDocument()
  })

  it("keeps the mobile unread badge and active destination semantics", () => {
    const onSelectSentencebank = vi.fn()

    render(
      <MobileBottomNav
        activeSection="wordbank"
        onSelectWordbank={vi.fn()}
        onSelectSentencebank={onSelectSentencebank}
        onSelectAccount={vi.fn()}
        onOpenSearch={vi.fn()}
        unreadWordbankNotificationCount={3}
      />,
    )

    expect(screen.getByRole("button", { name: /wordbank/i })).toHaveAttribute("data-variant", "default")
    expect(screen.getByText("3")).toHaveAttribute("data-variant", "destructive")

    fireEvent.click(screen.getByRole("button", { name: /sentences/i }))
    expect(onSelectSentencebank).toHaveBeenCalledOnce()
  })

  it("keeps the binary theme toggle accessible while switching the root class", async () => {
    render(
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
        <ThemeToggleButton />
      </ThemeProvider>,
    )

    const darkButton = await screen.findByRole("button", { name: /switch to dark theme/i })
    fireEvent.click(darkButton)

    await waitFor(() => {
      expect(document.documentElement).toHaveClass("dark")
      expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeInTheDocument()
    })
  })

  it("removes account and hides developer from default command page results", async () => {
    const user = userEvent.setup()
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /^search$/i }))
    const commandDialog = await screen.findByRole("dialog")

    expect(within(commandDialog).getByText(/^Words$/)).toBeInTheDocument()
    expect(within(commandDialog).getByText(/^Sentences$/)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Developer$/)).not.toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Account$/)).not.toBeInTheDocument()

    await user.type(within(commandDialog).getByRole("textbox", { name: /command search/i }), "chochito")
    expect(await within(commandDialog).findByText(/^Developer$/)).toBeInTheDocument()
    expect(within(commandDialog).queryByText(/^Account$/)).not.toBeInTheDocument()
  })

  it("marks mobile shortcuts as hidden while keeping desktop shortcut affordances", async () => {
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const sidebarShortcut = screen.getByText("⌘").closest("[aria-hidden='true']")
    expect(sidebarShortcut).toHaveClass("hidden")
    expect(sidebarShortcut).toHaveClass("md:flex")

    fireEvent.click(screen.getByRole("button", { name: /^search$/i }))
    const commandDialog = await screen.findByRole("dialog")
    const pageShortcut = within(commandDialog).getAllByText("Alt")[0].closest("span")
    expect(pageShortcut).toHaveClass("hidden")
    expect(pageShortcut).toHaveClass("md:inline-flex")
  })
})
