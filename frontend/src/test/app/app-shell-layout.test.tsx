import { afterEach } from "vitest"
import userEvent from "@testing-library/user-event"

import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  })
}

afterEach(() => {
  setViewportWidth(1024)
})

describe("App shell layout normalization", () => {
  it("uses the shared shell gutter token on the main layout container", async () => {
    mockFetchImplementation()

    renderApp()
    const status = await screen.findByLabelText("backend-connection-status")

    const main = status.closest("main")
    expect(main).not.toBeNull()
    expect(main).toHaveClass("px-[var(--danote-shell-gutter-x)]")
    expect(main).toHaveClass("pt-[var(--danote-shell-gutter-y)]")
    expect(main).toHaveClass("pb-[calc(5.5rem+env(safe-area-inset-bottom))]")
    expect(main).toHaveClass("md:pb-[var(--danote-shell-gutter-y-compact)]")
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
