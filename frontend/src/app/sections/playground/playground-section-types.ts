import type {
  AnalyzedToken,
  HighlightPopoverState,
  PhrasePopoverState,
  SaveDialogMode,
  WordActionSuggestion,
} from "@/app/core"
import type { HighlightSpan } from "@/lib/token-highlights"

export type PlaygroundSectionProps = {
  isSaveDialogOpen: boolean
  saveDialogMode: SaveDialogMode
  noteNameDraft: string
  duplicateNameConflictNoteId: string | null
  onSaveDialogOpenChange: (open: boolean) => void
  onNoteNameDraftChange: (value: string) => void
  onSaveDialogSubmit: () => void
  onResolveDuplicateName: () => void
  phrasePopover: PhrasePopoverState
  onPhrasePopoverOpenChange: (open: boolean) => void
  isGeneratingPhraseTranslation: boolean
  phraseTranslation: string | null
  generatePhraseTranslationError: string | null
  isSavingSentence: boolean
  isSelectedPhraseSaved: boolean
  onAddSentenceFromPhrase: () => void
  highlightPopover: HighlightPopoverState
  onHighlightPopoverOpenChange: (open: boolean) => void
  popoverDisplayToken: AnalyzedToken | null
  showPopoverLemma: boolean
  popoverLemmaText: string | null
  popoverMetadataBadges: Array<{ key: string; label: string; className: string }>
  showTranslationSkeleton: boolean
  popoverIsNoun: boolean
  popoverIsVerbLike: boolean
  generateTranslationError: string | null
  popoverTranslation: string | null
  popoverPrimaryAction: WordActionSuggestion | null
  addingTokens: Record<string, boolean>
  onOpenWordbankFromPopover: () => void
  onAddTokenFromPopover: () => void
  noteText: string
  noteHighlights: HighlightSpan[]
  analysisError: string | null
  onNoteTextChange: (nextText: string) => void
  onHighlightClick: (payload: { tokenIndex: number; left: number; lineTop: number; lineBottom: number }) => void
  onTextSelectionSettled: (payload: { selectedText: string; left: number; lineTop: number; lineBottom: number } | null) => void
}
