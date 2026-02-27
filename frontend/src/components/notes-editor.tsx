import { useEditor, EditorContent, type Editor as TiptapEditor } from "@tiptap/react"
import type { JSONContent } from "@tiptap/core"
import Highlight from "@tiptap/extension-highlight"
import StarterKit from "@tiptap/starter-kit"
import { useEffect, useMemo, useRef } from "react"

import { cn } from "@/lib/utils"
import type { HighlightClassification, HighlightSpan } from "@/lib/token-highlights"

type NotesEditorProps = {
  value: string
  onChange: (next: string) => void
  placeholder: string
  highlights: HighlightSpan[]
  id?: string
  ariaLabel?: string
  className?: string
  onHighlightClick?: (payload: { tokenIndex: number; x: number; y: number }) => void
}

type HighlightMarkAttributes = {
  color: string
  status: HighlightClassification
  tokenIndex: number
}

const ClassificationHighlight = Highlight.extend({
  addAttributes() {
    return {
      ...(this.parent?.() ?? {}),
      status: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-status"),
        renderHTML: (attributes: { status?: string | null }) => {
          if (!attributes.status) {
            return {}
          }
          return {
            "data-status": attributes.status,
          }
        },
      },
      tokenIndex: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-token-index"),
        renderHTML: (attributes: { tokenIndex?: number | string | null }) => {
          if (attributes.tokenIndex === undefined || attributes.tokenIndex === null) {
            return {}
          }
          return {
            "data-token-index": String(attributes.tokenIndex),
            class: "clickable-word",
          }
        },
      },
    }
  },
})

const HIGHLIGHT_COLOR_MAP: Record<HighlightClassification, string> = {
  new: "var(--danote-highlight-new)",
  variation: "var(--danote-highlight-variation)",
  typo_likely: "var(--danote-highlight-typo)",
}

const TEST_MODE = import.meta.env.MODE === "test"

function toEditorContent(text: string): JSONContent {
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

function fromEditorText(editor: TiptapEditor): string {
  return editor.getText({ blockSeparator: "\n" })
}

function normalizeInputText(value: string): string {
  return value.replace(/\u00a0/gu, " ").replace(/\u200b/gu, "")
}

type CharacterPositionMap = {
  charToPos: number[]
}

function buildCharacterPositionMap(editor: TiptapEditor): CharacterPositionMap {
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

function resolveRangeToPositions(
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

function applyHighlights(editor: TiptapEditor, highlights: HighlightSpan[]) {
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

    const attributes: HighlightMarkAttributes = {
      color: HIGHLIGHT_COLOR_MAP[highlight.classification],
      status: highlight.classification,
      tokenIndex: highlight.tokenIndex,
    }

    transaction = transaction.addMark(range.from, range.to, markType.create(attributes))
  }

  transaction = transaction.setMeta("addToHistory", false)
  editor.view.dispatch(transaction)
}

export function NotesEditor({
  value,
  onChange,
  placeholder,
  highlights,
  id,
  ariaLabel,
  className,
  onHighlightClick,
}: NotesEditorProps) {
  const valueRef = useRef(value)

  useEffect(() => {
    valueRef.current = value
  }, [value])

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        horizontalRule: false,
      }),
      ClassificationHighlight.configure({
        multicolor: true,
      }),
    ],
    content: toEditorContent(value),
    editorProps: {
      handleDOMEvents: {
        click: (_view, event) => {
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

          onHighlightClick?.({
            tokenIndex,
            x: event.clientX,
            y: event.clientY,
          })
          return false
        },
      },
      attributes: {
        id: id ?? "",
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": ariaLabel ?? "Lesson notes",
        spellcheck: "false",
        autocorrect: "off",
        autocapitalize: "off",
        autocomplete: "off",
        class: cn(
          "danote-notes-editor border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 min-h-[360px] w-full rounded-md border bg-transparent px-3 py-2 pb-8 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px]",
          className,
        ),
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      const nextValue = fromEditorText(currentEditor)
      if (nextValue !== valueRef.current) {
        onChange(nextValue)
      }
    },
  })

  useEffect(() => {
    if (!editor) {
      return
    }
    if (fromEditorText(editor) === value) {
      return
    }
    editor.commands.setContent(toEditorContent(value), {
      emitUpdate: false,
      parseOptions: { preserveWhitespace: "full" },
    })
  }, [editor, value])

  const normalizedHighlights = useMemo(() => highlights, [highlights])

  useEffect(() => {
    if (!editor) {
      return
    }
    applyHighlights(editor, normalizedHighlights)
  }, [editor, normalizedHighlights])

  if (!editor) {
    return (
      <div className="relative">
        {TEST_MODE && (
          <textarea
            data-testid="lesson-notes-test-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="hidden"
            aria-hidden="true"
            tabIndex={-1}
          />
        )}
        <div
          role="textbox"
          aria-label={ariaLabel ?? "Lesson notes"}
          aria-multiline="true"
          className="border-input min-h-[360px] w-full rounded-md border bg-transparent px-3 py-2 pb-8"
        />
      </div>
    )
  }

  return (
    <div className="relative">
      {TEST_MODE && (
        <textarea
          data-testid="lesson-notes-test-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="hidden"
          aria-hidden="true"
          tabIndex={-1}
        />
      )}
      {value.length === 0 && (
        <span className="text-muted-foreground pointer-events-none absolute top-2 left-3 text-base">
          {placeholder}
        </span>
      )}
      <EditorContent
        editor={editor}
        data-testid="lesson-notes-editor"
        onInputCapture={
          TEST_MODE
            ? (event) => {
              const nextValue = normalizeInputText((event.currentTarget as HTMLElement).textContent ?? "")
              if (nextValue !== valueRef.current) {
                onChange(nextValue)
              }
            }
            : undefined
        }
      />
    </div>
  )
}
