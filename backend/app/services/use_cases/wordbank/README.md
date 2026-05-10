# Wordbank Use Case

Purpose: application workflows for wordbank lookups, mutations, enrichment, and related collaborators.

Main entrypoints:
- `core.py`: public facade for the wordbank use case surface.
- `commands_add_word.py`, `queries_*.py`, `shared.py`: focused workflow helpers.
- `static_details.py`: details fallback for built-in words that are browsable but not stored as DB lexemes.
- `collaborators/`: provider- and subsystem-specific orchestration helpers.

Where to add new behavior:
- Add new workflow logic beside the closest existing command/query module.
- Add provider-specific integration logic under `collaborators/`.
- Keep route handlers calling the facade instead of importing collaborators directly.

Keep these files thin:
- `core.py` should remain the stable facade, not become a catch-all workflow file.
- Collaborators should own one integration concern each.
