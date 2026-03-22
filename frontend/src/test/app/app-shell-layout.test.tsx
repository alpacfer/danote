import { mockFetchImplementation, renderApp, screen } from "@/test/app-test-helpers"

describe("App shell layout normalization", () => {
  it("uses the shared shell gutter token on the main layout container", async () => {
    mockFetchImplementation()

    renderApp()
    const status = await screen.findByLabelText("backend-connection-status")

    const main = status.closest("main")
    expect(main).not.toBeNull()
    expect(main).toHaveClass("px-[var(--danote-shell-gutter-x)]")
    expect(main).toHaveClass("pt-[var(--danote-shell-gutter-y)]")
    expect(main).toHaveClass("pb-[var(--danote-shell-gutter-y-compact)]")
  })
})
