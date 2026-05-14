import { BACKEND_URL } from "@/app/core/constants"
import { createApiClient } from "@/app/core/api-client"

const apiClient = createApiClient({ backendUrl: BACKEND_URL })

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
