import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { type DeveloperServiceProbeResponse, type GeminiProbeResponse, type ApiStatusItem, type ConnectionStatus } from "@/app/core"
import { ApiKeysTab } from "./api-keys-tab"
import { DatabaseTab } from "./database-tab"
import { ProbesTab } from "./probes-tab"
import { StatusTab } from "./status-tab"

export type DeveloperSectionProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
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
  isTestingTranslation: boolean
  translationProbeResult: DeveloperServiceProbeResponse | null
  isTestingSpeech: boolean
  speechProbeResult: DeveloperServiceProbeResponse | null
  isTestingGemini: boolean
  geminiProbeResult: GeminiProbeResponse | null
  isResettingDatabase: boolean
  isSeedingNumbersAudio: boolean
  isSeedingPresavedWordsAudio: boolean
  isRegeneratingPresavedWordsAudio: boolean
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
  onRunTranslationProbe: () => void
  onRunSpeechProbe: () => void
  onRunGeminiProbe: () => void
  onResetDatabase: () => void
  onSeedPresavedWordsAudio: () => void
  onRegeneratePresavedWordsAudio: () => void
}

export function DeveloperSection(props: DeveloperSectionProps) {
  return (
    <Tabs defaultValue="status">
      <div className="flex flex-col gap-4">
        <TabsList>
          <TabsTrigger value="status">Status</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="probes">Probes</TabsTrigger>
          <TabsTrigger value="database">Database</TabsTrigger>
        </TabsList>
        <TabsContent value="status">
          <StatusTab
            badgeVariant={props.badgeVariant}
            status={props.status}
            backendUrl={props.backendUrl}
            apiStatusItems={props.apiStatusItems}
          />
        </TabsContent>
        <TabsContent value="api-keys">
          <ApiKeysTab
            translationProvider={props.translationProvider}
            translationProviderOptions={props.translationProviderOptions}
            developerTranslationAzureApiKey={props.developerTranslationAzureApiKey}
            developerTranslationAzureRegion={props.developerTranslationAzureRegion}
            developerTranslationAzureEndpoint={props.developerTranslationAzureEndpoint}
            developerTranslationDeeplApiKey={props.developerTranslationDeeplApiKey}
            developerTranslationDeeplEndpoint={props.developerTranslationDeeplEndpoint}
            developerTtsAzureApiKey={props.developerTtsAzureApiKey}
            developerTtsAzureRegion={props.developerTtsAzureRegion}
            developerTtsAzureEndpoint={props.developerTtsAzureEndpoint}
            developerGeminiApiKey={props.developerGeminiApiKey}
            isSavingDeveloperApiKeys={props.isSavingDeveloperApiKeys}
            onTranslationProviderChange={props.onTranslationProviderChange}
            onDeveloperTranslationAzureApiKeyChange={props.onDeveloperTranslationAzureApiKeyChange}
            onDeveloperTranslationAzureRegionChange={props.onDeveloperTranslationAzureRegionChange}
            onDeveloperTranslationAzureEndpointChange={props.onDeveloperTranslationAzureEndpointChange}
            onDeveloperTranslationDeeplApiKeyChange={props.onDeveloperTranslationDeeplApiKeyChange}
            onDeveloperTranslationDeeplEndpointChange={props.onDeveloperTranslationDeeplEndpointChange}
            onDeveloperTtsAzureApiKeyChange={props.onDeveloperTtsAzureApiKeyChange}
            onDeveloperTtsAzureRegionChange={props.onDeveloperTtsAzureRegionChange}
            onDeveloperTtsAzureEndpointChange={props.onDeveloperTtsAzureEndpointChange}
            onDeveloperGeminiApiKeyChange={props.onDeveloperGeminiApiKeyChange}
            onSaveDeveloperApiKeys={props.onSaveDeveloperApiKeys}
          />
        </TabsContent>
        <TabsContent value="probes">
          <ProbesTab
            translationProvider={props.translationProvider}
            isTestingTranslation={props.isTestingTranslation}
            translationProbeResult={props.translationProbeResult}
            isTestingSpeech={props.isTestingSpeech}
            speechProbeResult={props.speechProbeResult}
            isTestingGemini={props.isTestingGemini}
            geminiProbeResult={props.geminiProbeResult}
            onRunTranslationProbe={props.onRunTranslationProbe}
            onRunSpeechProbe={props.onRunSpeechProbe}
            onRunGeminiProbe={props.onRunGeminiProbe}
          />
        </TabsContent>
        <TabsContent value="database">
          <DatabaseTab
            isResettingDatabase={props.isResettingDatabase}
            isSeedingNumbersAudio={props.isSeedingNumbersAudio}
            isSeedingPresavedWordsAudio={props.isSeedingPresavedWordsAudio}
            isRegeneratingPresavedWordsAudio={props.isRegeneratingPresavedWordsAudio}
            onResetDatabase={props.onResetDatabase}
            onSeedPresavedWordsAudio={props.onSeedPresavedWordsAudio}
            onRegeneratePresavedWordsAudio={props.onRegeneratePresavedWordsAudio}
          />
        </TabsContent>
      </div>
    </Tabs>
  )
}
