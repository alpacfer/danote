import { useEffect, useMemo, useRef, useState } from "react"

import {
  loadSavedNotes,
  persistSavedNotes,
  type SavedNote,
} from "@/app/core"

export function useNotesPersistence() {
  const [savedNotes, setSavedNotes] = useState<SavedNote[]>(() => loadSavedNotes())
  const [activeNoteId, setActiveNoteId] = useState<string | null>(null)
  const [autosaveStatus, setAutosaveStatus] = useState<"off" | "saving" | "saved">("off")

  const noteAutosaveTimeoutRef = useRef<number | null>(null)

  const activeSavedNote = useMemo(
    () => savedNotes.find((note) => note.id === activeNoteId) ?? null,
    [activeNoteId, savedNotes],
  )
  const activeSavedNoteId = activeSavedNote?.id ?? null
  const activeSavedNoteName = activeSavedNote?.name ?? null

  useEffect(() => {
    persistSavedNotes(savedNotes)
  }, [savedNotes])

  return {
    savedNotes,
    setSavedNotes,
    activeNoteId,
    setActiveNoteId,
    autosaveStatus,
    setAutosaveStatus,
    noteAutosaveTimeoutRef,
    activeSavedNote,
    activeSavedNoteId,
    activeSavedNoteName,
  }
}
