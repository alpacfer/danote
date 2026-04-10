# Developer Page Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat developer page with a tabbed layout using shadcn Tabs, add a sticky "Delete DB + Clear cache" action bar, and implement browser cache clearing.

**Architecture:** Split the monolithic `developer-section.tsx` into a `developer/` directory with one file per tab component. The main `developer-section.tsx` renders Tabs + a sticky bottom bar. Cache clearing logic is added to the existing `resetDatabase` function in the hook. No backend changes.

**Tech Stack:** React 19, TypeScript, shadcn/ui Tabs, Tailwind CSS v4

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/src/app/sections/developer/status-tab.tsx` | Backend connection, API status grid, NLP model selector |
| Create | `frontend/src/app/sections/developer/api-keys-tab.tsx` | Translation provider, API key fields, Apply button |
| Create | `frontend/src/app/sections/developer/probes-tab.tsx` | Service probe buttons + inline results |
| Create | `frontend/src/app/sections/developer/probe-result.tsx` | Reusable probe result display card |
| Create | `frontend/src/app/sections/developer/database-tab.tsx` | DB delete action with explanation |
| Create | `frontend/src/app/sections/developer/developer-section.tsx` | Tabs shell + sticky action bar |
| Create | `frontend/src/app/sections/developer/index.ts` | Barrel export |
| Modify | `frontend/src/app/sections/developer-section-props.ts` | Update import paths |
| Modify | `frontend/src/app/hooks/app/use-developer-settings.ts` | Add cache clearing to resetDatabase |
| Modify | `frontend/src/app/sections/index.ts` | Update developer import path |
| Delete | `frontend/src/app/sections/developer-section.tsx` | Replaced by `developer/` directory |
| Delete | `frontend/src/app/sections/developer-probe-result.tsx` | Moved to `developer/probe-result.tsx` |
| Modify | `frontend/src/app/sections/section-props-adapters.test.ts` | Update import path |

---

### Task 1: Create the developer directory with barrel export and probe-result

**Files:**
- Create: `frontend/src/app/sections/developer/index.ts`
- Create: `frontend/src/app/sections/developer/probe-result.tsx`

- [ ] **Step 1: Create the barrel export**

Create `frontend/src/app/sections/developer/index.ts`:

```typescript
export { DeveloperSection } from "./developer-section"
export { DeveloperProbeResult } from "./probe-result"
```

- [ ] **Step 2: Create probe-result.tsx (moved from root)**

Create `frontend/src/app/sections/developer/probe-result.tsx` — copy the exact content from the existing `frontend/src/app/sections/developer-probe-result.tsx`:

```typescript
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
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/sections/developer/index.ts frontend/src/app/sections/developer/probe-result.tsx
git commit -m "feat(developer): create developer directory with barrel export and probe-result"
```

---

### Task 2: Create the StatusTab component

**Files:**
- Create: `frontend/src/app/sections/developer/status-tab.tsx`

- [ ] **Step 1: Write the StatusTab component**

This tab shows backend connection info, a 2x2 service status grid, and the NLP model selector. It receives only the props it needs.

Create `frontend/src/app/sections/developer/status-tab.tsx`:

```typescript
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
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

type StatusTabProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
  selectedNlpModel: NlpModelOption
  nlpModelOptions: readonly NlpModelOption[]
  onSelectedNlpModelChange: (value: NlpModelOption) => void
}

