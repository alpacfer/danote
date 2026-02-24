# Language note app product definition

## overview

This app is a **language-learning note-taking web app** designed for live lesson use.

Its main purpose is to let a user **write normal lesson notes in a large text field** while the app quietly analyzes the text and helps turn it into a structured learning asset:

* a **wordbank** (known words, new words, inflected variants)
* a future **phrase/expression bank**
* a clean review flow after the lesson

The app is not meant to interrupt the writing process. It is a **note-taking tool first**, and an analysis tool second.

## core problem it solves

During language lessons, learners often write many useful words and expressions, but later they must manually:

* find what is new
* check dictionary forms
* separate mistakes from real vocabulary
* extract useful phrases
* organize everything into something reviewable

This app reduces that manual work by analyzing what the user writes and classifying tokens in near real time.

## primary user experience goal

The main UX goal is:

> The app should feel fast, calm, and helpful while the user is typing during a lesson.

This means:

* typing must feel instant
* no UI freezing or blocking
* minimal visual noise while writing
* subtle feedback during typing
* stronger review actions after writing

## product vision

The long-term vision is a language-learning note editor that can:

* detect words and their base forms automatically
* identify inflected variants (e.g., Danish `bog` / `bogen`)
* avoid polluting the wordbank with obvious typos
* detect useful expressions and multi-word chunks
* support review and learning workflows after the lesson
* remain local-first and privacy-friendly

The first implementation focuses on a narrow, solid foundation: **word detection and classification only**.

## initial app purpose (first implementation)

The initial app version is intentionally basic.

When the user types words in the main text field, the app classifies finalized words as:

* **known**: the exact word form exists in the local database
* **variation**: the exact form is not in the database, but the base form (lemma) exists
* **new**: neither exact form nor known base form is found

Example:

* database has `bog`
* user writes `bog` → **known**
* user writes `bogen` → **variation** (same base word)
* user writes an unseen word → **new**

## language focus

The app is designed **Danish-first**.

This matters because Danish has inflections and forms that make simple string matching insufficient. The app should recognize that different surface forms may belong to the same base word.

This Danish-first design is a strength, not a limitation. It allows better quality in the real use case.

## key design principle

## hybrid intelligence model

The app should not rely on an LLM for everything.

Instead, it uses a **hybrid design**:

* **local deterministic NLP** for fast, repeatable, low-cost analysis
* **LLM only later for high-value interpretation tasks** (expressions, ambiguity, semantics)

This keeps the app:

* fast
* token-efficient
* robust
* privacy-friendly

### what local NLP is responsible for

* tokenization
* normalization
* lemmatization
* part-of-speech and morphology (when needed)
* exact and lemma-based database lookup
* most real-time feedback

### what an LLM is reserved for (future, optional)

* phrase/expression validation
* ambiguity resolution
* semantic grouping
* optional explanations

The LLM is **not** part of the core typing loop.

## technology decisions

## frontend and app shape

The app should be a **web app UI in the browser**.

However, because the chosen Danish NLP tooling is Python-based, the recommended architecture is:

* **browser frontend**
* **local Python backend service** running on the user machine
* communication over `localhost`

This preserves the web app experience while allowing strong local Danish NLP.

## why not pure browser-only NLP (for this approach)

The preferred Danish NLP tools are Python-based and not ideal for a pure browser-only runtime.

A browser-only approach is possible with different strategies, but it would likely reduce accuracy and complicate performance for the current goals.

For a fast, accurate Danish-first product, the browser + local Python service approach is the right fit.

## local NLP stack (recommended)

### DaCy

DaCy is the recommended main Danish NLP pipeline for local processing.

Why:

* Danish-specific focus
* strong fit for Danish preprocessing and linguistic analysis
* useful foundation for future features (grammar-aware suggestions, phrase candidate detection)

### Lemmy

Lemmy is recommended as the Danish lemma normalizer / fallback lemmatizer.

Why:

* directly solves the key lexeme problem (`bogen` → `bog`)
* specialized for Danish lemmatization
* strong fit for lexeme grouping in the wordbank

### SQLite (local storage)

SQLite is the recommended local database.

Why:

* mature and reliable
* local-first by default
* simple deployment
* fast reads/writes
* good fit for a single-user app at this stage

FTS5 can be used later for search/fuzzy retrieval, but the first version can start with straightforward tables and indexed lookups.

