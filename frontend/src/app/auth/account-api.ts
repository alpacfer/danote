import { BACKEND_URL } from "@/app/core/constants"
import { createApiClient } from "@/app/core/api-client"

async function extractAccountErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload.detail === "email_not_allowed") {
      return "This signed-in email is not allowed for this danote deployment."
    }
    if (payload.detail === "missing_bearer_token" || payload.detail === "invalid_token") {
      return "Your sign-in session could not be verified. Sign out and sign in again."
    }
    if (payload.detail === "auth_not_initialized") {
      return "Authentication is not initialized on the backend."
    }
    if (payload.detail === "key_storage_not_initialized") {
      return "API key storage is not initialized on the backend."
    }
    if (payload.detail === "trial_daily_limit_reached") {
      return "You've reached today's free-trial search limit. Add your own API keys for unlimited access."
    }
    if (payload.detail === "guest_api_keys_forbidden") {
      return "Guest mode cannot save API keys. Sign in to manage your own keys."
    }
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // Fall through to default message.
  }
  return fallback
}

const apiClient = createApiClient({
  backendUrl: BACKEND_URL,
  extractErrorMessage: extractAccountErrorMessage,
})

export type ApiKeyStatus = {
  provider: string
  is_set: boolean
  last_four: string | null
}

export type TrialStatus = {
  enabled: boolean
  available: boolean
  opted_in: boolean
  keys_configured: boolean
  limit: number
  used: number
  remaining: number
  resets_on: string
}

export type AccountStatus = {
  keys_configured: boolean
  providers: Record<string, ApiKeyStatus>
  missing: string[]
  trial: TrialStatus
}

export type AccountMe = {
  id: number
  email: string | null
  display_name: string | null
  auth_provider: string
}

export type UpdateApiKeyResult = {
  provider: string
  is_set: boolean
  last_four: string | null
}

export type AccountFreshStartResult = {
  status: "reset"
  message: string
}

export const API_KEY_PROVIDERS = [
  "gemini",
  "deepl",
  "azure_translation",
  "azure_tts",
] as const

export type ApiKeyProvider = (typeof API_KEY_PROVIDERS)[number]

export const PROVIDER_LABELS: Record<ApiKeyProvider, string> = {
  gemini: "Google Gemini",
  deepl: "DeepL",
  azure_translation: "Azure Translation",
  azure_tts: "Azure Text-to-Speech",
}

export const PROVIDER_HELP_URLS: Record<ApiKeyProvider, string> = {
  gemini: "https://aistudio.google.com/app/apikey",
  deepl: "https://www.deepl.com/your-account/keys",
  azure_translation: "https://portal.azure.com/#blade/HubsExtension/BrowseResource/resourceType/Microsoft.CognitiveServices%2Faccounts",
  azure_tts: "https://portal.azure.com/#blade/HubsExtension/BrowseResource/resourceType/Microsoft.CognitiveServices%2Faccounts",
}

export function fetchAccountMe(): Promise<AccountMe> {
  return apiClient.getJson<AccountMe>("/api/account/me", "Could not load account.")
}

export function fetchAccountStatus(): Promise<AccountStatus> {
  return apiClient.getJson<AccountStatus>("/api/account/status", "Could not load account status.")
}

export function optInTrial(): Promise<{ trial: TrialStatus }> {
  return apiClient.postJson<{ trial: TrialStatus }>(
    "/api/account/trial/opt-in",
    {},
    "Could not start the free trial.",
  )
}

export function upsertApiKey(provider: ApiKeyProvider, value: string): Promise<UpdateApiKeyResult> {
  return apiClient.putJson<UpdateApiKeyResult>(
    `/api/account/api-keys/${provider}`,
    { value },
    `Could not save ${PROVIDER_LABELS[provider]} key.`,
  )
}

export function deleteApiKey(provider: ApiKeyProvider): Promise<UpdateApiKeyResult> {
  return apiClient.deleteJson<UpdateApiKeyResult>(
    `/api/account/api-keys/${provider}`,
    `Could not delete ${PROVIDER_LABELS[provider]} key.`,
  )
}

export function deleteAccountLearningData(): Promise<AccountFreshStartResult> {
  return apiClient.deleteJson<AccountFreshStartResult>(
    "/api/account/data",
    "Could not delete saved words and sentences.",
  )
}
