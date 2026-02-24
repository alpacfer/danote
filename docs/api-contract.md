# API Contract

## GET `/api/health`

Health and readiness status for backend dependencies.

### Response JSON

```json
{
  "status": "ok",
  "service": "backend",
  "components": {
    "database": "ok",
    "nlp": "ok"
  }
}
```

When startup checks fail (for example DB path invalid or NLP initialization failure), `status` becomes `"degraded"` and component-level status/error fields are returned.

## POST `/api/analyze`

Analyze full note text and return token classifications for finalized tokens.

### Request JSON

```json
{
  "text": "Jeg kan godt lide bogen"
}
```

### Response JSON (v1 typo-aware schema)

```json
{
  "tokens": [
    {
      "surface_token": "bogen",
      "normalized_token": "bogen",
      "lemma_candidate": "bog",
      "classification": "variation",
      "match_source": "lemma",
      "matched_lemma": "bog",
      "matched_surface_form": null,
      "suggestions": [],
      "confidence": 0.0,
      "reason_tags": ["lemma_match"],
      "status": "variation",
      "surface": "bogen",
      "normalized": "bogen",
      "lemma": "bog"
    }
  ]
}
```

### Token Filtering Rules (v0)

- Skip empty tokens.
- Skip pure punctuation tokens.
- Repeated spaces/newlines are allowed and do not break analysis.

### Classification Rules (v1)

- Exact DB match: `known`
- Else lemma found in lexeme DB: `variation`
- Else typo engine path:
  - high confidence: `typo_likely`
  - medium confidence or proper noun risk: `uncertain`
  - low confidence/no candidate: `new`

### Failure Responses

- `503` with JSON `{ "detail": "Database unavailable..." }` when DB is unavailable/locked.
- `503` with JSON `{ "detail": "NLP unavailable..." }` when NLP initialization failed.

## POST `/api/wordbank/lexemes`

Persist a token into the local wordbank with manual source. The backend stores the lemma when available and also stores the typed surface form.

### Request JSON

```json
{
  "surface_token": "bogen",
  "lemma_candidate": "bog"
}
```

### Response JSON

```json
{
  "status": "inserted",
  "stored_lemma": "bog",
  "stored_surface_form": "bogen",
  "source": "manual",
  "message": "Added 'bog' to wordbank."
}
```

### Write Rules (v0)

- Store `lemma_candidate` as the lexeme if present after normalization; otherwise store normalized `surface_token`.
- Store normalized `surface_token` as a surface form linked to that lexeme.
- All writes use source `manual`.
- Duplicate adds are graceful and return `status: "exists"` with HTTP `200`.

### Failure Responses

- `503` with JSON `{ "detail": "Database unavailable..." }` when DB is unavailable/locked.

## POST `/api/tokens/feedback`

Record user actions taken on typo suggestions.

### Request JSON

```json
{
  "raw_token": "spisr",
  "predicted_status": "typo_likely",
  "suggestions_shown": ["spiser"],
  "user_action": "replace",
  "chosen_value": "spiser"
}
```

### Response JSON

```json
{
  "status": "recorded"
}
```

## POST `/api/tokens/ignore`

Suppress token from future typo prompts.

### Request JSON

```json
{
  "token": "MilkoScna",
  "scope": "global"
}
```

### Response JSON

```json
{
  "status": "ignored"
}
```
