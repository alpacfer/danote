import { type Dispatch, type MutableRefObject, type SetStateAction, useEffect } from "react"

import {
  NOTE_AUTOSAVE_DEBOUNCE_MS,
  type AnalyzedToken,
  type DiscoveredTokenMemory,
  type SavedNote,
} from "@/app/core"

type UseNoteAutosaveParams = {
  activeSavedNoteId: string | null
  activeSavedNoteName: string | null
  noteText: string
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  noteAutosaveTimeoutRef: MutableRefObject<number | null>
  setAutosaveStatus: (value: "off" | "saving" | "saved") => void
  setSavedNotes: Dispatch<SetStateAction<SavedNote[]>>
}

export function useNoteAutosave({
  activeSavedNoteId,
  activeSavedNoteName,
  noteText,
  tokens,
  discoveredTokenMetadata,
  generatedTranslationMap,
  noteAutosaveTimeoutRef,
  setAutosaveStatus,
  setSavedNotes,
}: UseNoteAutosaveParams) {
  useEffect(() => {
    if (!activeSavedNoteId || !activeSavedNoteName) {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
      setAutosaveStatus("off")
      return
    }

    setAutosaveStatus("saving")
    if (noteAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(noteAutosaveTimeoutRef.current)
    }
    noteAutosaveTimeoutRef.current = window.setTimeout(() => {
      noteAutosaveTimeoutRef.current = null
      const savedAt = new Date().toISOString()
      const nextNote: SavedNote = {
        id: activeSavedNoteId,
        name: activeSavedNoteName,
        text: noteText,
        tokens: [...tokens],
        discoveredTokenMetadata: { ...discoveredTokenMetadata },
        generatedTranslationMap: { ...generatedTranslationMap },
        savedAt,
      }

      setSavedNotes((current) => {
        const existingIndex = current.findIndex((note) => note.id === activeSavedNoteId)
        if (existingIndex === -1) {
          return [nextNote, ...current]
        }
        const next = [...current]
        next[existingIndex] = nextNote
        return next
      })
      setAutosaveStatus("saved")
    }, NOTE_AUTOSAVE_DEBOUNCE_MS)

    return () => {
      if (noteAutosaveTimeoutRef.current !== null) {
        window.clearTimeout(noteAutosaveTimeoutRef.current)
        noteAutosaveTimeoutRef.current = null
      }
    }
  }, [
    activeSavedNoteId,
    activeSavedNoteName,
    discoveredTokenMetadata,
    generatedTranslationMap,
    noteText,
    noteAutosaveTimeoutRef,
    setAutosaveStatus,
    setSavedNotes,
    tokens,
  ])
}
