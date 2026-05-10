import { useCallback, useRef, useState } from "react"

import {
  fetchNumbersPronunciationBlob,
  fetchPresavedWordPronunciationBlob,
  fetchWordPronunciationBlob,
} from "@/app/core/audio-api"

// Plays pronunciation audio for built-in pinned-page words. Falls back silently
// if the form has no stored pronunciation (older built-ins are seeded; newer
// function words rely on the standard surface-form pronunciation pipeline).
export function usePinnedPageAudio() {
  const [loadingByForm, setLoadingByForm] = useState<Record<string, boolean>>({})
  const cachedUrls = useRef(new Map<string, string>())
  const activeAudio = useRef<HTMLAudioElement | null>(null)

  const playForm = useCallback(async (form: string) => {
    const term = form.trim().toLowerCase()
    if (!term) return
    setLoadingByForm((prev) => ({ ...prev, [term]: true }))
    try {
      let url = cachedUrls.current.get(term)
      if (!url) {
        // Try the seeded numbers endpoint first for numerals; the regular
        // pronunciation endpoint requires the form to be in surface_forms.
        const numbersBlob = await fetchNumbersPronunciationBlob(term)
        if (numbersBlob) {
          url = URL.createObjectURL(numbersBlob)
        } else {
          const presavedBlob = await fetchPresavedWordPronunciationBlob(term)
          if (presavedBlob) {
            url = URL.createObjectURL(presavedBlob)
          } else {
            const blob = await fetchWordPronunciationBlob(term)
            if (!blob) return
            url = URL.createObjectURL(blob)
          }
        }
        cachedUrls.current.set(term, url)
      }
      activeAudio.current?.pause()
      const audio = new Audio(url)
      activeAudio.current = audio
      await audio.play()
    } finally {
      setLoadingByForm((prev) => {
        const next = { ...prev }
        delete next[term]
        return next
      })
    }
  }, [])

  return { loadingByForm, playForm }
}
