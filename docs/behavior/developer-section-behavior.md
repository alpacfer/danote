# Developer section behavior

## 1) Entry points

UI components:
- `frontend/src/app/sections/developer/developer-section.tsx`
- `frontend/src/app/sections/developer/probe-result.tsx`

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
- `Database`: pinned audio generation and destructive reset actions

Database reset and pinned audio controls are scoped to the `Database` tab only; they are not rendered globally beneath the tab set.

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

Trigger: `Delete complete DB` → `resetDatabase()`. Guardrail: confirmation dialog must return true. Request: `DELETE /api/wordbank/database`. In-flight: button disabled (`isResettingDatabase === true`), label `Deleting...`. Success → toast with backend message, invoke `onDatabaseReset()`. The backend also prunes custom categories left unassigned by the reset and restores the standard starter category set. Failure → error toast with extracted message/fallback. Post-reset transitions delegated to `onDatabaseReset()` in composition layer.

## 8) Pinned audio generation

The Database tab has one `Pinned word audio` control group. `Generate missing`
calls both `POST /api/wordbank/numbers/pronunciation/seed` and
`POST /api/wordbank/presaved-words/pronunciation/seed`. `Regenerate all` calls
the same endpoints with `force=true`. The UI treats the two backend stores as
one developer setting because pinned cards use a shared audio playback hook.

## 9) Danote Terminal Controller

`scripts/dev-app.py` is the **Danote Terminal Controller** (**DTC**), the
JSON-only terminal controller for live app debugging. It auto-detects the local
backend and calls the same API routes as the frontend for health, developer
probes, search, wordbank, verification, and sentencebank workflows. References
to "DTC" mean this script.

Search-specific DTC commands:
- `scripts/dev-app.py search profile <query>` mirrors the single-word sidebar
  search waterfall and reports flow decisions, per-phase timings, result counts,
  translation keys, and whether direct translated COR was skipped.
- `scripts/dev-app.py search trace <english-query>` traces EN → DA → filtered
  COR decisions for an English query.
- `scripts/dev-app.py search all <query>` reads saved, direct COR, EN, and
  resolver outputs sequentially for broad debugging; use `search profile` for
  latency work.

Wordbank-specific DTC commands:
- `scripts/dev-app.py wordbank category-status <lemma> --polls 5` repeatedly
  reads lemma details and summarizes categories plus verification status by
  lemma/meaning/surface scope. Add `--expect-category <label>` one or more
  times to fail the command when the final snapshot still lacks a generated
  category.

After implementing user-facing or backend behavior that is reachable through
the app API, run at least one relevant DTC command as an extra terminal
acceptance check. This check supplements pytest, Vitest, lint, and docs smoke
verification; it does not replace them. Destructive controller commands
intentionally do not prompt.

## 10) Test map

Primary: `frontend/src/test/app/app-system-state.test.tsx`
- Connection status: offline on health failure, degraded on degraded report
- Developer basics: NLP picker presence/label, API status list + humanized labels
- Developer tabs: inactive tab content is hidden/unmounted; database reset and pinned audio controls only appear on `Database`
- Probes: Gemini (button, inline result, toast, API row updates), DeepL + Speech (independent results, toasts, status updates)
- DB reset: confirmation + DELETE method, success toast

Supporting: `frontend/src/app/sections/section-props-adapters.test.ts` — verifies handler adapters invoke controller functions for save/probe/reset.
