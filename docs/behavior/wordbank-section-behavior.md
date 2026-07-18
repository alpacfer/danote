# Wordbank section behavior deep dive

Exact behavior of the **Wordbank section**: list mode, lemma word page, meaning sections, pronunciation flows, Gemini verification.

## Entry points and ownership

- Section switch (list vs word page): `frontend/src/app/sections/wordbank-section.tsx`
- Data loading/detail fetches: `frontend/src/app/hooks/use-lexicon-data.ts`
- Workflows (add/pronunciation/verification): `frontend/src/app/hooks/use-wordbank-workflows.ts`
- Word page composition:
  - `frontend/src/app/sections/wordbank/wordbank-word-page.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-meaning-sections.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx`
- List view: `frontend/src/app/sections/wordbank/wordbank-list-view.tsx`

## High-level mode behavior

Two UI modes:
1. **List mode** — no lemma selected
2. **Word page mode** — lemma selected

Switch: `selectedLemma` absent => `WordbankListView`, present => `WordbankWordPage`.

## Data loading lifecycle

## Lemma list loading (`/api/wordbank/lemmas`)

- Deferred; loads when: active section is `wordbank` OR lemma selected OR `hasLoadedWordbank`
- Skips re-fetch if `wordbankRefreshTick` already loaded
- Success → update `lemmas`, set lazy-load marker, record tick
- Failure → set `wordbankError`, clear list
- List items include aggregate `pos_tags` and `categories` arrays used only for
  local filtering. A multi-meaning lemma remains represented once in the list.
- `created_at` is the lexeme creation time. `last_enriched_at` is the newest
  lexeme update, meaning update, surface-form creation, or category-assignment
  update. Both are informational owner-scoped timestamps; no migration or
  learning status is created.

## Lemma details loading (`/api/wordbank/lemmas/{lemma}`)

- Fetched when: active section is `wordbank` AND `selectedLemma` present
- Lemma change → drop previous payload immediately; wait for new response/skeleton
- Any visible target still `queued` → poll every 1.5s until all reach final state
- `related_words.status === "queued"` → poll every 1.5s until `ready`/`empty`/`error` (silent, no placeholder)
- Leaving wordbank/clearing selection → reset details state
- Loading skeleton delayed 180ms (avoids flicker) and uses the same scroll/card/grid shells, line heights, and badge heights as the final single-word result layout to avoid visible jumps when details arrive.
- Poll refresh failures → keep last rendered details, update error banner only

## List mode behavior (WordbankListView)

Priority:
1. `wordbankError` → error alert
2. Loading + `lemmas.length === 0` → grouped skeleton
3. No active filter matches → reference decks plus an empty state
4. Otherwise → reference decks plus grouped specimen tiles with letter headings

Collection composition:
- The collection alone uses the notebook's 8px dot-grid surface; word details,
  pinned reference interiors, and other sections retain normal 32px ruling.
- Reference pages render as a five-compartment catalogue drawer: one row on
  desktop and two columns on mobile, with descriptions hidden at the narrowest
  breakpoint.
- The reference drawer, filter row, and catalogue share the notebook content
  edge and use a 32px vertical interval between blocks. Plain group letters
  align to that same left edge.
- Saved lemmas use Danish collation and group in `A–Z, Æ, Ø, Å` order. A sticky,
  right-edge alphabet index exposes only letters present in the current filtered
  result, scrolls them into view, and tracks the visible group with
  `IntersectionObserver`.
- Each group pairs a plain sticky Fraunces margin letter with a responsive grid
  of compact word slips. Counts are omitted and word metadata remains in the
  specimen preview rather than expanding the collection tiles.

Filters:
- Filter bar sits below the reference drawer and auto-applies local filters.
- Word type filter is a multi-select popover; a lemma matches if any selected
  POS appears anywhere under that lemma.
- Category filter is a searchable multi-select popover; a lemma matches only
  when all selected categories appear somewhere under that lemma.
- Word type and category filters combine with AND.
- Clear filters resets both dimensions. Reference decks stay visible
  regardless of saved-lemma filters.

Per-specimen tile:
- Label: `display_lemma` fallback `lemma`
- Hover or keyboard focus opens a non-interactive specimen preview when saved
  translations or readable POS labels exist. It shows the display lemma,
  aggregate POS labels, and every saved primary/additional translation grouped
  by meaning. Case-insensitive duplicate translations are omitted.
