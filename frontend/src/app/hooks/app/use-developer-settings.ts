import { useMemo, useState } from "react"

import {
  createApiClient,
  type DeveloperServiceProbeResponse,
  type GeminiProbeResponse,
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
  setApiProbeStatuses: (
    next:
      | Record<string, DeveloperServiceProbeResponse | null>
      | ((current: Record<string, DeveloperServiceProbeResponse | null>) => Record<string, DeveloperServiceProbeResponse | null>),
  ) => void
  onDatabaseReset: () => void
  onNotifySuccess: (message: string) => void
  onNotifyError: (message: string) => void
}

export function useDeveloperSettings({
  backendUrl,
  extractErrorMessage,
  setStatus,
  setHealthPayload,
  setApiProbeStatuses,
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
  const [developerGeminiApiKey, setDeveloperGeminiApiKey] = useState("")
  const [isSavingDeveloperApiKeys, setIsSavingDeveloperApiKeys] = useState(false)
  const [isTestingTranslation, setIsTestingTranslation] = useState(false)
  const [translationProbeResult, setTranslationProbeResult] = useState<DeveloperServiceProbeResponse | null>(null)
  const [isTestingSpeech, setIsTestingSpeech] = useState(false)
  const [speechProbeResult, setSpeechProbeResult] = useState<DeveloperServiceProbeResponse | null>(null)
  const [isTestingGemini, setIsTestingGemini] = useState(false)
  const [geminiProbeResult, setGeminiProbeResult] = useState<GeminiProbeResponse | null>(null)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the complete database and cannot be undone. Continue?",
    )
    if (!shouldReset) {
      return
    }

    setIsResettingDatabase(true)
    try {
      const payload = await apiClient.deleteJson<ResetDatabaseResponse>(
        "/api/wordbank/database",
        "Could not reset database.",
      )
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
      const payload = await apiClient.postJson<DeveloperApiKeysUpdateResponse>(
        "/api/developer/api-keys",
        {
          gemini_api_key: developerGeminiApiKey,
          translation_azure_api_key: developerTranslationAzureApiKey,
          translation_azure_region: developerTranslationAzureRegion,
          translation_azure_endpoint: developerTranslationAzureEndpoint,
          tts_azure_api_key: developerTtsAzureApiKey,
          tts_azure_region: developerTtsAzureRegion,
          tts_azure_endpoint: developerTtsAzureEndpoint,
          word_verification_gemini_api_key: developerGeminiApiKey,
        },
        "Could not save API keys.",
      )
      onNotifySuccess(payload.message || "Runtime API keys updated.")

      const healthPayload = await apiClient.tryGetJson<HealthPayload>("/api/health")
      if (healthPayload) {
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

  async function runGeminiProbe() {
    setIsTestingGemini(true)
    try {
      const payload = await apiClient.postJson<GeminiProbeResponse>(
        "/api/developer/gemini-probe",
        {},
        "Could not test Gemini.",
      )
      setGeminiProbeResult(payload)
      setApiProbeStatuses((current) => ({ ...current, gemini: payload }))
      if (payload.status === "ok") {
        onNotifySuccess(payload.message || "Gemini probe completed successfully.")
      } else {
        onNotifyError(payload.message || "Gemini probe failed.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not test Gemini."
      setGeminiProbeResult({
        status: "error",
        probe_input: "bogen",
        result_text: null,
        provider: null,
        message,
      })
      setApiProbeStatuses((current) => ({
        ...current,
        gemini: {
          status: "error",
          probe_input: "bogen",
          result_text: null,
          provider: null,
          message,
        },
      }))
      onNotifyError(message)
    } finally {
      setIsTestingGemini(false)
    }
  }

  async function runTranslationProbe() {
    setIsTestingTranslation(true)
    try {
      const payload = await apiClient.postJson<DeveloperServiceProbeResponse>(
        "/api/developer/translation-probe",
        {},
        "Could not test Azure Translator.",
      )
      setTranslationProbeResult(payload)
      setApiProbeStatuses((current) => ({ ...current, azure_translator: payload }))
      if (payload.status === "ok") {
        onNotifySuccess(payload.message || "Azure Translator probe completed successfully.")
      } else {
        onNotifyError(payload.message || "Azure Translator probe failed.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not test Azure Translator."
      const failurePayload = {
        status: "error",
        probe_input: "bogen",
        result_text: null,
        provider: null,
        message,
      } satisfies DeveloperServiceProbeResponse
      setTranslationProbeResult(failurePayload)
      setApiProbeStatuses((current) => ({ ...current, azure_translator: failurePayload }))
      onNotifyError(message)
    } finally {
      setIsTestingTranslation(false)
    }
  }

  async function runSpeechProbe() {
    setIsTestingSpeech(true)
    try {
      const payload = await apiClient.postJson<DeveloperServiceProbeResponse>(
        "/api/developer/tts-probe",
        {},
        "Could not test Azure Speech.",
      )
      setSpeechProbeResult(payload)
      setApiProbeStatuses((current) => ({ ...current, azure_speech: payload }))
      if (payload.status === "ok") {
        onNotifySuccess(payload.message || "Azure Speech probe completed successfully.")
      } else {
        onNotifyError(payload.message || "Azure Speech probe failed.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not test Azure Speech."
      const failurePayload = {
        status: "error",
        probe_input: "bogen",
        result_text: null,
        provider: null,
        message,
      } satisfies DeveloperServiceProbeResponse
      setSpeechProbeResult(failurePayload)
      setApiProbeStatuses((current) => ({ ...current, azure_speech: failurePayload }))
      onNotifyError(message)
    } finally {
      setIsTestingSpeech(false)
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
    developerGeminiApiKey,
    setDeveloperGeminiApiKey,
    isSavingDeveloperApiKeys,
    saveDeveloperApiKeys,
    isTestingTranslation,
    translationProbeResult,
    runTranslationProbe,
    isTestingSpeech,
    speechProbeResult,
    runSpeechProbe,
    isTestingGemini,
    geminiProbeResult,
    runGeminiProbe,
    resetDatabase,
  }
}
