import {
  type AnalyzedToken,
  type VerificationAction,
  type WordActionSuggestion,
} from "@/app/core/types-api"

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

type BaseNotification = {
  id: string
  message: string
  createdAt: string
  read: boolean
}

export type InfoNotification = BaseNotification & {
  kind: "info"
}

export type WordVerificationNotification = BaseNotification & {
  kind: "word_verification"
  lemma: string
  meaningId: number | null
  surfaceForm: string | null
  actionCount: number
}

export type AppNotification = InfoNotification | WordVerificationNotification

export type VerificationErrorDetail = {
  provider: string
  status: "flagged" | "error"
  problem: string
  changeToImplement: string
  rawMessage: string
  storedSurfaceForm: string | null
  meaningId: number | null
  suggestedActions: VerificationAction[]
}

export type VerificationSuccessDetail = {
  provider: string
  rawMessage: string
  storedSurfaceForm: string | null
  meaningId: number | null
  verifiedAt: string
}