- The preview uses real saved linguistic data only: no specimen identifiers,
  inferred definitions, glosses, categories, dates, variation counts, or
  pronunciation status.
- The preview opens after 300ms, remains open while hovered, closes after
  200ms, and dismisses on Escape. The same plain-text metadata is exposed as
  the word trigger's accessible description.
- One category-derived material wash identifies the tile without a colored
  edge or leading icon; POS remains available in the preview. Multi-word
  expressions use a restrained joined-label silhouette.
- Unread verification markers:
  - queued/in-progress → no marker
  - unread `1` → dot indicator
  - unread `>1` → numeric badge pill
- Click → `onSelectLemma(lemma)` → opens word page
- Touch tap follows the same one-step word-page navigation and does not insert
  a preview-first interaction.
- Right-click → destructive `Delete whole lemma` action. The confirmation
  dialog explains that all meanings under the lemma are removed and linked
  sentence tokens become unsaved instead of disappearing.

Five built-in reference decks are pinned in the compact drawer at the top of
the Wordbank list and shown even when there are no saved lemmas: **Pronouns**, **HV Questions**,
**Prepositions**, **Conjunctions**, and **Numbers & Time**. The responsive
deck shelf uses a distinct icon and short collection description for each page
plus its own restrained material tint while dimensions and behavior remain
identical. The whole visible card remains one accessible button. Each page is
identified by its canonical sentinel lemma. Legacy
sentinels such as `__pronouns_personal`, `__question_words`, and `__numbers`
still route through
`frontend/src/app/sections/wordbank/_shared/pinned-pages-registry.ts`; they
open the owning grouped page and select the matching default tab.

Grouped pinned pages render through `PinnedPageLayout` and shadcn/Radix
`Tabs` (except HV Questions, Prepositions, and Conjunctions, which each present
their words together in a single grid). Pronouns includes Personal, Possessive,
Demonstrative, Relative, and Indefinite tabs. Numbers & Time includes Cardinal
Numbers, Ordinal Numbers, Days, and Months. The pages intentionally
avoid instructional descriptions, note sections, generated examples, and
textbook-style rules; they are word collections only.

Every pinned tab uses the same simplified `PinnedWordCard` grid. Cards show the
Danish word, pronunciation control, English translation, and only a short
disambiguation label when needed. Cards also show compact POS/morphology badges
when useful, reusing the normal word-page/search badge pipeline
(`n-word`/`t-word`, person/number, interrogative, possessive, etc.). Cards do
not show add buttons, eye icons, generated-example context menus, or
saved-sentence example dialogs. Clicking the card opens
`/api/wordbank/lemmas/{lemma}` through a raw lemma navigation path. Sentence
token navigation also uses raw lemma/meaning navigation.

Pinned tab changes are navigation entries: changing tabs writes the tab-specific
sentinel, so browser Back/Forward restores the previous pinned tab state.
Backend static search/detail fallbacks let built-in/presaved words open normal
word pages even when they are not stored as regular lexemes. Search for a
presaved Danish or English word returns the static saved-default row before COR
or provider translation. Opening that saved row routes to the normal word page,
not to the pinned collection. Sentence-token clicks also open normal word pages
for saved built-in words rather than jumping to pinned collection tabs.
Static homographs such as `der`, `en`, `et`, and preposition/conjunction
overlaps render as sense-aware lemma pages. The backend owns each built-in
sense's POS, translation, meaning key, and `reference_links`; the frontend does
not infer pinned homes from lemma-only matching. Pinned collection links live
inside the matching word card rather than in the lemma header.
Number-only search still adds a page result for numeric queries (e.g. `21`)
labeled with the Danish written form and opens the Numbers & Time page on
Cardinal Numbers.

## Word page behavior (WordbankWordPage)

- `lemmaDetailsError` → error alert
- Loading + skeleton gate open + no details → full word-page skeleton
- Loading + skeleton gate not open → `null`
- Not loading + no details → `No details found for this lemma.`
- With details:
  - sectioned pages render `WordbankLemmaHeader` followed by `WordbankMeaningSections`
  - non-sectioned pages render the same standard word-card layout through a root `WordbankMeaningSections` card
  - after body: `WordbankRelatedWords` when `related_words.status === "ready"` and cards exist
  - presaved/static words that belong to pinned collections show backend-provided reference links inside the owning word card
  - Related section includes direct compound components + reverse compound-host links

