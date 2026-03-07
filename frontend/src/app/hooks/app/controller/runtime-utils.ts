import { createApiClient, type TokenFeedbackPayload } from "@/app/core"

export async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // Fall through to default message.
  }
  return fallback
}

export async function postTokenFeedback(backendUrl: string, payload: TokenFeedbackPayload) {
  try {
    const apiClient = createApiClient({ backendUrl })
    await apiClient.postJson("/api/tokens/feedback", payload, "Could not send token feedback.")
  } catch {
    // Feedback logging is best-effort in v1.
  }
}
