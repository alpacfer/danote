import { type ComponentProps } from "react"

import { NLP_MODEL_OPTIONS, type ConnectionStatus } from "@/app/core"
import { DeveloperSection } from "@/app/sections/developer-section"

export type DeveloperSectionAdapterArgs = {
  status: ConnectionStatus
  backendUrl: ComponentProps<typeof DeveloperSection>["backendUrl"]
  apiStatusItems: ComponentProps<typeof DeveloperSection>["apiStatusItems"]
  selectedNlpModel: ComponentProps<typeof DeveloperSection>["selectedNlpModel"]
  developerTranslationAzureApiKey: ComponentProps<typeof DeveloperSection>["developerTranslationAzureApiKey"]
  developerTranslationAzureRegion: ComponentProps<typeof DeveloperSection>["developerTranslationAzureRegion"]
  developerTranslationAzureEndpoint: ComponentProps<typeof DeveloperSection>["developerTranslationAzureEndpoint"]
  developerTtsAzureApiKey: ComponentProps<typeof DeveloperSection>["developerTtsAzureApiKey"]
  developerTtsAzureRegion: ComponentProps<typeof DeveloperSection>["developerTtsAzureRegion"]
  developerTtsAzureEndpoint: ComponentProps<typeof DeveloperSection>["developerTtsAzureEndpoint"]
  developerGeminiApiKey: ComponentProps<typeof DeveloperSection>["developerGeminiApiKey"]
  isSavingDeveloperApiKeys: ComponentProps<typeof DeveloperSection>["isSavingDeveloperApiKeys"]
  isTestingTranslation: ComponentProps<typeof DeveloperSection>["isTestingTranslation"]
  translationProbeResult: ComponentProps<typeof DeveloperSection>["translationProbeResult"]
  isTestingSpeech: ComponentProps<typeof DeveloperSection>["isTestingSpeech"]
  speechProbeResult: ComponentProps<typeof DeveloperSection>["speechProbeResult"]
  isTestingGemini: ComponentProps<typeof DeveloperSection>["isTestingGemini"]
  geminiProbeResult: ComponentProps<typeof DeveloperSection>["geminiProbeResult"]
  isResettingDatabase: ComponentProps<typeof DeveloperSection>["isResettingDatabase"]
  setSelectedNlpModel: (model: ComponentProps<typeof DeveloperSection>["selectedNlpModel"]) => void
  setDeveloperTranslationAzureApiKey: (value: string) => void
  setDeveloperTranslationAzureRegion: (value: string) => void
  setDeveloperTranslationAzureEndpoint: (value: string) => void
  setDeveloperTtsAzureApiKey: (value: string) => void
  setDeveloperTtsAzureRegion: (value: string) => void
  setDeveloperTtsAzureEndpoint: (value: string) => void
  setDeveloperGeminiApiKey: (value: string) => void
  saveDeveloperApiKeys: () => Promise<void>
  runTranslationProbe: () => Promise<void>
  runSpeechProbe: () => Promise<void>
  runGeminiProbe: () => Promise<void>
  resetDatabase: () => Promise<void>
}

function badgeVariantForStatus(status: ConnectionStatus): ComponentProps<typeof DeveloperSection>["badgeVariant"] {
  if (status === "connected") {
    return "secondary"
  }
  if (status === "offline") {
    return "destructive"
  }
  return "outline"
}

export function buildDeveloperSectionProps(
  args: DeveloperSectionAdapterArgs,
): ComponentProps<typeof DeveloperSection> {
  return {
    badgeVariant: badgeVariantForStatus(args.status),
    status: args.status,
    backendUrl: args.backendUrl,
    apiStatusItems: args.apiStatusItems,
    selectedNlpModel: args.selectedNlpModel,
    nlpModelOptions: NLP_MODEL_OPTIONS,
    developerTranslationAzureApiKey: args.developerTranslationAzureApiKey,
    developerTranslationAzureRegion: args.developerTranslationAzureRegion,
    developerTranslationAzureEndpoint: args.developerTranslationAzureEndpoint,
    developerTtsAzureApiKey: args.developerTtsAzureApiKey,
    developerTtsAzureRegion: args.developerTtsAzureRegion,
    developerTtsAzureEndpoint: args.developerTtsAzureEndpoint,
    developerGeminiApiKey: args.developerGeminiApiKey,
    isSavingDeveloperApiKeys: args.isSavingDeveloperApiKeys,
    isTestingTranslation: args.isTestingTranslation,
    translationProbeResult: args.translationProbeResult,
    isTestingSpeech: args.isTestingSpeech,
    speechProbeResult: args.speechProbeResult,
    isTestingGemini: args.isTestingGemini,
    geminiProbeResult: args.geminiProbeResult,
    isResettingDatabase: args.isResettingDatabase,
    onSelectedNlpModelChange: args.setSelectedNlpModel,
    onDeveloperTranslationAzureApiKeyChange: args.setDeveloperTranslationAzureApiKey,
    onDeveloperTranslationAzureRegionChange: args.setDeveloperTranslationAzureRegion,
    onDeveloperTranslationAzureEndpointChange: args.setDeveloperTranslationAzureEndpoint,
    onDeveloperTtsAzureApiKeyChange: args.setDeveloperTtsAzureApiKey,
    onDeveloperTtsAzureRegionChange: args.setDeveloperTtsAzureRegion,
    onDeveloperTtsAzureEndpointChange: args.setDeveloperTtsAzureEndpoint,
    onDeveloperGeminiApiKeyChange: args.setDeveloperGeminiApiKey,
    onSaveDeveloperApiKeys: () => {
      void args.saveDeveloperApiKeys()
    },
    onRunTranslationProbe: () => {
      void args.runTranslationProbe()
    },
    onRunSpeechProbe: () => {
      void args.runSpeechProbe()
    },
    onRunGeminiProbe: () => {
      void args.runGeminiProbe()
    },
    onResetDatabase: () => {
      void args.resetDatabase()
    },
  }
}