Meaning auto-scroll:
- Selected meaning id → `requestAnimationFrame` + `scrollIntoView({ behavior: "smooth", block: "nearest" })`

## Header behavior (WordbankLemmaHeader)

## Title/pronunciation source selection

- Title: `lemmaDetails.lemma` via `WordbankPronunciationWord`
- Right-click header word → contextual audio menu
- Pronunciation playback precedence:
  1. exact normalized match among selected-meaning forms + top-level forms + all section forms, with pronunciation
  2. first available pronunciation form from combined list
  3. no icon/action when none exist
- Sectioned lemmas: backend may keep lemma form in top-level `surface_forms` while meaning sections show only non-lemma variations → preserves exact lemma playback without duplicating lemma row per section
- Non-sectioned lemmas: `map_lemma_details_response` keeps the lemma form in `surface_forms` whenever it carries pronunciation. This ensures the frontend's pronunciation-availability map sees the lemma's audio so the synthetic Infinitive / Singular-Indefinite row renders a play button (critical for MWE verbs like `passe på` where the lemma form IS the audio carrier). The variation card filter excludes lemma forms by name, so this never causes the lemma to show twice.

### Multi-word expression (MWE) word pages

MWE lemmas (e.g. `passe på`) save through the same wordbank pipeline as
single-word lemmas. The MWE branch in `sentencebank_token_resolution.py`:

- Creates a `lexeme_meanings` row via `ensure_mwe_meaning_section`
  (`backend/app/services/use_cases/sentencebank_mwe.py`) so the page renders
  sectioned and "Complete variations" is gated by the same verified-status
  logic used for any other word.
- Tags `dictionary_status="cor"` when `runtime.cor.lookup_mwe_lemma(lemma)`
  finds a match (links to the COR lemma index), otherwise `generated_non_cor`.
- Saves the encountered surface form (e.g. `pas på`) with morphology inferred
  from the head verb's COR entry (`pas` → `Mood=Imp|VerbForm=Fin`) via
  `infer_mwe_surface_morphology`, so the form slots into the Imperative row of
  the verb paradigm instead of "Other forms".
- Writes a synchronous "Composition" seed (`seed_mwe_component_related_words`
  on `RelatedWordsCollaborator`) with the constituent words. The existing
  Gemini related-words background job still runs for MWE lemmas — its prompt
  has an MWE branch (see `_prompt` in `services/related_words.py`) that asks
  for the constituent words in reading order (decomposition only — near-synonyms
  / related expressions are not a feature yet) — and replaces the seed when it
  completes. The frontend renders this data under the "Composition" heading and
  filters to `relation_type=compound_component`; `compound_host` reverse-links
  ("this lemma is part of these other saved compounds") are intentionally hidden
  until a real Related/Synonyms surface exists.

Variations (Present / Past / Past participle for an MWE verb) are not
auto-populated; the user fills them in via the same "Complete variations"
flow as for any other verb.

## Header metadata and translation

- Sectioned mode → translation suppressed
- Non-sectioned legacy header metadata is mirrored in the standard root word card
- `additional_translations` → inline comma-separated italic line when present
- Badges shown only when `showSupplementaryMetadata` true
- Badge source: POS/morphology from selected meaning (fallback lemma-level); `gram_raw` from lemma-level surface form matching selected lemma
- Non-sectioned semantic category badges:
  - from `lemmaDetails.categories`, own header row, dedicated outline styling
  - root-scope recategorization → lemma word's right-click menu (not whole header)

## Header actions

- **Verification trigger button**:
  - sole visible header action button
  - icon by aggregated state: idle→info, queued→spinner, verified→check, error/flagged→alert
  - trigger priority: `review` (any flagged/error) > `queued` (any queued) > `verified` (all verified) > neutral
  - review-needed → shows total suggested-action count inline
