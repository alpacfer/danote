import { type AnalyzedToken, type WordActionSuggestion } from "@/app/core/types-api"

export type HighlightPopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  tokenIndex: number | null
}

export type PhrasePopoverState = {
  open: boolean
  left: number
  lineTop: number
  lineBottom: number
  side: "top" | "bottom"
  selectedText: string
}

export type DiscoveredTokenMetadata = {
  pos_tag: string
  morphology: string | null
  lemma: string | null
  word_actions?: WordActionSuggestion[]
}

export type DiscoveredTokenMemory = {
  latest: DiscoveredTokenMetadata
  byPos: Record<string, DiscoveredTokenMetadata>
}

export type SaveDialogMode = "initial" | "create_new"

export type SavedNote = {
  id: string
  name: string
  text: string
  tokens: AnalyzedToken[]
  discoveredTokenMetadata: Record<string, DiscoveredTokenMemory>
  generatedTranslationMap: Record<string, string | null>
  savedAt: string
}

export type AppNotification = {
  id: string
  message: string
  createdAt: string
  read: boolean
}

export type VerificationErrorDetail = {
  provider: string
  status: "flagged" | "error"
  problem: string
  changeToImplement: string
  rawMessage: string
  storedSurfaceForm: string | null
  meaningId: number | null
  suggestedChanges?: {
    lemmaPosTag?: string
    lemmaMorphology?: string
    surfacePosTag?: string
    surfaceMorphology?: string
    lexemeTranslation?: string
    surfaceTranslation?: string
  }
  suggestedChangesPayload?: {
    lemma_pos_tag?: string | null
    lemma_morphology?: string | null
    surface_pos_tag?: string | null
    surface_morphology?: string | null
    lexeme_translation?: string | null
    surface_translation?: string | null
  }
}
