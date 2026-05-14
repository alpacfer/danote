import { type ComponentProps } from "react"

import { type ConnectionStatus } from "@/app/core"
import { DeveloperSection } from "@/app/sections/developer"

export type DeveloperSectionAdapterArgs = {
  status: ConnectionStatus
  backendUrl: ComponentProps<typeof DeveloperSection>["backendUrl"]
  apiStatusItems: ComponentProps<typeof DeveloperSection>["apiStatusItems"]
  translationProvider: ComponentProps<typeof DeveloperSection>["translationProvider"]
  developerTranslationAzureApiKey: ComponentProps<typeof DeveloperSection>["developerTranslationAzureApiKey"]
  developerTranslationAzureRegion: ComponentProps<typeof DeveloperSection>["developerTranslationAzureRegion"]
  developerTranslationAzureEndpoint: ComponentProps<typeof DeveloperSection>["developerTranslationAzureEndpoint"]
  developerTranslationDeeplApiKey: ComponentProps<typeof DeveloperSection>["developerTranslationDeeplApiKey"]
  developerTranslationDeeplEndpoint: ComponentProps<typeof DeveloperSection>["developerTranslationDeeplEndpoint"]
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
  isSeedingNumbersAudio: ComponentProps<typeof DeveloperSection>["isSeedingNumbersAudio"]
  isSeedingPresavedWordsAudio: ComponentProps<typeof DeveloperSection>["isSeedingPresavedWordsAudio"]
  isRegeneratingPresavedWordsAudio: ComponentProps<typeof DeveloperSection>["isRegeneratingPresavedWordsAudio"]
  setTranslationProvider: (provider: ComponentProps<typeof DeveloperSection>["translationProvider"]) => void
  setDeveloperTranslationAzureApiKey: (value: string) => void
  setDeveloperTranslationAzureRegion: (value: string) => void
  setDeveloperTranslationAzureEndpoint: (value: string) => void
  setDeveloperTranslationDeeplApiKey: (value: string) => void
  setDeveloperTranslationDeeplEndpoint: (value: string) => void
  setDeveloperTtsAzureApiKey: (value: string) => void
  setDeveloperTtsAzureRegion: (value: string) => void
  setDeveloperTtsAzureEndpoint: (value: string) => void
  setDeveloperGeminiApiKey: (value: string) => void
  saveDeveloperApiKeys: () => Promise<void>
  runTranslationProbe: () => Promise<void>
  runSpeechProbe: () => Promise<void>
  runGeminiProbe: () => Promise<void>
  resetDatabase: () => Promise<void>
  seedNumbersAudio?: () => Promise<void>
  seedPresavedWordsAudio: () => Promise<void>
  regeneratePresavedWordsAudio: () => Promise<void>
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
    translationProvider: args.translationProvider,
    translationProviderOptions: ["deepl", "azure"] as const,
    developerTranslationAzureApiKey: args.developerTranslationAzureApiKey,
    developerTranslationAzureRegion: args.developerTranslationAzureRegion,
    developerTranslationAzureEndpoint: args.developerTranslationAzureEndpoint,
    developerTranslationDeeplApiKey: args.developerTranslationDeeplApiKey,
    developerTranslationDeeplEndpoint: args.developerTranslationDeeplEndpoint,
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
    isSeedingNumbersAudio: args.isSeedingNumbersAudio,
    isSeedingPresavedWordsAudio: args.isSeedingPresavedWordsAudio,
    isRegeneratingPresavedWordsAudio: args.isRegeneratingPresavedWordsAudio,
    onTranslationProviderChange: args.setTranslationProvider,
    onDeveloperTranslationAzureApiKeyChange: args.setDeveloperTranslationAzureApiKey,
    onDeveloperTranslationAzureRegionChange: args.setDeveloperTranslationAzureRegion,
    onDeveloperTranslationAzureEndpointChange: args.setDeveloperTranslationAzureEndpoint,
    onDeveloperTranslationDeeplApiKeyChange: args.setDeveloperTranslationDeeplApiKey,
    onDeveloperTranslationDeeplEndpointChange: args.setDeveloperTranslationDeeplEndpoint,
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
    onSeedPresavedWordsAudio: () => {
      void args.seedPresavedWordsAudio()
    },
    onRegeneratePresavedWordsAudio: () => {
      void args.regeneratePresavedWordsAudio()
    },
  }
}
