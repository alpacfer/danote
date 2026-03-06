import { useNoteWorkspace } from "@/app/hooks/use-note-workspace"
import { usePlaygroundPopovers } from "@/app/hooks/use-playground-popovers"

import type { useAppFoundation } from "@/app/hooks/app/controller/use-app-foundation"
import { extractErrorMessage } from "@/app/hooks/app/controller/runtime-utils"

type AppFoundation = ReturnType<typeof useAppFoundation>

type UsePlaygroundCompositionArgs = {
  foundation: AppFoundation
}

export function usePlaygroundComposition({ foundation }: UsePlaygroundCompositionArgs) {
  const { analysis, discoveredTokenMetadataState, lexiconData, notesPersistence, notifications, navigation, noteText, setNoteText, backendUrl } = foundation

  const popovers = usePlaygroundPopovers({
    backendUrl,
    extractErrorMessage,
    tokens: analysis.tokens,
    discoveredTokenMetadata: discoveredTokenMetadataState.discoveredTokenMetadata,
    sentences: lexiconData.sentences,
  })

  const workspace = useNoteWorkspace({
    noteText,
    tokens: analysis.tokens,
    discoveredTokenMetadata: discoveredTokenMetadataState.discoveredTokenMetadata,
    generatedTranslationMap: popovers.generatedTranslationMap,
    savedNotes: notesPersistence.savedNotes,
    setSavedNotes: notesPersistence.setSavedNotes,
    activeSavedNote: notesPersistence.activeSavedNote,
    setActiveNoteId: notesPersistence.setActiveNoteId,
    setAutosaveStatus: notesPersistence.setAutosaveStatus,
    noteAutosaveTimeoutRef: notesPersistence.noteAutosaveTimeoutRef,
    setNoteText,
    setTokens: analysis.setTokens,
    setDiscoveredTokenMetadata: discoveredTokenMetadataState.setDiscoveredTokenMetadata,
    setGeneratedTranslationMap: popovers.setGeneratedTranslationMap,
    setAnalysisError: analysis.setAnalysisError,
    clearPlaygroundTransientState: popovers.clearTransientState,
    setActiveSection: navigation.setActiveSection,
    pushNotification: notifications.pushNotification,
  })

  return {
    popovers,
    workspace,
  }
}
