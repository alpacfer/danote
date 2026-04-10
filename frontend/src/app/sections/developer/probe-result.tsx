import { Card } from "@/components/ui/card"
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
    <Card aria-label={ariaLabel} variant="subtle" className="p-2 text-sm">
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
    </Card>
  )
}