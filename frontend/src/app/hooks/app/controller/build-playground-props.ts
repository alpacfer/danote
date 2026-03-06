import type { UseAppSectionPropsParams } from "@/app/hooks/app/use-app-section-props"

type BuildPlaygroundPropsArgs = {
  isSaveDialogOpen: boolean
  saveDialogMode: UseAppSectionPropsParams["playgroundProps"]["saveDialogMode"]
  noteNameDraft: string
  duplicateNameConflictNoteId: string | null
  handleSaveDialogOpenChange: (open: boolean) => void
  handleNoteNameDraftChange: (value: string) => void
  handleSaveDialogSubmit: () => void
  resolveDuplicateNameConflict: () => void
  phrasePopover: UseAppSectionPropsParams["playgroundProps"]["phrasePopover"]
  handlePhrasePopoverOpenChange: (open: boolean) => void
  isGeneratingPhraseTranslation: boolean
  phraseTranslation: string | null
  generatePhraseTranslationError: string | null
  isSavingSentence: boolean
  isSelectedPhraseSaved: boolean
  addSentenceToSentencebank: (text: string) => Promise<void>
  highlightPopover: UseAppSectionPropsParams["playgroundProps"]["highlightPopover"]
  handleHighlightPopoverOpenChange: (open: boolean) => void
  popoverDisplayToken: UseAppSectionPropsParams["playgroundProps"]["popoverDisplayToken"]
  showPopoverLemma: boolean
  popoverLemmaText: string | null
  popoverMetadataBadges: UseAppSectionPropsParams["playgroundProps"]["popoverMetadataBadges"]
  showTranslationSkeleton: boolean
  popoverIsNoun: boolean
  popoverIsVerbLike: boolean
  generateTranslationError: string | null
  popoverTranslation: string | null
  popoverPrimaryAction: UseAppSectionPropsParams["playgroundProps"]["popoverPrimaryAction"]
  addingTokens: Record<string, boolean>
  closeHighlightPopover: () => void
  openWordbankLemma: (lemma: string) => void
  addTokenToWordbank: (
    token: NonNullable<UseAppSectionPropsParams["playgroundProps"]["popoverDisplayToken"]>,
    action: NonNullable<UseAppSectionPropsParams["playgroundProps"]["popoverPrimaryAction"]>,
  ) => Promise<void>
  noteText: string
  noteHighlights: UseAppSectionPropsParams["playgroundProps"]["noteHighlights"]
  analysisError: string | null
  setNoteText: (value: string) => void
  clearPlaygroundTransientState: () => void
  openHighlightPopover: (tokenIndex: number, left: number, lineTop: number, lineBottom: number) => void
  handleEditorSelection: UseAppSectionPropsParams["playgroundProps"]["onTextSelectionSettled"]
}

export function buildPlaygroundProps(args: BuildPlaygroundPropsArgs): UseAppSectionPropsParams["playgroundProps"] {
  return {
    isSaveDialogOpen: args.isSaveDialogOpen,
    saveDialogMode: args.saveDialogMode,
    noteNameDraft: args.noteNameDraft,
    duplicateNameConflictNoteId: args.duplicateNameConflictNoteId,
    onSaveDialogOpenChange: args.handleSaveDialogOpenChange,
    onNoteNameDraftChange: args.handleNoteNameDraftChange,
    onSaveDialogSubmit: args.handleSaveDialogSubmit,
    onResolveDuplicateName: args.resolveDuplicateNameConflict,
    phrasePopover: args.phrasePopover,
    onPhrasePopoverOpenChange: args.handlePhrasePopoverOpenChange,
    isGeneratingPhraseTranslation: args.isGeneratingPhraseTranslation,
    phraseTranslation: args.phraseTranslation,
    generatePhraseTranslationError: args.generatePhraseTranslationError,
    isSavingSentence: args.isSavingSentence,
    isSelectedPhraseSaved: args.isSelectedPhraseSaved,
    onAddSentenceFromPhrase: () => {
      void args.addSentenceToSentencebank(args.phrasePopover.selectedText)
    },
    highlightPopover: args.highlightPopover,
    onHighlightPopoverOpenChange: args.handleHighlightPopoverOpenChange,
    popoverDisplayToken: args.popoverDisplayToken,
    showPopoverLemma: args.showPopoverLemma,
    popoverLemmaText: args.popoverLemmaText,
    popoverMetadataBadges: args.popoverMetadataBadges,
    showTranslationSkeleton: args.showTranslationSkeleton,
    popoverIsNoun: args.popoverIsNoun,
    popoverIsVerbLike: args.popoverIsVerbLike,
    generateTranslationError: args.generateTranslationError,
    popoverTranslation: args.popoverTranslation,
    popoverPrimaryAction: args.popoverPrimaryAction,
    addingTokens: args.addingTokens,
    onOpenWordbankFromPopover: () => {
      if (!args.popoverPrimaryAction?.lemma) {
        return
      }
      args.closeHighlightPopover()
      args.openWordbankLemma(args.popoverPrimaryAction.lemma)
    },
    onAddTokenFromPopover: () => {
      if (!args.popoverDisplayToken || !args.popoverPrimaryAction) {
        return
      }
      void args.addTokenToWordbank(args.popoverDisplayToken, args.popoverPrimaryAction)
      args.closeHighlightPopover()
    },
    noteText: args.noteText,
    noteHighlights: args.noteHighlights,
    analysisError: args.analysisError,
    onNoteTextChange: (nextText: string) => {
      args.setNoteText(nextText)
      args.clearPlaygroundTransientState()
    },
    onHighlightClick: ({ tokenIndex, left, lineTop, lineBottom }) => {
      args.openHighlightPopover(tokenIndex, left, lineTop, lineBottom)
    },
    onTextSelectionSettled: args.handleEditorSelection,
  }
}
