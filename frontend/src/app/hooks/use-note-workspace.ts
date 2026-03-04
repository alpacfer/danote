import { type MutableRefObject, type Dispatch, type SetStateAction, useState } from "react"

import {
  createSavedNoteId,
  type AnalyzedToken,
  type AppSection,
  type DiscoveredTokenMemory,
  type SaveDialogMode,
  type SavedNote,
} from "@/app/core"
import { toast } from "sonner"

type UseNoteWorkspaceParams = {
  noteText: string
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  savedNotes: SavedNote[]
  setSavedNotes: Dispatch<SetStateAction<SavedNote[]>>
  activeSavedNote: SavedNote | null
  setActiveNoteId: (value: string | null) => void
  setAutosaveStatus: (value: "off" | "saving" | "saved") => void
  noteAutosaveTimeoutRef: MutableRefObject<number | null>
  setNoteText: (value: string) => void
  setTokens: (value: AnalyzedToken[]) => void
  setDiscoveredTokenMetadata: (value: Record<string, DiscoveredTokenMemory>) => void
  setGeneratedTranslationMap: (value: Record<string, string | null>) => void
  setAnalysisError: (value: string | null) => void
  clearPlaygroundTransientState: () => void
  setActiveSection: (value: AppSection) => void
  pushNotification: (message: string) => void
}

