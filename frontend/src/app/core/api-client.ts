export type ApiErrorMessageExtractor = (
  response: Response,
  fallback: string,
) => Promise<string>

export class ApiRequestError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

type ApiClientOptions = {
  backendUrl: string
  extractErrorMessage?: ApiErrorMessageExtractor
}

export function createApiClient({
  backendUrl,
  extractErrorMessage,
}: ApiClientOptions) {
  async function readErrorMessage(response: Response, fallback: string): Promise<string> {
    if (extractErrorMessage) {
      return extractErrorMessage(response, fallback)
    }
    return fallback
  }

  async function requestJson<T>(
    path: string,
    init: RequestInit | undefined,
    fallback: string,
  ): Promise<T> {
    const response = await fetch(`${backendUrl}${path}`, init)
    if (!response.ok) {
      throw new ApiRequestError(await readErrorMessage(response, fallback), response.status)
    }
    return (await response.json()) as T
  }

  async function requestBlob(
    path: string,
    init: RequestInit | undefined,
    fallback: string,
  ): Promise<Response> {
    const response = await fetch(`${backendUrl}${path}`, init)
    if (!response.ok) {
      throw new ApiRequestError(await readErrorMessage(response, fallback), response.status)
    }
    return response
  }

  async function tryGetJson<T>(path: string, init?: RequestInit): Promise<T | null> {
    const response = await fetch(`${backendUrl}${path}`, init)
    if (!response.ok) {
      return null
    }
    return (await response.json()) as T
  }

  return {
    getJson<T>(path: string, fallback: string, init?: RequestInit) {
      return requestJson<T>(path, init, fallback)
    },
    postJson<T>(path: string, body: unknown, fallback: string, init?: RequestInit) {
      return requestJson<T>(
        path,
        {
          ...init,
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(init?.headers ?? {}),
          },
          body: JSON.stringify(body),
        },
        fallback,
      )
    },
    deleteJson<T>(path: string, fallback: string, init?: RequestInit) {
      return requestJson<T>(
        path,
        {
          ...init,
          method: "DELETE",
        },
        fallback,
      )
    },
    getBlob(path: string, fallback: string, init?: RequestInit) {
      return requestBlob(path, init, fallback)
    },
    tryGetJson,
  }
}
