import { useEditor, EditorContent } from "@tiptap/react"
import Highlight from "@tiptap/extension-highlight"
import StarterKit from "@tiptap/starter-kit"
import { useEffect, useMemo, useRef } from "react"

import { applyHighlights } from "@/components/notes-editor-highlights"
import { handleHighlightMarkClick } from "@/components/notes-editor-highlight-click"
import { clearSelectionTimeout, scheduleSelectionSettled, type NotesEditorSelectionPayload } from "@/components/notes-editor-selection"
import { fromEditorText, normalizeInputText, toEditorContent } from "@/components/notes-editor-text"
import { cn } from "@/lib/utils"
import type { HighlightSpan } from "@/lib/token-highlights"

type NotesEditorProps = {
  value: string
  onChange: (next: string) => void
  placeholder: string
  highlights: HighlightSpan[]
  id?: string
  ariaLabel?: string
  className?: string
  onHighlightClick?: (payload: {
    tokenIndex: number
    left: number
    lineTop: number
    lineBottom: number
  }) => void
  onTextSelectionSettled?: (payload: NotesEditorSelectionPayload | null) => void
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
      comment: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-comment"),
        renderHTML: (attributes: { comment?: "true" | null }) => {
          if (attributes.comment !== "true") {
            return {}
          }
          return {
            "data-comment": "true",
          }
        },
      },
    }
  },
})

const TEST_MODE = import.meta.env.MODE === "test"

export function NotesEditor({
  value,
  onChange,
  placeholder,
  highlights,
  id,
  ariaLabel,
  className,
  onHighlightClick,
  onTextSelectionSettled,
}: NotesEditorProps) {
  const valueRef = useRef(value)
  const selectionTimeoutRef = useRef<number | null>(null)

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
        click: (view, event) => {
          return handleHighlightMarkClick({
            view,
            event,
            onHighlightClick,
          })
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
          "danote-notes-editor border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 min-h-[46vh] md:min-h-[58vh] w-full rounded-md border bg-transparent px-3 py-2 pb-8 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px]",
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
    onSelectionUpdate: ({ editor: currentEditor }) => {
      const hasSelection = !currentEditor.state.selection.empty

      selectionTimeoutRef.current = clearSelectionTimeout(selectionTimeoutRef.current)

      if (!onTextSelectionSettled) {
        return
      }

      if (!hasSelection) {
        onTextSelectionSettled(null)
        return
      }

      const from = currentEditor.state.selection.from
      const to = currentEditor.state.selection.to

      selectionTimeoutRef.current = scheduleSelectionSettled({
        editor: currentEditor,
        from,
        to,
        onTextSelectionSettled,
        onTimeoutConsumed: () => {
          selectionTimeoutRef.current = null
        },
      })
    },
  })

  useEffect(() => {
    return () => {
      selectionTimeoutRef.current = clearSelectionTimeout(selectionTimeoutRef.current)
    }
  }, [])

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
          className="border-input min-h-[46vh] md:min-h-[58vh] w-full rounded-md border bg-transparent px-3 py-2 pb-8"
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
