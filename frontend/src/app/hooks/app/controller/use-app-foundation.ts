import { useState } from "react"

import { BACKEND_URL } from "@/app/core"
import { useAnalysis } from "@/app/hooks/use-analysis"
import { useBackendHealth } from "@/app/hooks/use-backend-health"
import { useDiscoveredTokenMetadata } from "@/app/hooks/use-discovered-token-metadata"
import { useLexiconData } from "@/app/hooks/use-lexicon-data"
import { useNotesPersistence } from "@/app/hooks/use-notes-persistence"
import { useNotificationCenter } from "@/app/hooks/use-notification-center"
import { useSectionNavigation } from "@/app/hooks/app/use-section-navigation"

import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

export function useAppFoundation() {
  const [noteText, setNoteText] = useState("")
  const [wordbankRefreshTick, setWordbankRefreshTick] = useState(0)
  const [sentencebankRefreshTick, setSentencebankRefreshTick] = useState(0)

  const navigation = useSectionNavigation()
  const health = useBackendHealth({ backendUrl: BACKEND_URL })
  const analysis = useAnalysis({
    noteText,
    backendUrl: BACKEND_URL,
    extractErrorMessage,
  })
  const discoveredTokenMetadataState = useDiscoveredTokenMetadata()
  const notesPersistence = useNotesPersistence()
  const lexiconData = useLexiconData({
    backendUrl: BACKEND_URL,
    extractErrorMessage,
    activeSection: navigation.activeSection,
    selectedLemma: navigation.selectedLemma,
    wordbankRefreshTick,
    sentencebankRefreshTick,
  })
  const notifications = useNotificationCenter()

  return {
    noteText,
    setNoteText,
    wordbankRefreshTick,
    sentencebankRefreshTick,
    bumpWordbankRefreshTick: () => {
      setWordbankRefreshTick((current) => current + 1)
    },
    bumpSentencebankRefreshTick: () => {
      setSentencebankRefreshTick((current) => current + 1)
    },
    setWordbankRefreshTick,
    setSentencebankRefreshTick,
    navigation,
    health,
    analysis,
    discoveredTokenMetadataState,
    notesPersistence,
    lexiconData,
    notifications,
    backendUrl: BACKEND_URL,
  }
}
