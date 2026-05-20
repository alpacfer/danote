# `frontend/src/app/hooks/wordbank/`

Focused workflow hooks for wordbank actions.

Each file owns one user-facing workflow and keeps request state, API calls,
toasts, and refresh invalidation close together.

Use this directory for wordbank-specific actions such as pronunciation,
verification, category rethinking, variation completion, translation refresh,
and deletion.

Do not put generic app navigation, lexicon fetching, or sentencebank save logic
here. Those live in the app controller, `use-lexicon-data.ts`, and the
sentencebank hook directory.

Hooks in this directory should accept only the state setters and callbacks they
need from the composition layer. Prefer returning small action functions and
loading maps over exposing internal request helpers.

When adding a new workflow, first check whether it belongs to an existing file
with the same backend route family. If it has its own loading state or dialog
state, use a sibling hook instead of expanding the large composition hook.
