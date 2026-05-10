import { useCallback, useRef, useState } from "react"

import { fetchPresavedWordPronunciationBlob } from "@/app/core/audio-api"

export function usePresavedWordAudio() {
  const [loadingByTerm, setLoadingByTerm] = useState<Record<string, boolean>>({})
  const cachedUrls = useRef(new Map<string, string>())
  const activeAudio = useRef<HTMLAudioElement | null>(null)

  const playTerm = useCallback(async (term: string) => {
    const key = term.toLowerCase()
    setLoadingByTerm((prev) => ({ ...prev, [key]: true }))
    try {
      let url = cachedUrls.current.get(key)
      if (!url) {
        const blob = await fetchPresavedWordPronunciationBlob(key)
        if (!blob) return
        url = URL.createObjectURL(blob)
        cachedUrls.current.set(key, url)
      }
      activeAudio.current?.pause()
      const audio = new Audio(url)
      activeAudio.current = audio
      await audio.play()
    } finally {
      setLoadingByTerm((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }, [])

  return { loadingByTerm, playTerm }
}
