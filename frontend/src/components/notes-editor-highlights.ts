import type { Editor as TiptapEditor } from "@tiptap/react"

import type { HighlightClassification, HighlightSpan } from "@/lib/token-highlights"

import {
  buildCharacterPositionMap,
  commentRangesFromText,
  fromEditorText,
  resolveRangeToPositions,
} from "@/components/notes-editor-text"

export type HighlightMarkAttributes = {
  color: string
  status: HighlightClassification | null
  tokenIndex: number | null
  comment: "true" | null
}

const HIGHLIGHT_COLOR_MAP: Record<HighlightClassification, string> = {
  known: "transparent",
  new: "var(--danote-highlight-new)",
  variation: "var(--danote-highlight-variation)",
  typo_likely: "transparent",
}

export function applyHighlights(editor: TiptapEditor, highlights: HighlightSpan[]) {
  const markType = editor.state.schema.marks.highlight
  if (!markType) {
    return
  }

  const { doc } = editor.state
  const positionMap = buildCharacterPositionMap(editor)
  let transaction = editor.state.tr

  doc.descendants((node, pos) => {
    if (!node.isText) {
      return
    }
    transaction = transaction.removeMark(pos, pos + node.nodeSize, markType)
  })

  for (const highlight of highlights) {
    const range = resolveRangeToPositions(positionMap, highlight.from, highlight.to)
    if (!range) {
      continue
    }
    const isInteractiveHighlight = highlight.classification !== "typo_likely"

    const attributes: HighlightMarkAttributes = {
      color: HIGHLIGHT_COLOR_MAP[highlight.classification],
      status: highlight.classification,
      tokenIndex: isInteractiveHighlight ? highlight.tokenIndex : null,
      comment: null,
    }

    transaction = transaction.addMark(range.from, range.to, markType.create(attributes))
  }

  const editorText = fromEditorText(editor)
  for (const commentRange of commentRangesFromText(editorText)) {
    const range = resolveRangeToPositions(positionMap, commentRange.from, commentRange.to)
    if (!range) {
      continue
    }

    const attributes: HighlightMarkAttributes = {
      color: "transparent",
      status: null,
      tokenIndex: null,
      comment: "true",
    }
    transaction = transaction.addMark(range.from, range.to, markType.create(attributes))
  }

  transaction = transaction.setMeta("addToHistory", false)
  editor.view.dispatch(transaction)
}
