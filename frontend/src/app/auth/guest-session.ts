import { BACKEND_URL } from "@/app/core/constants"

const GUEST_BROWSER_ID_STORAGE_KEY = "danote.guest.browser-id.v1"
const GUEST_SESSION_TOKEN_STORAGE_KEY = "danote.guest.session-token.v1"

type GuestSessionResponse = {
  token: string
  auth_provider: "guest"
}

function storageAvailable(storage: Storage): boolean {
  try {
    const key = "danote.storage-probe"
    storage.setItem(key, "1")
    storage.removeItem(key)
    return true
  } catch {
    return false
  }
}

function createBrowserId(): string {
  if (crypto.randomUUID) {
    return crypto.randomUUID()
  }
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")
}

export function getOrCreateGuestBrowserId(): string {
  if (!storageAvailable(window.localStorage)) {
    return createBrowserId()
  }
  const existing = window.localStorage.getItem(GUEST_BROWSER_ID_STORAGE_KEY)
  if (existing) {
    return existing
  }
  const created = createBrowserId()
  window.localStorage.setItem(GUEST_BROWSER_ID_STORAGE_KEY, created)
  return created
}

export function getStoredGuestToken(): string | null {
  if (!storageAvailable(window.sessionStorage)) {
    return null
  }
  return window.sessionStorage.getItem(GUEST_SESSION_TOKEN_STORAGE_KEY)
}

export function storeGuestToken(token: string): void {
  if (!storageAvailable(window.sessionStorage)) {
    return
  }
  window.sessionStorage.setItem(GUEST_SESSION_TOKEN_STORAGE_KEY, token)
}

export function clearGuestToken(): void {
  if (!storageAvailable(window.sessionStorage)) {
    return
  }
  window.sessionStorage.removeItem(GUEST_SESSION_TOKEN_STORAGE_KEY)
}

export async function createGuestSession(): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/api/guest/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ browser_id: getOrCreateGuestBrowserId() }),
  })
  if (!response.ok) {
    throw new Error("Could not start guest mode.")
  }
  const payload = (await response.json()) as GuestSessionResponse
  storeGuestToken(payload.token)
  return payload.token
}
