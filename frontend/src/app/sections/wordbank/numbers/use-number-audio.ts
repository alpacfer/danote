import { useCallback, useRef, useState } from "react"

import { BACKEND_URL } from "@/app/core"

export function useNumberAudio() {
  const [loadingByTerm, setLoadingByTerm] = useState<Record<string, boolean>>({})
  const cachedUrls = useRef(new Map<string, string>())
  const activeAudio = useRef<HTMLAudioElement | null>(null)

  const playTerm = useCallback(async (term: string) => {
    setLoadingByTerm((prev) => ({ ...prev, [term]: true }))
    try {
      let url = cachedUrls.current.get(term)
      if (!url) {
        const res = await fetch(
          `${BACKEND_URL}/api/wordbank/numbers/pronunciation?term=${encodeURIComponent(term)}`,
        )
        if (!res.ok) return
        url = URL.createObjectURL(await res.blob())
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
