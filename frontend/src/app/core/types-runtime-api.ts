import type { ApiRuntimeStatus } from "@/app/core/types-app-api"

export type ResetDatabaseResponse = {
  status: "reset"
  message: string
}

export type SeedNumbersAudioResponse = {
  generated: number
  skipped: number
  failed: number
  message: string
}

export type SeedPresavedWordsAudioResponse = {
  generated: number
  skipped: number
  failed: number
  message: string
}

export type GenerateTranslationResponse = {
  status: "generated" | "unavailable"
  source_word: string
  lemma: string
  english_translation: string | null
}

export type GeneratePhraseTranslationResponse = {
  status: "generated" | "cached" | "unavailable"
  source_text: string
  english_translation: string | null
}

export type HealthApiStatusEntry = {
  status?: string
  active?: boolean
  configured?: boolean
  message?: string | null
}

export type HealthPayload = {
  status?: string
  service?: string
  components?: Record<string, string>
  apis?: Record<string, HealthApiStatusEntry>
}

export type ApiStatusItem = {
  name: string
  label: string
  status: ApiRuntimeStatus
  message: string | null
}

export type DeveloperApiKeysUpdateResponse = {
  status: string
  message: string
  configured: Record<string, boolean>
}

export type DeveloperServiceProbeResponse = {
  status: string
  probe_input: string
  result_text: string | null
  provider: string | null
  message: string
}

export type GeminiProbeResponse = DeveloperServiceProbeResponse
