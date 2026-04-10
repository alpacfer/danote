import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { type DeveloperServiceProbeResponse, type GeminiProbeResponse } from "@/app/core"
import { DeveloperProbeResult } from "./probe-result"

type ProbesTabProps = {
  translationProvider: "deepl" | "azure"
  isTestingTranslation: boolean
  translationProbeResult: DeveloperServiceProbeResponse | null
  isTestingSpeech: boolean
  speechProbeResult: DeveloperServiceProbeResponse | null
  isTestingGemini: boolean
  geminiProbeResult: GeminiProbeResponse | null
  onRunTranslationProbe: () => void
  onRunSpeechProbe: () => void
  onRunGeminiProbe: () => void
}

export function ProbesTab({
  translationProvider,
  isTestingTranslation,
  translationProbeResult,
  isTestingSpeech,
  speechProbeResult,
  isTestingGemini,
  geminiProbeResult,
  onRunTranslationProbe,
  onRunSpeechProbe,
  onRunGeminiProbe,
}: ProbesTabProps) {
  const translationLabel = translationProvider === "deepl" ? "DeepL" : "Azure Translator"

  return (
    <div className="space-y-6">
      <Card variant="subtle" className="space-y-2 p-4">
        <p className="text-sm font-medium">{translationLabel}</p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onRunTranslationProbe}
          disabled={isTestingTranslation}
        >
          {isTestingTranslation ? `Testing ${translationLabel}...` : `Test ${translationLabel}`}
        </Button>
        <DeveloperProbeResult ariaLabel="translation-probe-result" result={translationProbeResult} />
      </Card>

      <Card variant="subtle" className="space-y-2 p-4">
        <p className="text-sm font-medium">Azure Speech</p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onRunSpeechProbe}
          disabled={isTestingSpeech}
        >
          {isTestingSpeech ? "Testing Azure Speech..." : "Test Azure Speech"}
        </Button>
        <DeveloperProbeResult ariaLabel="speech-probe-result" result={speechProbeResult} />
      </Card>

      <Card variant="subtle" className="space-y-2 p-4">
        <p className="text-sm font-medium">Gemini</p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onRunGeminiProbe}
          disabled={isTestingGemini}
        >
          {isTestingGemini ? "Testing Gemini..." : "Test Gemini"}
        </Button>
        <DeveloperProbeResult ariaLabel="gemini-probe-result" result={geminiProbeResult} />
      </Card>
    </div>
  )
}