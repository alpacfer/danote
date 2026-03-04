import { useState } from "react"

import { type DiscoveredTokenMemory } from "@/app/core"

export function useDiscoveredTokenMetadata() {
  const [discoveredTokenMetadata, setDiscoveredTokenMetadata] = useState<Record<string, DiscoveredTokenMemory>>({})

  return {
    discoveredTokenMetadata,
    setDiscoveredTokenMetadata,
  }
}
