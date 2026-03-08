import { type DeveloperServiceProbeResponse } from "@/app/core"

type DeveloperProbeResultProps = {
  ariaLabel: string
  result: DeveloperServiceProbeResponse | null
}

export function DeveloperProbeResult({ ariaLabel, result }: DeveloperProbeResultProps) {
  if (!result) {
    return null
  }

  return (
    <div aria-label={ariaLabel} className="rounded-md border p-2 text-sm">
      <p>
        <strong>Status:</strong> {result.status}
      </p>
      <p>
        <strong>Probe:</strong> {result.probe_input}
      </p>
      {result.result_text ? (
        <p>
          <strong>Result:</strong> {result.result_text}
        </p>
      ) : null}
      <p className="text-muted-foreground">{result.message}</p>
    </div>
  )
}
