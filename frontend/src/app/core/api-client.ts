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

function buildNetworkErrorMessage(fallback: string, backendUrl: string): string {
  const trimmedFallback = fallback.trim().replace(/\.+$/u, "")
  return `${trimmedFallback}. Could not reach the backend at ${backendUrl}. Check that it is running and try again.`
}

function mapFetchErrorToMessage(
  error: unknown,
  fallback: string,
  backendUrl: string,
): string {
  if (!(error instanceof Error)) {
    return buildNetworkErrorMessage(fallback, backendUrl)
  }

  const normalizedMessage = error.message.trim().toLocaleLowerCase("en-US")
  if (
    normalizedMessage === "failed to fetch"
    || normalizedMessage === "load failed"
    || normalizedMessage.includes("networkerror")
  ) {
    return buildNetworkErrorMessage(fallback, backendUrl)
  }

  return error.message
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

  async function performFetch(path: string, init: RequestInit | undefined, fallback: string): Promise<Response> {
    try {
      return await fetch(`${backendUrl}${path}`, init)
    } catch (error) {
      throw new ApiRequestError(mapFetchErrorToMessage(error, fallback, backendUrl), 0)
    }
  }

  async function requestJson<T>(
    path: string,
    init: RequestInit | undefined,
    fallback: string,
  ): Promise<T> {
    const response = await performFetch(path, init, fallback)
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
    const response = await performFetch(path, init, fallback)
    if (!response.ok) {
      throw new ApiRequestError(await readErrorMessage(response, fallback), response.status)
    }
    return response
  }

  async function tryGetJson<T>(path: string, init?: RequestInit): Promise<T | null> {
    const response = await performFetch(path, init, "Could not load data.")
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
