import { type ApiRuntimeStatus } from "@/app/core/types-api"

export function normalizeApiRuntimeStatus(value: string | undefined): ApiRuntimeStatus {
  const normalized = (value ?? "").trim().toLocaleLowerCase("en-US")
  if (normalized === "ok") {
    return "ok"
  }
  if (normalized === "degraded") {
    return "degraded"
  }
  if (normalized === "inactive") {
    return "inactive"
  }
  if (normalized === "missing_key") {
    return "missing_key"
  }
  if (normalized === "disabled") {
    return "disabled"
  }
  return "unknown"
}

export function apiStatusBadgeClass(status: ApiRuntimeStatus): string {
  if (status === "ok") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700"
  }
  if (status === "degraded" || status === "missing_key") {
    return "border-amber-300 bg-amber-50 text-amber-700"
  }
  if (status === "inactive" || status === "disabled") {
    return "border-zinc-300 bg-zinc-50 text-zinc-700"
  }
  return "border-red-300 bg-red-50 text-red-700"
}

export function humanizeApiStatus(status: ApiRuntimeStatus): string {
  if (status === "missing_key") {
    return "missing key"
  }
  return status
}

export function humanizeApiName(name: string): string {
  if (name === "backend") {
    return "Backend API"
  }
  if (name === "azure_translator") {
    return "Azure Translator API"
  }
  if (name === "deepl_translator") {
    return "DeepL API"
  }
  if (name === "azure_speech") {
    return "Azure Speech API"
  }
  return name
}