export function StatusTab({
  badgeVariant,
  status,
  backendUrl,
  apiStatusItems,
  selectedNlpModel,
  nlpModelOptions,
  onSelectedNlpModelChange,
}: StatusTabProps) {
  return (
    <div className="space-y-6">
      <Card variant="subtle" className="flex items-center justify-between p-4">
        <div>
          <p className="text-sm font-medium">Backend connection</p>
          <p className="text-muted-foreground mt-1 text-xs">
            <code>{backendUrl}</code>
          </p>
        </div>
        <Badge variant={badgeVariant} aria-label="backend-connection-status">
          {status}
        </Badge>
      </Card>

      <div>
        <p className="mb-3 text-sm font-medium">Service status</p>
        <div className="grid grid-cols-2 gap-2" aria-label="api-status-list">
          {apiStatusItems.map((item) => (
            <Card key={item.name} variant="subtle" className="flex items-center justify-between gap-2 p-3">
              <span className="text-sm">{item.label}</span>
              <Badge variant="outline" className={apiStatusBadgeClass(item.status)}>
                {humanizeApiStatus(item.status)}
              </Badge>
            </Card>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-sm font-medium">NLP model</Label>
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
          Preferred model for local benchmarking. Backend default remains <code>da_dacy_small_trf-0.2.0</code> unless{" "}
          <code>DANOTE_NLP_MODEL</code> is set before startup.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/developer/status-tab.tsx
git commit -m "feat(developer): add StatusTab component with connection, status grid, and NLP selector"
```

---

### Task 3: Create the ApiKeysTab component

**Files:**
- Create: `frontend/src/app/sections/developer/api-keys-tab.tsx`

- [ ] **Step 1: Write the ApiKeysTab component**

This tab groups the translation provider selector, key fields grouped by service (Translation, TTS, Gemini), and the Apply button.

Create `frontend/src/app/sections/developer/api-keys-tab.tsx`:

```typescript
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
            placeholder="https://<resource>.cognitiveservices.azure.com"
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/developer/api-keys-tab.tsx
git commit -m "feat(developer): add ApiKeysTab with grouped key fields per service"
```

---

### Task 4: Create the ProbesTab component

**Files:**
- Create: `frontend/src/app/sections/developer/probes-tab.tsx`

- [ ] **Step 1: Write the ProbesTab component**

Test buttons + inline results, grouped by service.

Create `frontend/src/app/sections/developer/probes-tab.tsx`:

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/developer/probes-tab.tsx
git commit -m "feat(developer): add ProbesTab with grouped probe buttons and results"
```

---

### Task 5: Create the DatabaseTab component

**Files:**
- Create: `frontend/src/app/sections/developer/database-tab.tsx`

- [ ] **Step 1: Write the DatabaseTab component**

Full delete action with explanation of what gets cleared.

Create `frontend/src/app/sections/developer/database-tab.tsx`:

```typescript
import { Button } from "@/components/ui/button"

type DatabaseTabProps = {
  isResettingDatabase: boolean
  onResetDatabase: () => void
}

export function DatabaseTab({
  isResettingDatabase,
  onResetDatabase,
}: DatabaseTabProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">Reset database and cache</p>
      <p className="text-muted-foreground text-xs">
        Deletes the SQLite database and clears all browser storage (localStorage, sessionStorage,
        service workers, Cache API). This cannot be undone.
      </p>
      <Button
        type="button"
        variant="destructive"
        disabled={isResettingDatabase}
        onClick={onResetDatabase}
      >
        {isResettingDatabase ? "Deleting..." : "Delete DB + Clear cache"}
      </Button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/developer/database-tab.tsx
git commit -m "feat(developer): add DatabaseTab with delete action and cache clearing explanation"
```

---

### Task 6: Create the main DeveloperSection with Tabs + sticky bar

**Files:**
- Create: `frontend/src/app/sections/developer/developer-section.tsx`

- [ ] **Step 1: Write the main DeveloperSection component**

This is the tabs shell that composes all tab components and renders the sticky action bar.

Create `frontend/src/app/sections/developer/developer-section.tsx`:

```typescript
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
        <TabsContent value="status">
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/developer/developer-section.tsx
git commit -m "feat(developer): add main DeveloperSection with Tabs and sticky action bar"
```

---

### Task 7: Add cache clearing logic to the hook

**Files:**
- Modify: `frontend/src/app/hooks/app/use-developer-settings.ts`

- [ ] **Step 1: Add clearBrowserCache helper**

Add a helper function before `resetDatabase` in `frontend/src/app/hooks/app/use-developer-settings.ts`. Insert after line 77 (the `apiClient` useMemo):

```typescript
async function clearBrowserCache(): Promise<void> {
  try {
    localStorage.clear()
  } catch { /* storage may be inaccessible */ }
  try {
    sessionStorage.clear()
  } catch { /* storage may be inaccessible */ }
  try {
    if ("serviceWorker" in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations()
      for (const registration of registrations) {
        await registration.unregister()
      }
    }
  } catch { /* service worker may not be available */ }
  try {
    if ("caches" in window) {
      const cacheNames = await caches.keys()
      await Promise.all(cacheNames.map((name) => caches.delete(name)))
    }
  } catch { /* Cache API may not be available */ }
}
```

- [ ] **Step 2: Update resetDatabase to clear cache and reload**

Replace the existing `resetDatabase` function (lines 79-101) with:

```typescript
  async function resetDatabase() {
    const shouldReset = window.confirm(
      "This will delete the database and clear all browser cache. Continue?",
    )
    if (!shouldReset) {
      return
    }

    setIsResettingDatabase(true)
    try {
      const payload = await apiClient.deleteJson<ResetDatabaseResponse>(
        "/api/wordbank/database",
        "Could not reset database.",
      )
      onNotifySuccess(payload.message)
      onDatabaseReset()
      await clearBrowserCache()
      window.location.reload()
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not reset database."
      onNotifyError(message)
    } finally {
      setIsResettingDatabase(false)
    }
  }
```

Note: `window.location.reload()` is called after cache clearing. If the page reloads before `setIsResettingDatabase(false)` runs, that's fine — the state is gone on reload anyway.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/hooks/app/use-developer-settings.ts
git commit -m "feat(developer): add cache clearing (localStorage, sessionStorage, service workers, Cache API) to DB reset"
```

---

### Task 8: Wire up the new structure — update imports and delete old files

**Files:**
- Modify: `frontend/src/app/sections/index.ts`
- Modify: `frontend/src/app/sections/developer-section-props.ts`
- Modify: `frontend/src/app/sections/section-props-adapters.test.ts`
- Delete: `frontend/src/app/sections/developer-section.tsx`
- Delete: `frontend/src/app/sections/developer-probe-result.tsx`

- [ ] **Step 1: Update the barrel export in `frontend/src/app/sections/index.ts`**

Change line 1 from:
```typescript
export * from "./developer-section"
```
to:
```typescript
export * from "./developer"
```

- [ ] **Step 2: Update import in `frontend/src/app/sections/developer-section-props.ts`**

Change line 4 from:
```typescript
import { DeveloperSection } from "@/app/sections/developer-section"
```
to:
```typescript
import { DeveloperSection } from "@/app/sections/developer"
```

- [ ] **Step 3: Update import in `frontend/src/app/sections/section-props-adapters.test.ts`**

Change line 4 from:
```typescript
import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
```
to:
```typescript
import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
```

(No change needed for this file — it imports from the props adapter, not the section directly.)

- [ ] **Step 4: Delete the old files**

```bash
rm frontend/src/app/sections/developer-section.tsx
rm frontend/src/app/sections/developer-probe-result.tsx
```

- [ ] **Step 5: Verify the app compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors. All imports resolve correctly.

- [ ] **Step 6: Verify existing tests pass**

Run: `cd frontend && npx vitest run src/app/sections/section-props-adapters.test.ts`
Expected: All tests pass (the props adapter test doesn't import from the old files directly).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/sections/index.ts frontend/src/app/sections/developer-section-props.ts
git rm frontend/src/app/sections/developer-section.tsx frontend/src/app/sections/developer-probe-result.tsx
git commit -m "refactor(developer): wire up new tabbed layout, delete old flat section files"
```

---

### Task 9: Run lint and maintainability checks

**Files:** None (verification only)

- [ ] **Step 1: Run lint**

Run: `cd frontend && npx eslint src/app/sections/developer/ src/app/hooks/app/use-developer-settings.ts --max-warnings 0`
Expected: No warnings or errors.

- [ ] **Step 2: Run maintainability check**

Run: `make maintainability-check`
Expected: All files within size limits. Verify that no new files exceed 300 lines (target) and none exceed 450 lines (hard limit).

- [ ] **Step 3: Run full frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

- [ ] **Step 4: Commit if any fixes were needed**

Only commit if lint or checks required fixes.
