import { useCallback, useRef, useState } from "react"

import { fetchNumbersPronunciationBlob } from "@/app/core/audio-api"

export function useNumberAudio() {
  const [loadingByTerm, setLoadingByTerm] = useState<Record<string, boolean>>({})
  const cachedUrls = useRef(new Map<string, string>())
  const activeAudio = useRef<HTMLAudioElement | null>(null)

  const playTerm = useCallback(async (term: string) => {
    setLoadingByTerm((prev) => ({ ...prev, [term]: true }))
    try {
      let url = cachedUrls.current.get(term)
      if (!url) {
        const blob = await fetchNumbersPronunciationBlob(term)
        if (!blob) return
        url = URL.createObjectURL(blob)
        cachedUrls.current.set(term, url)
      }
      activeAudio.current?.pause()
      const audio = new Audio(url)
      activeAudio.current = audio
      await audio.play()
    } finally {
      setLoadingByTerm((prev) => {
        const next = { ...prev }
        delete next[term]
        return next
      })
    }
  }, [])

  return { loadingByTerm, playTerm }
}