- **Verification popover**:
  - single surface for verification status/details; no standalone status line/badges
  - opening → marks visible targets as read in notification center
  - adaptive height: shrinks to fit short content, bounded viewport height + scroll for long
  - compact static header: title + one overall state badge + one summary sentence
  - targets grouped by priority: `Needs review` → `In progress` → `Checked` (word-page order within groups)
  - review rows: compact action-first — target label+scope, mismatch line, muted follow-up, one semantic action button per Gemini suggestion (`Fix translation`, `Move to different lemma`, `Fix variations`)
  - meaning-level/root reviews → may show `Fix translation`; surface-form reviews → never show translation-fix, only relocation actions
  - both surface-form and meaning reviews pass saved POS/morphology, COR `gram_raw`, derived paradigm-slot context to Gemini
  - error rows → `Retry verification` (requeues exact target, keeps polling)
  - queued rows → compact in-progress copy + requested time
  - verified rows → collapsed into one low-emphasis checked summary (count + latest time)
  - unchanged `verified` → no app notification row; silent success
  - surface-form review as translation-only Gemini noise → backend suppresses, stays in checked bucket
  - meaning review returning only conflicting lemma-move → backend drops move; if gloss hint available, backfills translation-fix action
  - meaning review with no saved translation or low-confidence verb self-translation + backend gloss hint → stays `Needs review` with `Fix translation` even if Gemini returns `OK`
  - COR/translated glosses → reference context only; popover never asks user to rewrite gloss
  - `Fix translation` → backend normalizes to translation-only wording (no verbatim Gemini gloss critique)
  - legacy completion-review meaning cards may show one `Fix variations` action; current Complete variations requests no longer create these reviews
  - no-record → neutral empty state ("verification details will appear here once Gemini runs")
  - action buttons + `Retry verification` → disabled while request in progress

## Word-card context menu

- Uses shadcn `ContextMenu` for audio actions + category-bearing scopes
- Pronunciation words are direct click targets; no click-to-listen tooltip is shown
- Sectioned pages:
  - header lemma word → `Regenerate audio`
  - each meaning card → context-menu trigger exposing `Rerun verification`, `Find alternative translations`, and destructive `Delete meaning`; noun/adj/verb cards also expose `Rethink categories`, `Complete variations`; other POS cards expose only `Find alternative translations` + `Rethink categories` plus deletion
  - each surface-form word in meaning card → `Regenerate audio`
- Non-sectioned pages:
  - lemma word → `Regenerate audio`, `Find alternative translations`, `Rethink categories`
  - each flat variation word tile → `Regenerate audio`
- `Find alternative translations`: reuses `ContextMenuItem` (no `DropdownMenu`/popover); calls backend Gemini translation route, refreshes lemma details on success
  - Gemini returns only very common obvious alternatives for exact saved sense (may return none)
  - if current saved translation not best → backend replaces primary
  - valid distinct alternates → persisted into `additional_translations`
- `Rethink categories`: immediate backend recategorization, refreshes lemma details; no confirmation flow; same Gemini flow as initial verification but user-triggered
- `Rerun verification`: requeues `general` Gemini review for meaning + saved non-lemma variations; existing word-page polling/popover surfaces changes
- `Delete meaning`: opens a confirmation dialog. Deleting a meaning preserves
  saved sentence text while converting linked tokens to unsaved. If the meaning
  was the last saved meaning for that lemma, the backend deletes the whole lemma
  and the frontend navigates back.
- `Complete variations`: meaning-only v1 for noun, adjective, verb sections
  - uses one Gemini variation-resolution call for COR, generated non-COR, and unknown meanings
  - Gemini receives the saved lemma, meaning/gloss/translation/POS, and existing saved forms; its returned forms are persisted directly after normalization/dedupe
  - gated by verification state: enabled only when meaning target + all saved variations are `verified`
  - gated labels: `Waiting for verification...` (any queued), `Retry verification first` (any error), `Resolve verification review first` (any flagged), `Complete variations unavailable` (other non-verified)
  - queues pronunciation only for newly added forms
  - no follow-up completion verification is queued; `queued_verification_targets` is empty for this path
  - insufficient COR identity → skipped with user-facing message, except generated non-COR meanings, which use Gemini slot completion

## Body mode A: sectioned meanings (WordbankMeaningSections)

- No meaning sections → `No saved meanings for this lemma.`
- Each section card:
  - layered dictionary-slip material with a neutral hairline; never a colored
    rail. The selected sense moves forward through tint, shadow, and a small
    positional transition.
  - left metadata: lemma label + inline translation + section POS/morphology badges
  - verb cards: lemma in infinitive form `at <lemma>`
  - section `gram_raw` → badge set from COR grammar (e.g. invariant `orange` keeps merged badges)
  - right semantic category badges from `meaning_sections[].categories`; right-aligned wide, wrap narrow
  - optional combined translation line: `translation (gloss translation)` format; search rows use the same display string before save so the saved word card matches what the user selected
  - optional `reference_links` render as compact buttons inside the same card
