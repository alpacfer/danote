import { TextSelection } from "@tiptap/pm/state"
import type { EditorView } from "@tiptap/pm/view"

export type NotesEditorHighlightClickPayload = {
  tokenIndex: number
  left: number
  lineTop: number
  lineBottom: number
}

export function handleHighlightMarkClick(params: {
  view: EditorView
  event: MouseEvent
  onHighlightClick?: (payload: NotesEditorHighlightClickPayload) => void
}): boolean {
  const { view, event, onHighlightClick } = params
  const eventTarget = event.target
  const targetElement =
    eventTarget instanceof Element ? eventTarget : eventTarget instanceof Node ? eventTarget.parentElement : null
  const mark = targetElement?.closest("mark.clickable-word[data-token-index]")
  if (!mark) {
    return false
  }

  const tokenIndexValue = mark.getAttribute("data-token-index")
  const tokenIndex = Number.parseInt(tokenIndexValue ?? "", 10)
  if (Number.isNaN(tokenIndex)) {
    return false
  }

  const root = view.root as Document | ShadowRoot
  const clickPosition =
    "elementFromPoint" in root && typeof root.elementFromPoint === "function"
      ? view.posAtCoords({ left: event.clientX, top: event.clientY })
      : null

  if (clickPosition) {
    view.dispatch(view.state.tr.setSelection(TextSelection.create(view.state.doc, clickPosition.pos)))
  }
  view.focus()

  const markRect = mark.getBoundingClientRect()
  onHighlightClick?.({
    tokenIndex,
    left: markRect.left,
    lineTop: markRect.top,
    lineBottom: markRect.bottom,
  })
  return false
}
