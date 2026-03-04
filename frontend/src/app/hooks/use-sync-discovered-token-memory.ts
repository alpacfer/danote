import { useEffect } from "react"

import {
  isLowConfidencePosTag,
  normalizeWordKey,
  type AnalyzedToken,
  type DiscoveredTokenMemory,
} from "@/app/core"

type UseSyncDiscoveredTokenMemoryParams = {
  tokens: AnalyzedToken[]
  setDiscoveredTokenMetadata: (
    value: Record<string, DiscoveredTokenMemory> | ((current: Record<string, DiscoveredTokenMemory>) => Record<string, DiscoveredTokenMemory>),
  ) => void
}

export function useSyncDiscoveredTokenMemory({
  tokens,
  setDiscoveredTokenMetadata,
}: UseSyncDiscoveredTokenMemoryParams) {
  useEffect(() => {
    if (tokens.length === 0) {
      return
    }

    setDiscoveredTokenMetadata((current) => {
      let changed = false
      const next = { ...current }
      for (const token of tokens) {
        if (isLowConfidencePosTag(token.pos_tag)) {
          continue
        }
        const tokenPos = token.pos_tag
        if (!tokenPos) {
          continue
        }
        const key = normalizeWordKey(token.normalized_token || token.surface_token)
        const lemma = token.matched_lemma ?? token.lemma_candidate ?? null
        const candidate = {
          pos_tag: tokenPos,
          morphology: token.morphology,
          lemma,
        }
        const existing = next[key]
        const existingForPos = existing?.byPos[candidate.pos_tag]

        if (
          !existing ||
          !existingForPos ||
          existingForPos.morphology !== candidate.morphology ||
          existingForPos.lemma !== candidate.lemma ||
          existing.latest.pos_tag !== candidate.pos_tag ||
          existing.latest.morphology !== candidate.morphology ||
          existing.latest.lemma !== candidate.lemma
        ) {
          next[key] = {
            latest: candidate,
            byPos: {
              ...(existing?.byPos ?? {}),
              [candidate.pos_tag]: candidate,
            },
          }
          changed = true
        }
      }
      return changed ? next : current
    })
  }, [setDiscoveredTokenMetadata, tokens])
}
