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

export type AccountStatus = {
  keys_configured: boolean
  providers: Record<string, ApiKeyStatus>
  missing: string[]
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
