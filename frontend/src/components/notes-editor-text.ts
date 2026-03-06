import type { JSONContent } from "@tiptap/core"
import type { Editor as TiptapEditor } from "@tiptap/react"

export function toEditorContent(text: string): JSONContent {
  const paragraphContent: JSONContent[] = []
  const lines = text.split("\n")

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    if (line.length > 0) {
      paragraphContent.push({ type: "text", text: line })
    }
    if (index < lines.length - 1) {
      paragraphContent.push({ type: "hardBreak" })
    }
  }

  return {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: paragraphContent.length > 0 ? paragraphContent : undefined,
      },
    ],
  }
}

export function fromEditorText(editor: TiptapEditor): string {
  return editor.getText({ blockSeparator: "\n" })
}

export function normalizeInputText(value: string): string {
  return value.replace(/\u00a0/gu, " ").replace(/\u200b/gu, "")
}

export type CharacterPositionMap = {
  charToPos: number[]
}

export function buildCharacterPositionMap(editor: TiptapEditor): CharacterPositionMap {
  const charToPos: number[] = []
  let offset = 0
  let seenTextBlock = false

  editor.state.doc.descendants((node, pos) => {
    if (node.isTextblock) {
      if (seenTextBlock) {
        // `getText({ blockSeparator: "\\n" })` inserts a newline between text blocks.
        offset += 1
      }
      seenTextBlock = true
      return
    }

    if (node.isText) {
      const textValue = node.text ?? ""
      const length = textValue.length
      for (let index = 0; index < length; index += 1) {
        charToPos[offset + index] = pos + index
      }
      offset += length
      return
    }

    if (node.type.name === "hardBreak") {
      offset += 1
    }
  })

  return { charToPos }
}

export function resolveRangeToPositions(
  positionMap: CharacterPositionMap,
  fromOffset: number,
  toOffset: number,
): { from: number; to: number } | null {
  if (toOffset <= fromOffset) {
    return null
  }

  const from = positionMap.charToPos[fromOffset]
  const endCharPos = positionMap.charToPos[toOffset - 1]
  if (typeof from !== "number" || typeof endCharPos !== "number") {
    return null
  }

  return { from, to: endCharPos + 1 }
}

export function commentRangesFromText(text: string): Array<{ from: number; to: number }> {
  if (!text || !text.includes("#")) {
    return []
  }

  const ranges: Array<{ from: number; to: number }> = []
  const lines = text.split("\n")
  let lineStartOffset = 0

  for (const line of lines) {
    const commentStart = line.indexOf("#")
    if (commentStart >= 0) {
      const from = lineStartOffset + commentStart
      const to = lineStartOffset + line.length
      if (to > from) {
        ranges.push({ from, to })
      }
    }
    lineStartOffset += line.length + 1
  }

  return ranges
}
