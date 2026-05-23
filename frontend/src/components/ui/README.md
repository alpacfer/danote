# UI Components (`frontend/src/components/ui/`)

This directory contains reusable, low-level UI primitives and design system components for danote.

## What Lives Here
- Standard, generic UI components (e.g., `button.tsx`, `card.tsx`, `dialog.tsx`, `input.tsx`, `badge.tsx`) managed with shadcn/ui.
- Composition-ready design system tokens and helper elements (e.g., `kbd.tsx`, `spinner.tsx`, `scrollable-badge-row.tsx`).
- Styled wrapper components targeting maximum accessibility and consistency.

## What Does NOT Live Here
- Feature-specific UI components or layout sections (these live in `frontend/src/app/sections/` or `frontend/src/app/chrome/`).
- Business logic, routing, domain data-fetching, or custom application hooks (these live in `frontend/src/app/hooks/` or `frontend/src/app/core/`).

## How to Choose & Use Sibling Files
- Prefer using or extending these existing shadcn/ui primitives before building custom elements.
- When a new standard UI element is required, install it via the shadcn CLI: `npx shadcn@latest add <component>`.
- Keep changes to these generated files minimal. Do not rewrite generated internal APIs unless explicitly requested.
