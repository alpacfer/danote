import { SAVED_NOTES_STORAGE_KEY } from "@/app/core/constants"
import { type SavedNote } from "@/app/core/types-ui"

export function loadSavedNotes(): SavedNote[] {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const raw = window.localStorage.getItem(SAVED_NOTES_STORAGE_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter((item): item is SavedNote => {
      if (!item || typeof item !== "object") {
        return false
      }
      const candidate = item as Partial<SavedNote>
      return (
        typeof candidate.id === "string" &&
        typeof candidate.name === "string" &&
        typeof candidate.text === "string" &&
        typeof candidate.savedAt === "string" &&
        Array.isArray(candidate.tokens) &&
        candidate.discoveredTokenMetadata !== null &&
        typeof candidate.discoveredTokenMetadata === "object" &&
        candidate.generatedTranslationMap !== null &&
        typeof candidate.generatedTranslationMap === "object"
      )
    })
  } catch {
    return []
  }
}

export function persistSavedNotes(notes: SavedNote[]) {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.setItem(SAVED_NOTES_STORAGE_KEY, JSON.stringify(notes))
}

export function createSavedNoteId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `note-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function createNotificationId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  return `notification-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function formatSavedNoteTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}
