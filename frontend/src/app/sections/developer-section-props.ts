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
  developerVerificationGeminiApiKey: ComponentProps<typeof DeveloperSection>["developerVerificationGeminiApiKey"]
  isSavingDeveloperApiKeys: ComponentProps<typeof DeveloperSection>["isSavingDeveloperApiKeys"]
  isResettingDatabase: ComponentProps<typeof DeveloperSection>["isResettingDatabase"]
  setSelectedNlpModel: (model: ComponentProps<typeof DeveloperSection>["selectedNlpModel"]) => void
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
    developerVerificationGeminiApiKey: args.developerVerificationGeminiApiKey,
    isSavingDeveloperApiKeys: args.isSavingDeveloperApiKeys,
    isResettingDatabase: args.isResettingDatabase,
    onSelectedNlpModelChange: args.setSelectedNlpModel,
    onDeveloperTranslationAzureApiKeyChange: args.setDeveloperTranslationAzureApiKey,
    onDeveloperTranslationAzureRegionChange: args.setDeveloperTranslationAzureRegion,
    onDeveloperTranslationAzureEndpointChange: args.setDeveloperTranslationAzureEndpoint,
    onDeveloperTtsAzureApiKeyChange: args.setDeveloperTtsAzureApiKey,
    onDeveloperTtsAzureRegionChange: args.setDeveloperTtsAzureRegion,
    onDeveloperTtsAzureEndpointChange: args.setDeveloperTtsAzureEndpoint,
    onDeveloperVerificationGeminiApiKeyChange: args.setDeveloperVerificationGeminiApiKey,
    onSaveDeveloperApiKeys: () => {
      void args.saveDeveloperApiKeys()
    },
    onResetDatabase: () => {
      void args.resetDatabase()
    },
  }
}
