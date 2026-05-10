import { BACKEND_URL } from "./constants"

export async function fetchNumbersPronunciationBlob(term: string): Promise<Blob | null> {
  return fetchPronunciationBlob(`/api/wordbank/numbers/pronunciation?term=${encodeURIComponent(term)}`)
}

export async function fetchPresavedWordPronunciationBlob(term: string): Promise<Blob | null> {
  return fetchPronunciationBlob(`/api/wordbank/presaved-words/pronunciation?term=${encodeURIComponent(term)}`)
}

export async function fetchWordPronunciationBlob(form: string): Promise<Blob | null> {
  return fetchPronunciationBlob(`/api/wordbank/pronunciation?form=${encodeURIComponent(form)}`)
}

async function fetchPronunciationBlob(path: string): Promise<Blob | null> {
  const response = await fetch(`${BACKEND_URL}${path}`)
  if (!response.ok) {
    return null
  }
  return response.blob()
}
