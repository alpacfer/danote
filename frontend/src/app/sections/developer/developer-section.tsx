import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { type DeveloperServiceProbeResponse, type GeminiProbeResponse, type ApiStatusItem, type ConnectionStatus, type NlpModelOption } from "@/app/core"
import { ApiKeysTab } from "./api-keys-tab"
import { DatabaseTab } from "./database-tab"
import { ProbesTab } from "./probes-tab"
import { StatusTab } from "./status-tab"

export type DeveloperSectionProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
  selectedNlpModel: NlpModelOption
  nlpModelOptions: readonly NlpModelOption[]
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
  onSelectedNlpModelChange: (value: NlpModelOption) => void
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
}

export function DeveloperSection(props: DeveloperSectionProps) {
  return (
    <div className="flex flex-col">
      <Tabs defaultValue="status">
        <TabsList>
          <TabsTrigger value="status">Status</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="probes">Probes</TabsTrigger>
          <TabsTrigger value="database">Database</TabsTrigger>
        </TabsList>
        <TabsContent value="status" forceMount>
          <StatusTab
            badgeVariant={props.badgeVariant}
            status={props.status}
            backendUrl={props.backendUrl}
            apiStatusItems={props.apiStatusItems}
            selectedNlpModel={props.selectedNlpModel}
            nlpModelOptions={props.nlpModelOptions}
            onSelectedNlpModelChange={props.onSelectedNlpModelChange}
          />
        </TabsContent>
        <TabsContent value="api-keys" forceMount>
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
        <TabsContent value="probes" forceMount>
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
        <TabsContent value="database" forceMount>
          <DatabaseTab
            isResettingDatabase={props.isResettingDatabase}
            onResetDatabase={props.onResetDatabase}
          />
        </TabsContent>
      </Tabs>
      <div className="sticky bottom-0 mt-4 flex items-center justify-between border-t py-3">
        <span className="text-muted-foreground text-sm">Danger zone</span>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground text-xs">Deletes database and clears all browser cache</span>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            disabled={props.isResettingDatabase}
            onClick={props.onResetDatabase}
          >
            {props.isResettingDatabase ? "Deleting..." : "Delete DB + Clear cache"}
          </Button>
        </div>
      </div>
    </div>
  )
}
