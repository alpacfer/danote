import { useMemo } from "react"
import { type ComponentProps } from "react"

import {
  DeveloperSection,
  NotesSection,
  PlaygroundSection,
  SentencebankSection,
  WordbankSection,
} from "@/app/sections"
import {
  NLP_MODEL_OPTIONS,
  type ApiStatusItem,
  type ConnectionStatus,
  type NlpModelOption,
  type SentencebankSentence,
  type WordbankLemma,
} from "@/app/core"

type PlaygroundProps = ComponentProps<typeof PlaygroundSection>
type NotesProps = ComponentProps<typeof NotesSection>
type WordbankProps = ComponentProps<typeof WordbankSection>
type SentencebankProps = ComponentProps<typeof SentencebankSection>
type DeveloperProps = ComponentProps<typeof DeveloperSection>

export type UseAppSectionPropsParams = {
  autosaveStatus: "off" | "saving" | "saved"
  playgroundProps: PlaygroundProps
  savedNotes: NotesProps["savedNotes"]
  openSavedNoteInPlayground: NotesProps["onOpenSavedNote"]
  selectedLemma: string | null
  wordbankError: WordbankProps["wordbankError"]
  isWordbankLoading: boolean
  lemmas: WordbankLemma[]
  groupedWordbankLemmas: WordbankProps["groupedWordbankLemmas"]
  setSelectedLemma: (lemma: string | null) => void
  lemmaDetails: WordbankProps["lemmaDetails"]
  lemmaDetailsError: WordbankProps["lemmaDetailsError"]
  isLemmaDetailsLoading: boolean
  showLemmaDetailsLoadingSkeleton: boolean
  pronunciationLoadingByForm: WordbankProps["pronunciationLoadingByForm"]
  playPronunciation: (form: string) => Promise<void>
  isRegeneratingLemmaPronunciation: boolean
  regenerateSelectedLemmaPronunciation: () => Promise<void>
  selectedLemmaVerificationError: WordbankProps["selectedLemmaVerificationError"]
  hasSuggestedVerificationChanges: boolean
  isApplyingVerificationChanges: boolean
  applySelectedLemmaVerificationChanges: () => Promise<void>
  sentencebankError: SentencebankProps["sentencebankError"]
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
  selectedNlpModel: NlpModelOption
  developerTranslationAzureApiKey: string
  developerTranslationAzureRegion: string
  developerTranslationAzureEndpoint: string
  developerTtsAzureApiKey: string
  developerTtsAzureRegion: string
  developerTtsAzureEndpoint: string
  developerVerificationGeminiApiKey: string
  isSavingDeveloperApiKeys: boolean
  isResettingDatabase: boolean
  setSelectedNlpModel: (model: NlpModelOption) => void
  setDeveloperTranslationAzureApiKey: (value: string) => void
  setDeveloperTranslationAzureRegion: (value: string) => void
  setDeveloperTranslationAzureEndpoint: (value: string) => void
  setDeveloperTtsAzureApiKey: (value: string) => void
  setDeveloperTtsAzureRegion: (value: string) => void
  setDeveloperTtsAzureEndpoint: (value: string) => void
  setDeveloperVerificationGeminiApiKey: (value: string) => void
  saveDeveloperApiKeys: () => Promise<void>
  resetDatabase: () => Promise<void>
}

function badgeVariantForStatus(status: ConnectionStatus): DeveloperProps["badgeVariant"] {
  if (status === "connected") {
    return "secondary"
  }
  if (status === "offline") {
    return "destructive"
  }
  return "outline"
}

function autosaveStatusLabel(autosaveStatus: "off" | "saving" | "saved") {
  if (autosaveStatus === "saving") {
    return "Autosaving..."
  }
  if (autosaveStatus === "saved") {
    return "Autosaved"
  }
  return "Autosave off"
}

