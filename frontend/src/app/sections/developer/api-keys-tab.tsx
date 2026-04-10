import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type ApiKeysTabProps = {
  translationProvider: "deepl" | "azure"
  translationProviderOptions: readonly ("deepl" | "azure")[]
  developerTranslationAzureApiKey: string
  developerTranslationAzureRegion: string
  developerTranslationAzureEndpoint: string
  developerTranslationDeeplApiKey: string
  developerTranslationDeeplEndpoint: string
  developerTtsAzureApiKey: string
  developerTtsAzureRegion: string
  developerTtsAzureEndpoint: string
  developerGeminiApiKey: string
  isSavingDeveloperApiKeys: boolean
  onTranslationProviderChange: (value: "deepl" | "azure") => void
  onDeveloperTranslationAzureApiKeyChange: (value: string) => void
  onDeveloperTranslationAzureRegionChange: (value: string) => void
  onDeveloperTranslationAzureEndpointChange: (value: string) => void
  onDeveloperTranslationDeeplApiKeyChange: (value: string) => void
  onDeveloperTranslationDeeplEndpointChange: (value: string) => void
  onDeveloperTtsAzureApiKeyChange: (value: string) => void
  onDeveloperTtsAzureRegionChange: (value: string) => void
  onDeveloperTtsAzureEndpointChange: (value: string) => void
  onDeveloperGeminiApiKeyChange: (value: string) => void
  onSaveDeveloperApiKeys: () => void
}

export function ApiKeysTab({
  translationProvider,
  translationProviderOptions,
  developerTranslationAzureApiKey,
  developerTranslationAzureRegion,
  developerTranslationAzureEndpoint,
  developerTranslationDeeplApiKey,
  developerTranslationDeeplEndpoint,
  developerTtsAzureApiKey,
  developerTtsAzureRegion,
  developerTtsAzureEndpoint,
  developerGeminiApiKey,
  isSavingDeveloperApiKeys,
  onTranslationProviderChange,
  onDeveloperTranslationAzureApiKeyChange,
  onDeveloperTranslationAzureRegionChange,
  onDeveloperTranslationAzureEndpointChange,
  onDeveloperTranslationDeeplApiKeyChange,
  onDeveloperTranslationDeeplEndpointChange,
  onDeveloperTtsAzureApiKeyChange,
  onDeveloperTtsAzureRegionChange,
  onDeveloperTtsAzureEndpointChange,
  onDeveloperGeminiApiKeyChange,
  onSaveDeveloperApiKeys,
}: ApiKeysTabProps) {
  return (
    <div className="space-y-6">
      <p className="text-muted-foreground text-xs">
        Keys entered here apply immediately for this backend process and are not persisted to source code.
      </p>

      <Card variant="subtle" className="space-y-3 p-4">
        <p className="text-sm font-medium">Translation</p>
        <div className="space-y-1">
          <Label htmlFor="developer-translation-provider">Provider</Label>
          <Select
            value={translationProvider}
            onValueChange={(value) => onTranslationProviderChange(value as "deepl" | "azure")}
          >
            <SelectTrigger id="developer-translation-provider" aria-label="Translator provider picker" className="w-full max-w-sm">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {translationProviderOptions.map((provider) => (
                <SelectItem key={provider} value={provider}>
                  {provider === "deepl" ? "DeepL" : "Azure Translator"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {translationProvider === "deepl" ? (
          <>
            <div className="space-y-1">
              <Label htmlFor="developer-translation-deepl-key">DeepL API key</Label>
              <Input
                id="developer-translation-deepl-key"
                type="password"
                value={developerTranslationDeeplApiKey}
                onChange={(event) => onDeveloperTranslationDeeplApiKeyChange(event.target.value)}
                placeholder="Paste DeepL key"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="developer-translation-deepl-endpoint">DeepL endpoint (optional)</Label>
              <Input
                id="developer-translation-deepl-endpoint"
                value={developerTranslationDeeplEndpoint}
                onChange={(event) => onDeveloperTranslationDeeplEndpointChange(event.target.value)}
                placeholder="https://api-free.deepl.com"
              />
            </div>
          </>
        ) : (
          <>
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
          </>
        )}
      </Card>

      <Card variant="subtle" className="space-y-3 p-4">
        <p className="text-sm font-medium">Text-to-speech</p>
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
            placeholder="https://&lt;resource&gt;.cognitiveservices.azure.com"
          />
        </div>
      </Card>

      <Card variant="subtle" className="space-y-3 p-4">
        <p className="text-sm font-medium">Gemini</p>
        <div className="space-y-1">
          <Label htmlFor="developer-gemini-key">Gemini API key</Label>
          <Input
            id="developer-gemini-key"
            type="password"
            value={developerGeminiApiKey}
            onChange={(event) => onDeveloperGeminiApiKeyChange(event.target.value)}
            placeholder="Paste Gemini key"
          />
        </div>
      </Card>

      <Button type="button" size="sm" onClick={onSaveDeveloperApiKeys} disabled={isSavingDeveloperApiKeys}>
        {isSavingDeveloperApiKeys ? "Saving..." : "Apply runtime API keys"}
      </Button>
    </div>
  )
}