import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  apiStatusBadgeClass,
  humanizeApiStatus,
  type ApiStatusItem,
  type ConnectionStatus,
  type NlpModelOption,
} from "@/app/core"

export type DeveloperSectionProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
  selectedNlpModel: NlpModelOption
  nlpModelOptions: readonly NlpModelOption[]
  developerTranslationAzureApiKey: string
  developerTranslationAzureRegion: string
  developerTranslationAzureEndpoint: string
  developerTtsAzureApiKey: string
  developerTtsAzureRegion: string
  developerTtsAzureEndpoint: string
  developerVerificationGeminiApiKey: string
  isSavingDeveloperApiKeys: boolean
  isResettingDatabase: boolean
  onSelectedNlpModelChange: (value: NlpModelOption) => void
  onDeveloperTranslationAzureApiKeyChange: (value: string) => void
  onDeveloperTranslationAzureRegionChange: (value: string) => void
  onDeveloperTranslationAzureEndpointChange: (value: string) => void
  onDeveloperTtsAzureApiKeyChange: (value: string) => void
  onDeveloperTtsAzureRegionChange: (value: string) => void
  onDeveloperTtsAzureEndpointChange: (value: string) => void
  onDeveloperVerificationGeminiApiKeyChange: (value: string) => void
  onSaveDeveloperApiKeys: () => void
  onResetDatabase: () => void
}

export function DeveloperSection({
  badgeVariant,
  status,
  backendUrl,
  apiStatusItems,
  selectedNlpModel,
  nlpModelOptions,
  developerTranslationAzureApiKey,
  developerTranslationAzureRegion,
  developerTranslationAzureEndpoint,
  developerTtsAzureApiKey,
  developerTtsAzureRegion,
  developerTtsAzureEndpoint,
  developerVerificationGeminiApiKey,
  isSavingDeveloperApiKeys,
  isResettingDatabase,
  onSelectedNlpModelChange,
  onDeveloperTranslationAzureApiKeyChange,
  onDeveloperTranslationAzureRegionChange,
  onDeveloperTranslationAzureEndpointChange,
  onDeveloperTtsAzureApiKeyChange,
  onDeveloperTtsAzureRegionChange,
  onDeveloperTtsAzureEndpointChange,
  onDeveloperVerificationGeminiApiKeyChange,
  onSaveDeveloperApiKeys,
  onResetDatabase,
}: DeveloperSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Developer</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm">Backend status</span>
          <Badge variant={badgeVariant} aria-label="backend-connection-status">
            {status}
          </Badge>
        </div>
        <div className="text-muted-foreground text-sm">
          Backend: <code>{backendUrl}</code>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">API status</p>
          <div className="space-y-2" aria-label="api-status-list">
            {apiStatusItems.map((item) => (
              <div key={item.name} className="rounded-md border p-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm">{item.label}</span>
                  <Badge variant="outline" className={apiStatusBadgeClass(item.status)}>
                    {humanizeApiStatus(item.status)}
                  </Badge>
                </div>
                {item.message ? (
                  <p className="text-muted-foreground mt-1 text-xs">{item.message}</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">NLP model</p>
          <Select value={selectedNlpModel} onValueChange={(value) => onSelectedNlpModelChange(value as NlpModelOption)}>
            <SelectTrigger aria-label="NLP model picker" className="w-full max-w-sm">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {nlpModelOptions.map((model) => (
                <SelectItem key={model} value={model}>
                  {model}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-muted-foreground text-xs">
            Preferred model for local benchmarking. Backend default remains <code>da_dacy_small_trf-0.2.0</code> unless
            <code> DANOTE_NLP_MODEL</code> is set before startup.
          </p>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Runtime API keys</p>
          <p className="text-muted-foreground text-xs">
            Keys entered here apply immediately for this backend process and are not persisted to source code.
          </p>
          <div className="space-y-1">
            <Label htmlFor="developer-translation-azure-key">Azure Translator API key</Label>
            <Input
              id="developer-translation-azure-key"
              type="password"
              value={developerTranslationAzureApiKey}
              onChange={(event) => onDeveloperTranslationAzureApiKeyChange(event.target.value)}
              placeholder="Paste Azure Translator key"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-translation-azure-region">Azure Translator region</Label>
            <Input
              id="developer-translation-azure-region"
              value={developerTranslationAzureRegion}
              onChange={(event) => onDeveloperTranslationAzureRegionChange(event.target.value)}
              placeholder="e.g. westeurope"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-translation-azure-endpoint">Azure Translator endpoint (optional)</Label>
            <Input
              id="developer-translation-azure-endpoint"
              value={developerTranslationAzureEndpoint}
              onChange={(event) => onDeveloperTranslationAzureEndpointChange(event.target.value)}
              placeholder="https://api.cognitive.microsofttranslator.com"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-tts-azure-key">Azure Speech API key</Label>
            <Input
              id="developer-tts-azure-key"
              type="password"
              value={developerTtsAzureApiKey}
              onChange={(event) => onDeveloperTtsAzureApiKeyChange(event.target.value)}
              placeholder="Paste Azure Speech key"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-tts-azure-region">Azure Speech region</Label>
            <Input
              id="developer-tts-azure-region"
              value={developerTtsAzureRegion}
              onChange={(event) => onDeveloperTtsAzureRegionChange(event.target.value)}
              placeholder="e.g. westeurope"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-tts-azure-endpoint">Azure Speech endpoint (optional)</Label>
            <Input
              id="developer-tts-azure-endpoint"
              value={developerTtsAzureEndpoint}
              onChange={(event) => onDeveloperTtsAzureEndpointChange(event.target.value)}
              placeholder="https://<resource>.cognitiveservices.azure.com"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="developer-verification-key">Word verification Gemini key</Label>
            <Input
              id="developer-verification-key"
              type="password"
              value={developerVerificationGeminiApiKey}
              onChange={(event) => onDeveloperVerificationGeminiApiKeyChange(event.target.value)}
              placeholder="Paste Gemini key for verification"
            />
          </div>
          <Button type="button" size="sm" onClick={onSaveDeveloperApiKeys} disabled={isSavingDeveloperApiKeys}>
            {isSavingDeveloperApiKeys ? "Saving..." : "Apply runtime API keys"}
          </Button>
        </div>
        <Button
          type="button"
          variant="destructive"
          size="sm"
          disabled={isResettingDatabase}
          onClick={onResetDatabase}
        >
          {isResettingDatabase ? "Deleting..." : "Delete complete DB"}
        </Button>
      </CardContent>
    </Card>
  )
}
