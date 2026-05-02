import type { Dispatch, SetStateAction } from "react"

import {
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
  createApiClient,
} from "@/app/core"

export type SidebarApiClient = ReturnType<typeof createApiClient>

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
