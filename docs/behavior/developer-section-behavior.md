# Developer section behavior

## 1) Entry points

UI components:
- `frontend/src/app/sections/developer-section.tsx`
- `frontend/src/app/sections/developer-probe-result.tsx`

Controller/composition:
- `frontend/src/app/hooks/app/use-app-controller.ts` — wires `developerSettings` into `buildDeveloperSectionProps(...)`, provides `apiProbeStatuses`
- `frontend/src/app/sections/developer-section-props.ts` — adapts state/actions into props, converts async handlers to fire-and-forget callbacks
- `frontend/src/app/hooks/app/use-developer-settings.ts` — owns mutable form state + side-effectful workflows (API key apply, translation/speech/gemini probes, DB reset)

## 2) Connection/API status display

### Backend connection badge

`badgeVariant` from `buildDeveloperSectionProps(...)`: `connected -> secondary`, `degraded -> outline`, `offline -> destructive`. Text = raw connection status.

### API status list rendering

Built by `useApiStatusItems(...)`. Ordering:
1. Preferred: `backend`, `deepl_translator`, `azure_translator`, `azure_speech`, `gemini`
2. Missing from health but in `apiProbeStatuses` → still shown
3. Additional names → alphabetical
4. Fallback: no APIs + no probes → synthetic `backend` row from connection state

### Badge variants per API row

All badges `variant="outline"`. Color via `apiStatusBadgeClass(...)`: `ok ->` green, `degraded`/`missing_key ->` amber, `inactive`/`disabled ->` zinc, `unknown ->` red. Labels humanized by `humanizeApiStatus(...)` (`missing_key` → `missing key`). Service names by `humanizeApiName(...)` (`deepl_translator` → `DeepL API`).

### Probe-overrides-health

Rows with probe results in `apiProbeStatuses` prefer probe output over health payload. Probe mapping: `ok -> ok`, non-`ok -> degraded`.

## 3) NLP model selection

Removed from the Developer UI. The previous DaCy model picker is retired with the DaCy/spaCy/Lemmy stack.

## 3.5) Tab visibility

The Developer section uses Shadcn/Radix tabs with standard `Tabs` / `TabsList` / `TabsTrigger` / `TabsContent` composition. Only the active panel is mounted and rendered:
- `Status`: backend connection, API status list
- `API Keys`: runtime provider credentials and apply action
- `Probes`: translation, speech, and Gemini test actions/results
- `Database`: destructive reset action

Database reset controls are scoped to the `Database` tab only; they are not rendered globally beneath the tab set.

## 4) Provider probe workflows

### Translation provider switch

`translationProvider` controls `deepl` vs `azure` rendering:
- `deepl`: DeepL API key + optional endpoint
- `azure`: Azure Translator key + region + optional endpoint
- Button labels: idle `Test DeepL`/`Test Azure Translator`, loading `Testing DeepL...`/`Testing Azure Translator...`

### Translation probe

Trigger: test button → `runTranslationProbe()`. Request: `POST /api/developer/translation-probe` body `{}`. Success → store in `translationProbeResult`, write to `apiProbeStatuses` under provider key (`deepl_translator`/`azure_translator`), toast success if `status === "ok"` else error toast. Failure → synthetic error payload (`status: error`, `probe_input: bogen`, exception message), store in result + `apiProbeStatuses`, error toast. Rendering: `DeveloperProbeResult` shows status, probe input, optional result text, message.

### Loading/disabled states

Test button disabled while `isTestingTranslation`. Other probes independently operable during in-flight.

## 5) Speech and Gemini probes

### Speech probe

Button → `runSpeechProbe()`. `POST /api/developer/tts-probe` `{}`. Same pattern as translation: persisted in `speechProbeResult`, `apiProbeStatuses.azure_speech` updated, toast on ok/error, synthetic payload on exception. Disabled during `isTestingSpeech`, label → `Testing Azure Speech...`.

### Gemini probe

Button → `runGeminiProbe()`. `POST /api/developer/gemini-probe` `{}`. Same pattern: `geminiProbeResult`, `apiProbeStatuses.gemini`, toast, synthetic payload. Disabled during `isTestingGemini`, label → `Testing Gemini...`.

## 6) Runtime API key apply

Trigger: `Apply runtime API keys` → `saveDeveloperApiKeys()`. Request: `POST /api/developer/api-keys` with provider + all key/endpoint fields. Backend runtime config updated (runtime only, not persisted to files). Frontend refreshes health via `GET /api/health` → updates `healthPayload` + connection status. Startup settings (e.g. model env vars) still require restart.

## 7) Database reset

Trigger: `Delete complete DB` → `resetDatabase()`. Guardrail: confirmation dialog must return true. Request: `DELETE /api/wordbank/database`. In-flight: button disabled (`isResettingDatabase === true`), label `Deleting...`. Success → toast with backend message, invoke `onDatabaseReset()`. Failure → error toast with extracted message/fallback. Post-reset transitions delegated to `onDatabaseReset()` in composition layer.

## 8) Test map

Primary: `frontend/src/test/app/app-system-state.test.tsx`
- Connection status: offline on health failure, degraded on degraded report
- Developer basics: NLP picker presence/label, API status list + humanized labels
- Developer tabs: inactive tab content is hidden/unmounted; database reset only appears on `Database`
- Probes: Gemini (button, inline result, toast, API row updates), DeepL + Speech (independent results, toasts, status updates)
- DB reset: confirmation + DELETE method, success toast

Supporting: `frontend/src/app/sections/section-props-adapters.test.ts` — verifies handler adapters invoke controller functions for save/probe/reset.
