import type { Dispatch, SetStateAction } from "react"

import {
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
  createApiClient,
} from "@/app/core"

export type SidebarApiClient = ReturnType<typeof createApiClient>
export type SearchLanguageMode = "da" | "en"

export type SearchModeSwitchSuggestion = {
  targetMode: SearchLanguageMode
  value: "switch-search-mode-da" | "switch-search-mode-en"
  label: string
  evidenceLabel: string
}

/** Identifies one search attempt so a trial-limit banner clears when the
 *  query or the search/cache config changes. */
export const searchAttemptKey = (resetVersion: string, normalizedQuery: string): string =>
  `${resetVersion}:${normalizedQuery}`

export type UseSidebarSearchParams = {
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
}

export type EnResolveResult = {
  query: string
  groups: ENPosGroup[]
}

export type EnTranslatedCorResults = {
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  fallbackEnPosGroups: ENPosGroup[]
}

export type CorFormSearchResult = {
  query: string
  payload: CORSearchFormResponse
}

export type SearchQueryState = {
  searchQuery: string
  setSearchQuery: Dispatch<SetStateAction<string>>
}
