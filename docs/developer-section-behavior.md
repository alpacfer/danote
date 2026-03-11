# Developer section behavior

This document explains the runtime behavior of the Developer section in the frontend app, including probe flows, API-status rendering, and reset semantics.

## 1) Entry points

Primary UI components:

- `frontend/src/app/sections/developer-section.tsx`
- `frontend/src/app/sections/developer-probe-result.tsx`

Controller/composition handlers:

- `frontend/src/app/hooks/app/use-app-controller.ts`
  - Wires `developerSettings` state/actions into `buildDeveloperSectionProps(...)`.
  - Provides the `apiProbeStatuses` state used for merged API-status rendering.
- `frontend/src/app/sections/developer-section-props.ts`
  - Adapts app-controller state/actions into `DeveloperSection` props.
  - Converts async handlers (`saveDeveloperApiKeys`, `run*Probe`, `resetDatabase`) into fire-and-forget UI callbacks.
- `frontend/src/app/hooks/app/use-developer-settings.ts`
  - Owns mutable developer form state and all side-effectful workflows:
    - runtime API key apply
    - translation probe
    - speech probe
    - Gemini probe
    - database reset

## 2) Connection/API status display behavior

### Backend connection badge

- `badgeVariant` is derived from connection status in `buildDeveloperSectionProps(...)`:
  - `connected -> secondary`
  - `degraded -> outline`
  - `offline -> destructive`
- The visible text is the raw connection status (`connected`, `degraded`, `offline`).

### API status list rendering

- API entries are built by `useApiStatusItems(...)`.
- Ordering behavior:
  1. Preferred order from health payload: `backend`, `deepl_translator`, `azure_translator`, `azure_speech`, `gemini`.
  2. If an API is missing from health payload but has probe status in `apiProbeStatuses`, it is still shown.
  3. Any additional API names are appended alphabetically.
- Fallback: when no APIs are available in health payload and no probe-derived entries exist, a synthetic `backend` row is shown from app connection state.

### Badge variant classes per API row

- API status badges always use `variant="outline"`, and color classes come from `apiStatusBadgeClass(...)`:
  - `ok ->` green class set
  - `degraded` or `missing_key ->` amber class set
  - `inactive` or `disabled ->` neutral/zinc class set
  - `unknown ->` red class set
- Status label text is humanized by `humanizeApiStatus(...)` (`missing_key` displays as `missing key`).
- Service names are humanized by `humanizeApiName(...)` (for example `deepl_translator -> DeepL API`).

### Probe-overrides-health behavior

- For rows with probe results in `apiProbeStatuses`, row status/message prefer probe output over health payload values.
- Probe status mapping is simplified for row status:
  - probe `ok -> ok`
  - probe non-`ok -> degraded`

## 3) NLP model selection behavior

- The NLP model select control is rendered from `NLP_MODEL_OPTIONS` via `buildDeveloperSectionProps(...)`.
- Selecting a model updates only frontend local state (`selectedNlpModel` in `useDeveloperSettings`).
- There is no API write for this selector today; it is intended as a local benchmark preference indicator.
- The helper text explicitly states backend runtime default remains `da_dacy_small_trf-0.2.0` unless `DANOTE_NLP_MODEL` is set before backend startup.

## 4) Provider probe workflows

### Translation provider switch behavior (DeepL vs Azure)

- Provider choice is controlled by `translationProvider` (`deepl` or `azure`).
- Field rendering is conditional:
  - `deepl`: DeepL API key + optional endpoint
  - `azure`: Azure Translator API key + region + optional endpoint
- Button label updates by provider:
  - idle: `Test DeepL` or `Test Azure Translator`
  - loading: `Testing DeepL...` or `Testing Azure Translator...`

### Translation probe request/response behavior

