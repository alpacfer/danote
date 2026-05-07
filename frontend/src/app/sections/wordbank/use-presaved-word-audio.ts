import { useCallback, useRef, useState } from "react"

import { BACKEND_URL } from "@/app/core"

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
        const res = await fetch(
          `${BACKEND_URL}/api/wordbank/presaved-words/pronunciation?term=${encodeURIComponent(key)}`,
        )
        if (!res.ok) return
        url = URL.createObjectURL(await res.blob())
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