export function useAppSectionProps(params: UseAppSectionPropsParams) {
  return useMemo(() => {
    const notesSectionProps: NotesProps = {
      savedNotes: params.savedNotes,
      onOpenSavedNote: params.openSavedNoteInPlayground,
    }

    const wordbankSectionProps: WordbankProps = {
      selectedLemma: params.selectedLemma,
      wordbankError: params.wordbankError,
      isWordbankLoading: params.isWordbankLoading,
      lemmas: params.lemmas,
      groupedWordbankLemmas: params.groupedWordbankLemmas,
      onSelectLemma: params.setSelectedLemma,
      lemmaDetails: params.lemmaDetails,
      lemmaDetailsError: params.lemmaDetailsError,
      isLemmaDetailsLoading: params.isLemmaDetailsLoading,
      showLemmaDetailsLoadingSkeleton: params.showLemmaDetailsLoadingSkeleton,
      pronunciationLoadingByForm: params.pronunciationLoadingByForm,
      onPlayPronunciation: (form: string) => {
        void params.playPronunciation(form)
      },
      isRegeneratingLemmaPronunciation: params.isRegeneratingLemmaPronunciation,
      onRegenerateSelectedLemmaPronunciation: () => {
        void params.regenerateSelectedLemmaPronunciation()
      },
      selectedLemmaVerificationError: params.selectedLemmaVerificationError,
      hasSuggestedVerificationChanges: params.hasSuggestedVerificationChanges,
      isApplyingVerificationChanges: params.isApplyingVerificationChanges,
      onApplySelectedLemmaVerificationChanges: () => {
        void params.applySelectedLemmaVerificationChanges()
      },
    }

    const sentencebankSectionProps: SentencebankProps = {
      sentencebankError: params.sentencebankError,
      isSentencebankLoading: params.isSentencebankLoading,
      sentences: params.sentences,
    }

    const developerSectionProps: DeveloperProps = {
      badgeVariant: badgeVariantForStatus(params.status),
      status: params.status,
      backendUrl: params.backendUrl,
      apiStatusItems: params.apiStatusItems,
      selectedNlpModel: params.selectedNlpModel,
      nlpModelOptions: NLP_MODEL_OPTIONS,
      developerTranslationAzureApiKey: params.developerTranslationAzureApiKey,
      developerTranslationAzureRegion: params.developerTranslationAzureRegion,
      developerTranslationAzureEndpoint: params.developerTranslationAzureEndpoint,
      developerTtsAzureApiKey: params.developerTtsAzureApiKey,
      developerTtsAzureRegion: params.developerTtsAzureRegion,
      developerTtsAzureEndpoint: params.developerTtsAzureEndpoint,
      developerVerificationGeminiApiKey: params.developerVerificationGeminiApiKey,
      isSavingDeveloperApiKeys: params.isSavingDeveloperApiKeys,
      isResettingDatabase: params.isResettingDatabase,
      onSelectedNlpModelChange: params.setSelectedNlpModel,
      onDeveloperTranslationAzureApiKeyChange: params.setDeveloperTranslationAzureApiKey,
      onDeveloperTranslationAzureRegionChange: params.setDeveloperTranslationAzureRegion,
      onDeveloperTranslationAzureEndpointChange: params.setDeveloperTranslationAzureEndpoint,
      onDeveloperTtsAzureApiKeyChange: params.setDeveloperTtsAzureApiKey,
      onDeveloperTtsAzureRegionChange: params.setDeveloperTtsAzureRegion,
      onDeveloperTtsAzureEndpointChange: params.setDeveloperTtsAzureEndpoint,
      onDeveloperVerificationGeminiApiKeyChange: params.setDeveloperVerificationGeminiApiKey,
      onSaveDeveloperApiKeys: () => {
        void params.saveDeveloperApiKeys()
      },
      onResetDatabase: () => {
        void params.resetDatabase()
      },
    }

    return {
      autosaveStatusLabel: autosaveStatusLabel(params.autosaveStatus),
      playgroundSectionProps: params.playgroundProps,
      notesSectionProps,
      wordbankSectionProps,
      sentencebankSectionProps,
      developerSectionProps,
    }
  }, [params])
}