- Trigger: clicking translation test button calls `runTranslationProbe()`.
- Request: `POST /api/developer/translation-probe` with empty body `{}`.
- Success path:
  - stores response in `translationProbeResult`
  - writes probe outcome to `apiProbeStatuses` under normalized provider key (`deepl_translator` or `azure_translator`)
  - emits success toast when `payload.status === "ok"`, else error toast
- Failure path (network/exception):
  - builds synthetic error payload (`status: error`, `probe_input: bogen`, message from exception)
  - stores synthetic payload in `translationProbeResult`
  - stores synthetic payload into provider-specific `apiProbeStatuses` entry
  - emits error toast
- Rendering: `DeveloperProbeResult` prints status, probe input, optional result text, and message.

### Loading/disabled states

- Translation test button disabled only while translation probe is running (`isTestingTranslation`).
- Other probe buttons remain independently operable while one probe is in-flight.

## 5) Speech and Gemini probe behavior

### Speech probe

- Trigger: clicking `Test Azure Speech` calls `runSpeechProbe()`.
- Request: `POST /api/developer/tts-probe` with `{}`.
- Success/failure behavior mirrors translation probe pattern:
  - persisted in `speechProbeResult`
  - `apiProbeStatuses.azure_speech` updated
  - success toast for `status === ok`, error toast otherwise
  - synthetic error payload on thrown errors
- Button is disabled during in-flight run via `isTestingSpeech` and label becomes `Testing Azure Speech...`.

### Gemini probe

- Trigger: clicking `Test Gemini` calls `runGeminiProbe()`.
- Request: `POST /api/developer/gemini-probe` with `{}`.
- Success/failure behavior:
  - persisted in `geminiProbeResult`
  - `apiProbeStatuses.gemini` updated
  - success toast for `status === ok`, error toast otherwise
  - synthetic error payload on thrown errors
- Button is disabled during in-flight run via `isTestingGemini` and label becomes `Testing Gemini...`.

## 6) Runtime API key apply behavior

- Trigger: `Apply runtime API keys` calls `saveDeveloperApiKeys()`.
- Request: `POST /api/developer/api-keys` with current provider + all runtime key/endpoint fields.
- Immediate update behavior:
  - backend runtime configuration is updated for the current process (toast message communicates runtime update)
  - frontend refreshes health via `GET /api/health`; if available, it updates both:
    - `healthPayload`
    - top-level connection status (`connected`/`degraded`/`offline`)
- Persistence behavior:
  - values are runtime-only for the process, not persisted to source files.
- Restart-required behavior:
  - backend startup settings (for example model environment variables loaded at startup) still require restart as noted by UI helper text for NLP model defaulting.

## 7) Database reset behavior

- Trigger: `Delete complete DB` button calls `resetDatabase()`.
- Guardrail: confirmation dialog must return true; otherwise no request is sent.
- Request: `DELETE /api/wordbank/database`.
- In-flight behavior:
  - button disabled while `isResettingDatabase === true`
  - label changes from `Delete complete DB` to `Deleting...`
- Success behavior:
  - success toast uses backend message
  - invokes `onDatabaseReset()` callback from composition layer
- Failure behavior:
  - error toast with extracted message or fallback
- Post-reset state transitions are delegated to `onDatabaseReset()` in higher-level composition/controller logic.

## 8) Test map (centered on `frontend/src/test/app/app-system-state.test.tsx`)

`app-system-state.test.tsx` is the primary integration map for Developer section system-state behavior:

- Connection status rendering:
  - offline when health fetch fails
  - degraded when health reports degraded
- Developer section basics:
  - NLP model picker presence and default label
  - API status list presence and humanized service labels
- Probe workflows:
  - Gemini probe: button trigger, inline result rendering, toast behavior, API row updates
  - DeepL + Speech probes: independent probe results, success/error toasts, API status/message updates
- Database reset flow:
  - confirmation + delete request method verification (`DELETE`)
  - success toast

Supporting tests around the same behavior contract:

- `frontend/src/app/sections/section-props-adapters.test.ts`
  - verifies handler adapters invoke controller functions for save/probe/reset.
