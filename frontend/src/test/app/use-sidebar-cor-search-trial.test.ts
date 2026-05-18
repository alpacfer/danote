import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiRequestError, SEARCH_RESOLVE_DEBOUNCE_MS } from "@/app/core"
import { useSidebarCorSearch } from "@/app/chrome/sidebar/use-sidebar-cor-search"
import {
  searchAttemptKey,
  type SidebarApiClient,
} from "@/app/chrome/sidebar/sidebar-search-types"

afterEach(() => {
  vi.useRealTimers()
})

function rejectingClient(): SidebarApiClient {
  const reject = () => Promise.reject(new ApiRequestError("trial limit", 429))
  return {
    tryGetJson: reject,
    getJson: reject,
    postJson: reject,
    putJson: reject,
    deleteJson: reject,
  } as unknown as SidebarApiClient
}

describe("useSidebarCorSearch trial limit", () => {
  it("reports the search attempt key when the backend returns 429", async () => {
    vi.useFakeTimers()
    const onTrialLimitReached = vi.fn()
    const resetVersion = "0:0"
    const normalizedQuery = "bilen"

    renderHook(() =>
      useSidebarCorSearch({
        apiClient: rejectingClient(),
        shouldSkipLookup: false,
        normalizedQuery,
        resetVersion,
        onTrialLimitReached,
      }),
    )

    await act(async () => {
      await vi.advanceTimersByTimeAsync(SEARCH_RESOLVE_DEBOUNCE_MS + 5)
    })

    expect(onTrialLimitReached).toHaveBeenCalledWith(
      searchAttemptKey(resetVersion, normalizedQuery),
    )
  })
})