- Surface forms per meaning:
  - divided list, each row uses `WordbankPronunciationWord`
  - section lists render only non-lemma variations
  - top-level `surface_forms` may include lemma form separately as deduped header/audio source
  - pronunciation resolved by normalized form across section rows + hidden top-level lemma rows
  - noun/adj meanings → 2x2 paradigm table when >=1 slot derivable
  - verb meanings → fixed rows: `Infinitive`, `Present`, `Past`, `Imperative`, `Past participle` (no visible `Form` header)
  - paradigm markup remains a semantic table but is presented as a connected
    morphology journey with named slots and a stacked narrow-screen layout
  - initial saved form shown in table immediately
  - adj tables: number × definiteness; singular-indefinite has separate `n-word`/`t-word` lines; partial generated non-COR morphology is still slotted when gender/number is enough; equivalent forms in one slot are separated with `/`; same-form entries (e.g. `store`, invariant `orange`) may render into multiple cells
  - verb same-form entries may render into multiple rows
  - noun order: non-slot/irregular first, then singular-definite, plural-indefinite, plural-definite
  - saved POS/morphology badges normalize to reader-facing labels (e.g. adj agreement uses `n-word`/`t-word` not `Common`/`Neuter`)
  - saved form `gram_raw` → badges from `gram_raw` first (align with search); form-level badges filtered to avoid repeating section-level labels

## Body mode B: flat variations (WordbankVariationGrid)

- Built from top-level `surface_forms`, excluding normalized selected lemma
- noun/adj/verb flat pages → prefer shared paradigm table even with only lemma saved; empty cells blank
- Non-paradigm pages, no remaining variations → nothing rendered
- Each tile: pronunciation-enabled form title, right-click `Regenerate audio`, form badges

## Related section (WordbankRelatedWords)

- Renders only when `related_words.status === "ready"` AND `items.length > 0`
- Verb cards: Danish infinitive (`at lege`) + English infinitive (`to play`)
- `compound_component` → current lemma decomposes into that component
- `compound_host` → another saved compound contains current lemma (links back e.g. `legeplads` from `lege`+`plads`)
- Saved targets → eye button, opens saved lemma/meaning
- Unsaved unique → plus button, saves through add-word flow
- Different valid translation for saved target → backend persists into `additional_translations` immediately
  - optional `from <lemma>` line + merged lemma translation+gloss in the shared
    related-word material treatment

## Related words section (`WordbankRelatedWords`)

- Placement:
  - header→first card: spacing only, no horizontal divider
  - below meaning/variation body
  - title: muted uppercase micro-label
  - hidden when `related_words.status === "empty"` and no items
- Source contract:
  - Gemini decides compound status, returns component lemmas + translation + POS hint
  - COR supplies morphology/badges via `display_variant`/`candidate_variants`
  - saved/open from persisted wordbank (saved lemmas + variations both treated as known)
  - different Gemini translation for saved target → persists into `additional_translations`
- States: `queued`→no section, `ready`→one card per item, `error`→no section, `empty`→no section
- Card actions:
  - `Eye` → opens saved target lemma/meaning
  - unique unsaved → `Plus`, saves via add-word endpoint using `search_seed`
  - ambiguous unsaved → `Plus`, expands inline candidates first
- Ambiguous inline chooser: shadcn `Collapsible` per card (per-card, inline, no grouped semantics); `Dialog` rejected (interrupts flow); `Accordion` rejected (unnecessary grouped structure)
- Save result: keeps word page open; toast feedback; refreshes lemma details + wordbank list; card flips `Plus`→`Eye` on refresh

## Signature word-page composition

- A specimen hero combines lemma, English translation, audio, identity badges,
  verification, and existing reference bookmarks.
- Existing word- and meaning-level reference links render as bookmark controls.
- The newest linked sentence is promoted to a paper clipping; the complete
  collection remains below it. If no sentence exists, the existing Generate
  Example action is exposed without synthetic content.
- Compound components and related words share a compact connected composition
  shelf. This is intentionally not the later semantic-map feature.
