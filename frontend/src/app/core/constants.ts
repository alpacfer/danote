export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000"
export const ANALYZE_DEBOUNCE_MS = 450
export const SEARCH_RESOLVE_DEBOUNCE_MS = 220
export const SENTENCE_DEBOUNCE_DA_MS = 200
export const SENTENCE_DEBOUNCE_EN_MS = 350
export const SENTENCE_VERIFY_MAX_CHARS = 150
export const POPOVER_ENRICH_CACHE_TTL_MS = 60_000
export const PHRASE_TRANSLATION_DELAY_MS = 1000
export const NLP_MODEL_OPTIONS = [
  "da_dacy_small_trf-0.2.0",
  "da_dacy_medium_trf-0.2.0",
  "da_dacy_large_trf-0.2.0",
] as const
export const POPOVER_VIEWPORT_MARGIN_PX = 12
export const POPOVER_ESTIMATED_HEIGHT_PX = 280
export const PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS = "max-w-[42ch]"
export const SAVED_NOTES_STORAGE_KEY = "danote.saved-notes.v1"
export const NOTE_AUTOSAVE_DEBOUNCE_MS = 900

export type NlpModelOption = (typeof NLP_MODEL_OPTIONS)[number]
