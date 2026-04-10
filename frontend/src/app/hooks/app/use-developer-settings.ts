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

type TranslationProviderOption = "deepl" | "azure"

function translatorApiStatusKey(provider: string | null | undefined): string {
  const normalized = (provider ?? "").trim().toLocaleLowerCase("en-US")
  if (normalized === "azure" || normalized === "azure_translator") {
    return "azure_translator"
  }
  if (normalized === "deepl" || normalized === "deepl_translator") {
    return "deepl_translator"
  }
  return "deepl_translator"
}

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
  onSearchTranslationConfigSaved: () => void
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
  onSearchTranslationConfigSaved,
  onNotifySuccess,
  onNotifyError,
}: UseDeveloperSettingsParams) {
  const [isResettingDatabase, setIsResettingDatabase] = useState(false)
  const [selectedNlpModel, setSelectedNlpModel] = useState<NlpModelOption>(NLP_MODEL_OPTIONS[0])
  const [translationProvider, setTranslationProvider] = useState<TranslationProviderOption>("deepl")
  const [developerTranslationAzureApiKey, setDeveloperTranslationAzureApiKey] = useState("")
  const [developerTranslationAzureRegion, setDeveloperTranslationAzureRegion] = useState("")
  const [developerTranslationAzureEndpoint, setDeveloperTranslationAzureEndpoint] = useState("")
  const [developerTranslationDeeplApiKey, setDeveloperTranslationDeeplApiKey] = useState("")
  const [developerTranslationDeeplEndpoint, setDeveloperTranslationDeeplEndpoint] = useState("")
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

  async function clearBrowserCache(): Promise<void> {
    try {
      localStorage.clear()
    } catch { /* storage may be inaccessible */ }
    try {
      sessionStorage.clear()
    } catch { /* storage may be inaccessible */ }
    try {
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations()
        for (const registration of registrations) {
          await registration.unregister()
        }
      }
    } catch { /* service worker may not be available */ }
    try {
      if ("caches" in window) {
        const cacheNames = await caches.keys()
        await Promise.all(cacheNames.map((name) => caches.delete(name)))
      }
    } catch { /* Cache API may not be available */ }
  }

  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the database and clear all browser cache. Continue?",
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
      await clearBrowserCache()
      window.location.reload()
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
          translation_provider: translationProvider,
          gemini_api_key: developerGeminiApiKey,
          translation_azure_api_key: developerTranslationAzureApiKey,
          translation_azure_region: developerTranslationAzureRegion,
          translation_azure_endpoint: developerTranslationAzureEndpoint,
          translation_deepl_api_key: developerTranslationDeeplApiKey,
          translation_deepl_endpoint: developerTranslationDeeplEndpoint,
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
      onSearchTranslationConfigSaved()
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
        "Could not test translator.",
      )
      setTranslationProbeResult(payload)
      setApiProbeStatuses((current) => ({
        ...current,
        [translatorApiStatusKey(payload.provider ?? translationProvider)]: payload,
      }))
      if (payload.status === "ok") {
        onNotifySuccess(payload.message || "Translator probe completed successfully.")
      } else {
        onNotifyError(payload.message || "Translator probe failed.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not test translator."
      const failurePayload = {
        status: "error",
        probe_input: "bogen",
        result_text: null,
        provider: null,
        message,
      } satisfies DeveloperServiceProbeResponse
      setTranslationProbeResult(failurePayload)
      setApiProbeStatuses((current) => ({
        ...current,
        [translatorApiStatusKey(translationProvider)]: failurePayload,
      }))
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
    translationProvider,
    setTranslationProvider,
    developerTranslationAzureApiKey,
    setDeveloperTranslationAzureApiKey,
    developerTranslationAzureRegion,
    setDeveloperTranslationAzureRegion,
    developerTranslationAzureEndpoint,
    setDeveloperTranslationAzureEndpoint,
    developerTranslationDeeplApiKey,
    setDeveloperTranslationDeeplApiKey,
    developerTranslationDeeplEndpoint,
    setDeveloperTranslationDeeplEndpoint,
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
