import { useState } from "react"

import {
  NLP_MODEL_OPTIONS,
  type ConnectionStatus,
  type DeveloperApiKeysUpdateResponse,
  type HealthPayload,
  type NlpModelOption,
  type ResetDatabaseResponse,
} from "@/app/core"

type UseDeveloperSettingsParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  setStatus: (next: ConnectionStatus) => void
  setHealthPayload: (next: HealthPayload | null) => void
  onDatabaseReset: () => void
  onNotifySuccess: (message: string) => void
  onNotifyError: (message: string) => void
}

export function useDeveloperSettings({
  backendUrl,
  extractErrorMessage,
  setStatus,
  setHealthPayload,
  onDatabaseReset,
  onNotifySuccess,
  onNotifyError,
}: UseDeveloperSettingsParams) {
  const [isResettingDatabase, setIsResettingDatabase] = useState(false)
  const [selectedNlpModel, setSelectedNlpModel] = useState<NlpModelOption>(NLP_MODEL_OPTIONS[0])
  const [developerTranslationAzureApiKey, setDeveloperTranslationAzureApiKey] = useState("")
  const [developerTranslationAzureRegion, setDeveloperTranslationAzureRegion] = useState("")
  const [developerTranslationAzureEndpoint, setDeveloperTranslationAzureEndpoint] = useState("")
  const [developerTtsAzureApiKey, setDeveloperTtsAzureApiKey] = useState("")
  const [developerTtsAzureRegion, setDeveloperTtsAzureRegion] = useState("")
  const [developerTtsAzureEndpoint, setDeveloperTtsAzureEndpoint] = useState("")
  const [developerVerificationGeminiApiKey, setDeveloperVerificationGeminiApiKey] = useState("")
  const [isSavingDeveloperApiKeys, setIsSavingDeveloperApiKeys] = useState(false)

  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the complete database and cannot be undone. Continue?",
    )
    if (!shouldReset) {
      return
    }

    setIsResettingDatabase(true)
    try {
      const response = await fetch(`${backendUrl}/api/wordbank/database`, {
        method: "DELETE",
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Reset database request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ResetDatabaseResponse
      onNotifySuccess(payload.message)
      onDatabaseReset()
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not reset database."
      onNotifyError(message)
    } finally {
      setIsResettingDatabase(false)
    }
  }

  async function saveDeveloperApiKeys() {
    setIsSavingDeveloperApiKeys(true)
    try {
      const response = await fetch(`${backendUrl}/api/developer/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          translation_azure_api_key: developerTranslationAzureApiKey,
          translation_azure_region: developerTranslationAzureRegion,
          translation_azure_endpoint: developerTranslationAzureEndpoint,
          tts_azure_api_key: developerTtsAzureApiKey,
          tts_azure_region: developerTtsAzureRegion,
          tts_azure_endpoint: developerTtsAzureEndpoint,
          word_verification_gemini_api_key: developerVerificationGeminiApiKey,
        }),
      })

      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Save API keys request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as DeveloperApiKeysUpdateResponse
      onNotifySuccess(payload.message || "Runtime API keys updated.")

      const healthResponse = await fetch(`${backendUrl}/api/health`)
      if (healthResponse.ok) {
        const healthPayload = (await healthResponse.json()) as HealthPayload
        setHealthPayload(healthPayload)
        setStatus(
          healthPayload.status === "ok"
            ? "connected"
            : healthPayload.status === "degraded"
              ? "degraded"
              : "offline",
        )
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save API keys."
      onNotifyError(message)
    } finally {
      setIsSavingDeveloperApiKeys(false)
    }
  }

  return {
    isResettingDatabase,
    selectedNlpModel,
    setSelectedNlpModel,
    developerTranslationAzureApiKey,
    setDeveloperTranslationAzureApiKey,
    developerTranslationAzureRegion,
    setDeveloperTranslationAzureRegion,
    developerTranslationAzureEndpoint,
    setDeveloperTranslationAzureEndpoint,
    developerTtsAzureApiKey,
    setDeveloperTtsAzureApiKey,
    developerTtsAzureRegion,
    setDeveloperTtsAzureRegion,
    developerTtsAzureEndpoint,
    setDeveloperTtsAzureEndpoint,
    developerVerificationGeminiApiKey,
    setDeveloperVerificationGeminiApiKey,
    isSavingDeveloperApiKeys,
    saveDeveloperApiKeys,
    resetDatabase,
  }
}
