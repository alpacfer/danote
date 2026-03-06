import type { UseAppSectionPropsParams } from "@/app/hooks/app/use-app-section-props"
import type { DeveloperContext } from "@/app/hooks/app/controller/section-props-types"

export function buildDeveloperSectionProps(
  context: DeveloperContext,
): Pick<
  UseAppSectionPropsParams,
  | "status"
  | "backendUrl"
  | "apiStatusItems"
  | "selectedNlpModel"
  | "developerTranslationAzureApiKey"
  | "developerTranslationAzureRegion"
  | "developerTranslationAzureEndpoint"
  | "developerTtsAzureApiKey"
  | "developerTtsAzureRegion"
  | "developerTtsAzureEndpoint"
  | "developerVerificationGeminiApiKey"
  | "isSavingDeveloperApiKeys"
  | "isResettingDatabase"
  | "setSelectedNlpModel"
  | "setDeveloperTranslationAzureApiKey"
  | "setDeveloperTranslationAzureRegion"
  | "setDeveloperTranslationAzureEndpoint"
  | "setDeveloperTtsAzureApiKey"
  | "setDeveloperTtsAzureRegion"
  | "setDeveloperTtsAzureEndpoint"
  | "setDeveloperVerificationGeminiApiKey"
  | "saveDeveloperApiKeys"
  | "resetDatabase"
> {
  return {
    status: context.status,
    backendUrl: context.backendUrl,
    apiStatusItems: context.apiStatusItems,
    selectedNlpModel: context.selectedNlpModel,
    developerTranslationAzureApiKey: context.developerTranslationAzureApiKey,
    developerTranslationAzureRegion: context.developerTranslationAzureRegion,
    developerTranslationAzureEndpoint: context.developerTranslationAzureEndpoint,
    developerTtsAzureApiKey: context.developerTtsAzureApiKey,
    developerTtsAzureRegion: context.developerTtsAzureRegion,
    developerTtsAzureEndpoint: context.developerTtsAzureEndpoint,
    developerVerificationGeminiApiKey: context.developerVerificationGeminiApiKey,
    isSavingDeveloperApiKeys: context.isSavingDeveloperApiKeys,
    isResettingDatabase: context.isResettingDatabase,
    setSelectedNlpModel: context.setSelectedNlpModel,
    setDeveloperTranslationAzureApiKey: context.setDeveloperTranslationAzureApiKey,
    setDeveloperTranslationAzureRegion: context.setDeveloperTranslationAzureRegion,
    setDeveloperTranslationAzureEndpoint: context.setDeveloperTranslationAzureEndpoint,
    setDeveloperTtsAzureApiKey: context.setDeveloperTtsAzureApiKey,
    setDeveloperTtsAzureRegion: context.setDeveloperTtsAzureRegion,
    setDeveloperTtsAzureEndpoint: context.setDeveloperTtsAzureEndpoint,
    setDeveloperVerificationGeminiApiKey: context.setDeveloperVerificationGeminiApiKey,
    saveDeveloperApiKeys: context.saveDeveloperApiKeys,
    resetDatabase: context.resetDatabase,
  }
}