export function useNoteWorkspace({
  noteText,
  tokens,
  discoveredTokenMetadata,
  generatedTranslationMap,
  savedNotes,
  setSavedNotes,
  activeSavedNote,
  setActiveNoteId,
  setAutosaveStatus,
  noteAutosaveTimeoutRef,
  setNoteText,
  setTokens,
  setDiscoveredTokenMetadata,
  setGeneratedTranslationMap,
  setAnalysisError,
  clearPlaygroundTransientState,
  setActiveSection,
  pushNotification,
}: UseNoteWorkspaceParams) {
  const [isSaveDialogOpen, setIsSaveDialogOpen] = useState(false)
  const [saveDialogMode, setSaveDialogMode] = useState<SaveDialogMode>("initial")
  const [noteNameDraft, setNoteNameDraft] = useState("")
  const [duplicateNameConflictNoteId, setDuplicateNameConflictNoteId] = useState<string | null>(null)

  function findDuplicateNameNoteId(name: string, excludedNoteId: string | null): string | null {
    const normalized = name.trim().toLocaleLowerCase()
    if (!normalized) {
      return null
    }
    const duplicate = savedNotes.find(
      (note) => note.id !== excludedNoteId && note.name.trim().toLocaleLowerCase() === normalized,
    )
    return duplicate?.id ?? null
  }

  function clearAutosaveTimeout() {
    if (noteAutosaveTimeoutRef.current !== null) {
      window.clearTimeout(noteAutosaveTimeoutRef.current)
      noteAutosaveTimeoutRef.current = null
    }
  }

  function openSaveDialog() {
    setSaveDialogMode(activeSavedNote ? "create_new" : "initial")
    setNoteNameDraft(`Note ${savedNotes.length + 1}`)
    setDuplicateNameConflictNoteId(null)
    setIsSaveDialogOpen(true)
  }

  function saveCurrentNote(
    name: string,
    options?: {
      forceNew?: boolean
      forcedNoteId?: string
      silent?: boolean
    },
  ) {
    if (!name) {
      toast.error("Note name is required.")
      return
    }

    const forceNew = options?.forceNew ?? false
    const excludedNoteId = forceNew ? null : (options?.forcedNoteId ?? activeSavedNote?.id ?? null)
    const duplicateNameNoteId = findDuplicateNameNoteId(name, excludedNoteId)
    if (duplicateNameNoteId) {
      setDuplicateNameConflictNoteId(duplicateNameNoteId)
      return
    }

    const savedAt = new Date().toISOString()
    const noteId = options?.forcedNoteId ?? (forceNew ? undefined : activeSavedNote?.id) ?? createSavedNoteId()
    const nextNote: SavedNote = {
      id: noteId,
      name,
      text: noteText,
      tokens: [...tokens],
      discoveredTokenMetadata: { ...discoveredTokenMetadata },
      generatedTranslationMap: { ...generatedTranslationMap },
      savedAt,
    }

    setSavedNotes((current) => {
      const existingIndex = current.findIndex((note) => note.id === noteId)
      if (existingIndex === -1) {
        return [nextNote, ...current]
      }
      const next = [...current]
      next[existingIndex] = nextNote
      return next
    })
    setActiveNoteId(noteId)
    setDuplicateNameConflictNoteId(null)
    setAutosaveStatus("saved")
    setIsSaveDialogOpen(false)
    if (!options?.silent) {
      toast.success("Note saved.")
      pushNotification(`Saved note: ${name}`)
    }
  }

  function saveActiveNoteSilently() {
    if (!activeSavedNote) {
      return
    }
    const savedAt = new Date().toISOString()
    const nextNote: SavedNote = {
      id: activeSavedNote.id,
      name: activeSavedNote.name,
      text: noteText,
      tokens: [...tokens],
      discoveredTokenMetadata: { ...discoveredTokenMetadata },
      generatedTranslationMap: { ...generatedTranslationMap },
      savedAt,
    }

    setSavedNotes((current) => {
      const existingIndex = current.findIndex((note) => note.id === nextNote.id)
      if (existingIndex === -1) {
        return [nextNote, ...current]
      }
      const next = [...current]
      next[existingIndex] = nextNote
      return next
    })
    setAutosaveStatus("saved")
  }

  function createNewNamedNote(name: string) {
    if (!name) {
      toast.error("Note name is required.")
      return
    }

    const duplicateNameNoteId = findDuplicateNameNoteId(name, null)
    if (duplicateNameNoteId) {
      setDuplicateNameConflictNoteId(duplicateNameNoteId)
      return
    }

    clearAutosaveTimeout()
    saveActiveNoteSilently()

    const noteId = createSavedNoteId()
    const nextNote: SavedNote = {
      id: noteId,
      name,
      text: "",
      tokens: [],
      discoveredTokenMetadata: {},
      generatedTranslationMap: {},
      savedAt: new Date().toISOString(),
    }

    setSavedNotes((current) => [nextNote, ...current])
    setActiveNoteId(noteId)
    setNoteText("")
    setTokens([])
    setDiscoveredTokenMetadata({})
    setGeneratedTranslationMap({})
    setAnalysisError(null)
    clearPlaygroundTransientState()
    setDuplicateNameConflictNoteId(null)
    setAutosaveStatus("saved")
    setIsSaveDialogOpen(false)
    toast.success("New note created.")
    pushNotification(`Created new note: ${name}`)
  }

  function openSavedNoteInPlayground(note: SavedNote) {
    setNoteText(note.text)
    setTokens(note.tokens)
    setDiscoveredTokenMetadata(note.discoveredTokenMetadata)
    setGeneratedTranslationMap(note.generatedTranslationMap)
    setAnalysisError(null)
    clearPlaygroundTransientState()
    setActiveNoteId(note.id)
    setAutosaveStatus("saved")
    setActiveSection("playground")
  }

  function openSavedNoteById(noteId: string) {
    const note = savedNotes.find((candidate) => candidate.id === noteId)
    if (!note) {
      return
    }
    openSavedNoteInPlayground(note)
  }

  function handleSaveDialogOpenChange(open: boolean) {
    setIsSaveDialogOpen(open)
    if (!open) {
      setDuplicateNameConflictNoteId(null)
    }
  }

  function handleNoteNameDraftChange(value: string) {
    setNoteNameDraft(value)
    setDuplicateNameConflictNoteId(null)
  }

  function handleSaveDialogSubmit() {
    const nextName = noteNameDraft.trim()
    if (saveDialogMode === "create_new") {
      createNewNamedNote(nextName)
      return
    }
    saveCurrentNote(nextName)
  }

  function resolveDuplicateNameConflict() {
    if (!duplicateNameConflictNoteId) {
      return
    }
    if (saveDialogMode === "create_new") {
      clearAutosaveTimeout()
      saveActiveNoteSilently()
      setActiveNoteId(duplicateNameConflictNoteId)
      setDuplicateNameConflictNoteId(null)
      setIsSaveDialogOpen(false)
      toast.success("Opened existing note for autosave.")
      return
    }
    saveCurrentNote(noteNameDraft.trim(), { forcedNoteId: duplicateNameConflictNoteId })
  }

  return {
    isSaveDialogOpen,
    saveDialogMode,
    noteNameDraft,
    duplicateNameConflictNoteId,
    openSaveDialog,
    handleSaveDialogOpenChange,
    handleNoteNameDraftChange,
    handleSaveDialogSubmit,
    resolveDuplicateNameConflict,
    openSavedNoteInPlayground,
    openSavedNoteById,
    saveActiveNoteSilently,
  }
}
