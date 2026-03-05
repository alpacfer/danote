import { useMemo } from "react"

import {
  humanizeApiName,
  normalizeApiRuntimeStatus,
  type ApiStatusItem,
  type ConnectionStatus,
  type HealthPayload,
  type WordbankLemma,
} from "@/app/core"

export function useGroupedWordbankLemmas(lemmas: WordbankLemma[]) {
  return useMemo(() => {
    const collator = new Intl.Collator("da", { sensitivity: "base" })
    const sortedLemmas = [...lemmas].sort((left, right) => collator.compare(left.lemma, right.lemma))
    const groups = new Map<string, WordbankLemma[]>()

    for (const lemma of sortedLemmas) {
      const normalizedLemma = lemma.lemma.trim()
      if (!normalizedLemma) {
        continue
      }
      const groupLetter = normalizedLemma[0].toLocaleUpperCase("da-DK")
      if (!groups.has(groupLetter)) {
        groups.set(groupLetter, [])
      }
      groups.get(groupLetter)?.push(lemma)
    }

    return Array.from(groups.entries())
      .sort(([left], [right]) => collator.compare(left, right))
      .map(([letter, items]) => ({ letter, items }))
  }, [lemmas])
}

export function useApiStatusItems(healthPayload: HealthPayload | null, status: ConnectionStatus) {
  return useMemo(() => {
    const apis = healthPayload?.apis ?? {}
    const priorityOrder = ["backend", "azure_translator", "azure_speech"]
    const orderedNames = [
      ...priorityOrder.filter((name) => Object.hasOwn(apis, name)),
      ...Object.keys(apis).filter((name) => !priorityOrder.includes(name)).sort(),
    ]

    if (orderedNames.length === 0) {
      return [
        {
          name: "backend",
          label: "Backend API",
          status: status === "connected" ? "ok" : status === "degraded" ? "degraded" : "unknown",
          message: null,
        },
      ] satisfies ApiStatusItem[]
    }

    return orderedNames.map((name) => {
      const entry = apis[name] ?? {}
      return {
        name,
        label: humanizeApiName(name),
        status: normalizeApiRuntimeStatus(entry.status),
        message: entry.message ?? null,
      }
    }) satisfies ApiStatusItem[]
  }, [healthPayload, status])
}