- Audio rings, sense-depth transitions, example unfolding, variation arrival,
  and tile-to-page View Transitions are disabled or made immediate for reduced
  motion.

## Pronunciation workflow behavior

Shared by header + section rows + variation rows.

## Play flow (`GET /api/wordbank/pronunciation?form=<form>`)

- Form normalized; empty → no-op
- Per-form loading state during request/playback
- Blobs cached in-memory as object URLs by normalized form
- 404 → `No pronunciation is available yet for '<form>'.`
- Returned audio validated for playable content-type
- Active audio paused before new playback
- Unsupported audio (once): clear cache for form → forced background regeneration → retry once

## Regenerate flow (`POST /api/wordbank/lexemes/pronunciation`)

- Explicit regeneration: notification-enabled, targets exact right-clicked word (`stored_surface_form`)
- Automatic add/save/completion: no browser call; backend queues lemma-scoped pronunciation, page refreshes from persisted state; sentence-token saves track the saved lemma/surface so the opened word page polls for newly generated audio
- `status === "generated"`: invalidate cache, increment `wordbankRefreshTick`, success toast (notify mode)

## Verification workflow behavior

## Background verify

- Add flows: no browser-side Gemini calls
- After successful add → backend queues verification for each visible target on current word page
- Manual retries → `POST /api/wordbank/lexemes/queue-verification` (one exact target by `(stored_lemma, meaning_id, stored_surface_form, review_intent)`)
- `Complete variations` → one meaning-level request (not per-variation)
- Complete variations itself owns variation generation through Gemini; normal save verification cannot suggest paradigm completion
- Target discovery:
  - non-sectioned: one lemma/root target + one per non-lemma variation
  - sectioned: one per meaning section + one per saved variation in that meaning
  - no synthetic root target for sectioned pages unless root-level saved record exists
- Results persisted by `(lemma, meaning_id, stored_surface_form)`, returned through lemma-detail fetches
- Queue dedupe: stable per target, not per snapshot hash
- Newest-request-wins: stale in-flight run discarded at persist time; latest request stays pending
- Verification evaluates current persisted structure: lemma → meanings → surface forms
- Normal post-save verification: checks placement correctness only; doesn't fail for missing paradigm members, doesn't suggest variation completion
- Prompt payloads: target-scoped, token-lean (target + relevant forms + minimal sibling context + canonical lemma identity)
- Payloads include saved lemma + best COR-backed canonical lemma identity
- COR indicates inflected form (e.g. `mor` vs `moder`) → Gemini flags, suggests `move_to_lemma`
- Translation context from lemma/meaning only (surface forms have no independent translations)
- Meaning glosses: immutable COR disambiguators; Gemini uses for sense identification, never proposes gloss edits
- Meaning-section verification: reviewed section sent as current scope, not duplicated in sibling list
- Translated gloss hints sent for reviewed meaning, siblings, scoped surface forms (disambiguate homographs like `mor`)
- Canonical lemma metadata evaluated separately from saved surface-form metadata
- Post-verification: category classification runs as separate Gemini step after completed verification attempts when the category service is available
  - receives shared category list + scope's assigned categories + saved-word context, including word, translation/gloss, and POS metadata
  - prefers existing concise English categories; may apply or mint multiple 1-3 word Title Case semantic labels
  - auto-applied, no confirmation; visible through later lemma-detail fetches
