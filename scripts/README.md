# Development Scripts

This directory contains repo-local helpers for starting, debugging, testing, and
maintaining Danote. Run scripts from the repository root unless the script says
otherwise.

`run-project.sh` starts the local backend and frontend, loads dotenv files, and
reuses healthy default ports. It is the preferred local startup path.

`dev-app.py` is the **Danote Terminal Controller** (**DTC**), the JSON-only live
API controller for terminal debugging. It auto-detects the local backend and
calls the same HTTP routes used by the UI for wordbank, sentencebank, search,
verification, pronunciation, and developer actions. `wordbank category-status`
polls lemma details and summarizes categories plus verification state, which is
useful for diagnosing post-verification category refresh timing. `wordbank
details --brief` includes the word-card display string, and `wordbank
verify-saved-display` saves one discovered sense then fails if the search-dialog
display differs from the saved word-card display. Search commands accept
`--mode da|en` where the sidebar UI exposes the same Danish/English language
mode split. Use DTC as an extra acceptance check after feature work that is
reachable through the app API.

`dev-search-debug.py` is the older human-readable sidebar search tracer. Keep it
for compatibility; prefer `dev-app.py search trace` when agent-readable JSON is
needed.

Benchmark and fixture-recording scripts should stay read-oriented unless their
name clearly says they write fixtures or reports. Do not add secret-printing or
direct `.env` readers here.

Shell tests live under `scripts/tests/`. Keep script tests lightweight and
focused on command behavior, argument parsing, and bootstrap safety.
