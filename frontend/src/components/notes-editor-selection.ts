import type { Editor as TiptapEditor } from "@tiptap/react"

export type NotesEditorSelectionPayload = {
  selectedText: string
  left: number
  lineTop: number
  lineBottom: number
}

export function clearSelectionTimeout(timeoutId: number | null): null {
  if (timeoutId !== null) {
    window.clearTimeout(timeoutId)
  }
  return null
}

export function scheduleSelectionSettled(params: {
  editor: TiptapEditor
  from: number
  to: number
  onTextSelectionSettled: (payload: NotesEditorSelectionPayload | null) => void
  onTimeoutConsumed: () => void
}): number {
  const { editor, from, to, onTextSelectionSettled, onTimeoutConsumed } = params
  return window.setTimeout(() => {
    onTimeoutConsumed()

    const activeSelection = editor.state.selection
    if (activeSelection.empty || activeSelection.from !== from || activeSelection.to !== to) {
      return
    }

    const selectedText = editor.state.doc.textBetween(from, to, " ", " ").replace(/\s+/gu, " ").trim()
    if (!selectedText) {
      onTextSelectionSettled(null)
      return
    }

    const fromCoords = editor.view.coordsAtPos(from)
    const toCoords = editor.view.coordsAtPos(to)

    onTextSelectionSettled({
      selectedText,
      left: Math.min(fromCoords.left, toCoords.left),
      lineTop: Math.min(fromCoords.top, toCoords.top),
      lineBottom: Math.max(fromCoords.bottom, toCoords.bottom),
    })
  }, 180)
}