- Backend-driven via shared wordbank background-job runner; bounded parallel worker pool
- Queued payloads carry target snapshot hash; stale job skipped (doesn't overwrite newer result)
- Success → persisted record with `requested_at`/`completed_at`; error → persisted record with timestamps + suggested actions
- Queued/in-progress → silent in notification center, no Wordbank unread badge increment
- Target reaches `flagged`/`error` → push target-specific in-session notification

## Category rethink

- `POST /api/wordbank/lexemes/rethink-categories`: reruns Gemini category classification for root/meaning scope
- Triggered manually from context menu; uses standalone category payload
- May reuse existing categories + mint multiple concise semantic categories
- Success → replaces full persisted category assignment for scope
- Does not overwrite/re-review verification records

## Action apply (`POST /api/wordbank/lexemes/apply-verification-changes`)

- Accepting popover action → apply endpoint with target + action payload
- Always includes scope: `stored_lemma`, `meaning_id`, `stored_surface_form`
- `fix_translation`: only for lemma/meaning-scoped (`stored_surface_form` is `null`)
- Eligible Gemini `fix_translation` suggestions may auto-apply immediately after verification persistence
- Persisted `fix_translation` applies are stored in a per-lemma verification change log
- Applied: success toast (text varies by action type); backend prunes action; last suggestion applied → target flips to `verified`; increment `wordbankRefreshTick`; navigate to returned target
- No visible variation change → backend returns `status=skipped`, review stays pending
- Failure → error toast

## Verification change history

- `GET /api/wordbank/lexemes/verification-changes?stored_lemma=...`: fetches newest-first per-lemma history for persisted Gemini `fix_translation` / `fix_variations` applies
- `POST /api/wordbank/lexemes/revert-verification-change`: restores the saved `before_json` snapshot for a change-log entry and marks it reverted
- Word page verification popover adds a `Changes` section below review/progress/check state
- Change rows show action label, concise before/after summary, timestamp, and `Revert` button when still active
- Revert success → success toast, wordbank refresh tick increment, history re-fetch; already reverted/missing entries show error toast and refresh history

## Add flows that affect Wordbank state

## Single-word translation normalization

- Word-level provider translations normalized after lookup
- Content words: remove frame scaffolding; noun phrases may stay multi-word
- Function words: keep short lexicalized context when removing would lose meaning
- Phrase translation not in this path

## Retired Playground token add

The previous token-popover add path from Playground is retired while Playground is inaccessible. Active add flows come from sidebar search and direct wordbank workflows.

## Add from sidebar search

- `POST /api/wordbank/lexemes`
- Success: toast; backend queues full-page verification; returns `queued_pronunciation_forms`; token feedback (`source: "search"`)
  - `saved_snapshot` → details hydrated immediately; `queued_verification_targets` seed off-page tracking; queued verification → header shows `Verifying...`
  - open-page targets queued → polls until final; pronunciation queued → same polling loop waits bounded window
  - analysis + wordbank refresh ticks increment; navigate to stored lemma/meaning
- `search_seed` persistence: canonical lemma metadata from COR (`cor_lemma_idx`); selected surface keeps search-result variant tags; `english_translation` from COR lemma only; gloss translation separate
  - empty translations allowed; low-confidence glossless verb self-translations dropped
  - queued Gemini verification now flags missing lemma/meaning translations for review, including glossless entries where save-time translation generation produced nothing
  - when Gemini word translation can resolve a missing lemma/meaning translation during verification, verification now emits `fix_translation` and the existing Gemini auto-apply flow applies it immediately
  - word page computes gloss translations for search-saved meaning sections; raw gloss not promoted to `english_translation`; UI omits untranslated gloss
  - only selected surface stored; no full paradigm hydration

## Linked sentence cards

- Word pages now include a `Sentences` section below related words when lemma details include `linked_sentences`.
- Each card shows:
  - source sentence
  - underlined matched Danish token(s) from `matched_token_indexes` when the backend supplies token alignment
  - sentence translation
- No per-token cards render on the word page. Detailed token analysis remains in the Sentencebank section.

## Complete variations follow-up

- `POST /api/wordbank/lexemes/complete-variations`
- Success: Gemini-resolved missing paradigm members inserted; same-spelling forms are kept when they represent distinct morphology (for example verb past matching the lemma); pronunciation queueing merged via one lemma-scoped background job (`stored_lemma`); `queued_pronunciation_forms` = forms still missing audio (may include lemma itself); word page polls bounded window until `has_pronunciation=true` or timeout

## Behavioral test coverage map

- `renderer-only`: `frontend/src/test/app/app-wordbank-details.test.tsx`, `frontend/src/test/app/app-wordbank-actions.test.tsx`
- `request-shape`: `frontend/src/test/app/app-shell-search-actions.test.tsx`
- `contract`: `backend/tests/use_cases/test_wordbank_translation_details.py`, `backend/tests/api/test_wordbank_add_and_list_endpoint.py`
- `round-trip`: `backend/tests/use_cases/test_wordbank_add_and_list.py`, `backend/tests/api/test_wordbank_add_and_list_endpoint.py`
- `queue/orchestration`: `backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py`
- shared contract fixtures: `frontend/src/test/app/wordbank-contract-fixtures.ts`