## UI system decision

## shadcn/ui as the design system

The UI should use **shadcn/ui** as the standard design system, with as little custom component work as possible.

This supports the project goals:

* consistent UI patterns
* quick development
* maintainable styling
* standard composition over bespoke widgets

### shadcn-first philosophy for this app

* use standard shadcn components whenever possible
* compose layouts instead of building custom primitives
* postpone custom editors/inline highlighting until the core logic is stable

### standard components selected for the early UI

* **Textarea** (main note input)
* **Field / labels / descriptions** (input framing)
* **Card** (panel layout)
* **Badge** (status labels)
* **Tabs** (notes view vs detected words view)
* **Scroll Area** (result list panel)
* **Table** (detected words list)
* **Separator** (layout grouping)
* **Tooltip** (status meaning)
* **Skeleton** (loading states)
* **Sonner** (feedback toasts)

### UI simplification decision (important)

The first version should **not** use inline token highlighting inside the text editor.

Instead, it should use:

* a plain `Textarea` for writing
* a separate detected words panel showing statuses

This keeps the first version stable and easier to build, while preserving a good note-taking experience.

## app behavior and flow

## two-lane processing model

To feel fast and remain accurate, the app uses two local processing lanes:

### lane 1: fast feedback lane

Purpose: immediate UI feedback.

Characteristics:

* runs on a short debounce / pause
* processes only the changed text span or sentence
* tokenizes text
* checks finalized words against local data
* returns provisional statuses quickly

### lane 2: deeper local NLP lane

Purpose: refine the result using Danish NLP.

Characteristics:

* runs after a slightly longer pause
* uses DaCy + Lemmy
* improves lemma-based classification
* supports future phrase detection and ambiguity handling

This structure preserves smooth typing while allowing better analysis a moment later.

## typing flow philosophy

The app should not make hard decisions on every character.

It should distinguish between:

* **in-progress token** (currently being typed)
* **finalized token** (word completed by space/punctuation/pause)

This avoids flicker and false classifications while the user is still typing.

## example typing flow

Sentence: `Jeg kan godt lide bogen`

### what happens conceptually while typing

1. The editor updates instantly (no blocking).
2. The current sentence/span is marked as changed.
3. The app waits briefly (debounce).
4. Finalized words are analyzed and classified.
5. The currently typed token is treated as in-progress until finalized.
6. A deeper local NLP pass refines classification using Danish lemmatization.

### expected classification outcome

If the database contains lexeme `bog`:

* `Jeg` → known or hidden (depending on future filtering settings)
* `kan` → known
* `godt` → known
* `lide` → known
* `bogen` → **variation** (base form `bog` exists)

If `bog` is not in the database:

* `bogen` → **new** (with suggested base form `bog` for future add flow)

## classification logic (core v0 behavior)

For each finalized token, the app applies a simple lookup flow:

1. **exact form lookup**

   * if exact surface form exists → `known`
2. **lemma lookup**

   * if exact form does not exist, but lemma exists → `variation`
3. **otherwise**

   * classify as `new`

This is the fundamental behavior of the first implementation.

## lexeme-centered data model (conceptual)

A key design decision is to store vocabulary around **lexemes (base words)**, not just raw strings.

### why this matters

Without a lexeme layer, the database will treat inflected forms as separate words and create duplicates.

With a lexeme-centered model, the app can:

* preserve what the user typed
* group related forms correctly
* keep the wordbank cleaner
* support better review and future features

### conceptual entities

Even in a basic version, the app is designed around these concepts:

* **lexeme** (canonical/base form, e.g., `bog`)
* **surface form** (what the user typed, e.g., `bogen`)
* **occurrence** (where it appeared in notes)
* **status** (known / variation / new)

Future additions can include expressions, suggestions, and user actions.

## typo handling philosophy (future-aware, important)

The first implementation does not include typo detection, but the app design must anticipate it.

### key rule

The app should avoid treating every unknown token as a new word.

In later versions, unknown tokens may be classified as:

* typo-likely
* ambiguous
* new candidate

This matters for database quality and trust.

### why this is important even now

The status system and flow should not assume all unknowns are valid words. This design choice keeps the app extensible and prevents bad habits in the architecture.

## user experience principles

## 1) protect the writing experience

The user must be able to take notes naturally during a lesson.

The app should not:

