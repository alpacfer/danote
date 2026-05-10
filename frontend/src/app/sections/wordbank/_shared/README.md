# `wordbank/_shared`

Shared render helpers for Wordbank built-in pinned pages.

## What Lives Here

- `pinned-pages-registry.ts` maps visible grouped pinned pages and legacy sentinels.
- `pinned-page-layout.tsx` provides the scrollable page shell.
- `pinned-word-card.tsx` renders the simplified clickable built-in word card.
- `pinned-word-grid.tsx` lays out consistent card grids for every pinned tab.
- `use-pinned-page-audio.ts` plays seeded number, presaved-word, or normal word audio.

## What Does Not Live Here

- Topic-specific word lists stay in sibling domain folders such as `pronouns/`.
- Wordbank data fetching and navigation state stay in app hooks.
- shadcn primitives stay in `frontend/src/components/ui/`.

## Choosing A File

- Add new grouped pinned-page routing metadata to the registry.
- Put reusable pinned-card visual changes in `pinned-word-card.tsx`.
- Put page-specific tab composition in the owning domain page.
- Keep these helpers stateless except for the audio hook.