* freeze typing
* jump the cursor
* flood the UI with popups
* aggressively interrupt the user

The app should:

* provide subtle feedback
* keep the main editor calm
* push details into a side panel or secondary view

## 2) avoid false confidence

A language tool that is confidently wrong loses trust quickly.

The app should prefer clear, conservative labels and avoid pretending certainty where none exists.

Even in the first version, this principle guides how statuses are interpreted and displayed.

## 3) separate writing mode from review mode (product direction)

Although the first implementation is basic, the long-term UX should separate:

* **lesson mode** (live note-taking, minimal interruption)
* **review mode** (accept/ignore suggestions, organize vocabulary)

This is one of the strongest UX concepts in the app.

## 4) helpful, not judgmental tone

The app should support learning rather than act like a harsh correctness checker.

Even status names and future labels should feel practical and neutral.

## status model direction

For the first implementation, the visible statuses are:

* **known**
* **variation**
* **new**

Internally, the flow already implies a concept of **in-progress** for typing behavior, even if not fully exposed to the user.

Future versions are expected to expand the state model with typo and ambiguity states.

## app interface concept (v0-oriented, no code)

## main screen structure

The app UI is designed around a standard, simple layout:

* **header**

  * app title
  * backend connection status
* **main content area**

  * note input panel (large text area)
  * status legend (what known / variation / new means)
  * detected words panel (list/table view of analyzed tokens)

## why separate results from the editor

This is a deliberate design decision:

* easier to build correctly
* avoids editor complexity early
* keeps note-taking smooth
* still gives immediate value

Inline highlighting can be added later once the classification pipeline is stable.

## local-first and privacy position

The app is designed to be local-first in its core form.

Benefits:

* lesson notes stay on the user’s machine
* fast local lookups and analysis
* reduced dependence on internet connectivity
* simpler trust story for learners

If optional cloud or LLM features are added later, they should be explicit and not part of the default writing flow.

## feasibility and realism

## is the app realistic to build?

Yes. The app is realistic and technically feasible.

The first version is especially realistic because it focuses on a narrow but valuable feature:

* type notes
* detect known vs variation vs new
* store and use a local wordbank

## what is realistically achievable first

A version that:

* feels fast while typing
* performs local Danish lemma-based classification
* distinguishes exact matches from inflected variants
* stores data locally
* provides a clean, minimal UI

## what is not required for the first version

The app does not need to solve:

* perfect grammar correction
* perfect typo detection
* phrase semantics
* full LLM-powered language understanding

These are later layers, not prerequisites.

## technology maturity considerations

The chosen stack is mature enough for the app’s current goals:

* **SQLite** is a stable local storage choice
* **Python NLP ecosystem (spaCy-based)** is mature
* **DaCy + Lemmy** are appropriate Danish-focused tools, with the practical caveat that they are more specialized and should be wrapped behind a stable app interface
* **shadcn/ui** is a strong standard UI system for composing a clean web interface quickly

This supports a realistic and maintainable first implementation.

## product boundaries (current definition)

## in scope (current product definition)

* language lesson note-taking in a large text field
* local analysis of typed words
* local database of known words / lexemes
* classification into known / variation / new
* Danish-first inflection-aware behavior
* standard, simple web UI using shadcn components

## out of scope (for the first product slice)

* typo detection logic
* phrase/expression extraction
* LLM calls during typing
* cloud sync
* advanced grammar explanations
* inline rich editor highlighting

These are valid future directions, but they are not part of the current app definition.

## what makes this app valuable

The app is valuable because it sits in a practical space between:

* a plain notes app (no language support)
* a flashcard tool (too structured during live lessons)
* a grammar corrector (too intrusive)

It supports a real workflow:

1. take notes naturally
2. get automatic language-aware classification
3. build a clean learning resource from real lesson content

That makes it useful, realistic, and differentiated.

## summary

This app is a **Danish-first language lesson note-taking web app** with a **local NLP backend** and **local wordbank**.

Its purpose is to help learners write notes normally while the app quietly identifies:

* what they already know
* what is a variation of something known
* what is likely new vocabulary

The product is designed around:

* **fast, calm typing UX**
* **lexeme-aware language handling**
* **local-first architecture**
* **standard shadcn UI composition**
* **a hybrid path that can later add LLM enrichment without putting LLMs in the typing loop**

This defines the app and its purpose clearly, while keeping the first implementation achievable.
