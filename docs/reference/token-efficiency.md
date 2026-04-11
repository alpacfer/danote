# Token Efficiency

Runtime token hygiene for Claude Code sessions.

## 1. Fixed session costs

Every session loads these automatically:

| Source | Size | Controllable |
|---|---|---|
| System prompt | ~15KB | No |
| Superpowers plugin CLAUDE.md | ~6.5KB | No |
| using-superpowers SKILL (SessionStart) | ~5.4KB | No |
| CLAUDE.md | ~7KB | Yes (compressed) |
| Rules (3 files, contextual) | ~3.7KB | Yes (compressed) |

Fixed floor ~34KB before first message. Controllable portion ~10.7KB — compress to shrink.

## 2. Tool result discipline

**Grep**: default `head_limit` 250 usually fine. Lower for broad searches.

```
head_limit: 50   # when pattern matches many files
```

**Read**: use `offset`+`limit` for large files. Don't read 500 lines to find 10-line function.

```
offset: 120, limit: 30   # jump to known region
```

**Bash**: pipe long output through `head`.

```bash
some-command | head -40
```

**Glob over Bash ls**: Glob returns file paths only. `ls` dumps full listing into context.

## 3. Skill discipline

Each skill invocation = 3–8KB loaded into context.

- Don't invoke speculatively
- Match skill weight to task:
  - `caveman:caveman-commit` (~1KB) for commits — not full commit workflow
  - `superpowers:brainstorming` only for genuinely new features
  - `writing-plans` + `brainstorming` together = ~20KB; use only when spec is truly missing
  - Bug fixes: `superpowers:systematic-debugging` (~4KB), not brainstorming

## 4. Session hygiene

- `/compact` — mid-session summary when context grows large; use before switching subtask
- `/clear` — between unrelated tasks; resets context entirely

`session-context.sh` re-injects 10-line summary after compaction. Lean by design — don't fight it.

## 5. effortLevel toggle

`~/.claude/settings.json`:

```json
{ "effortLevel": "low" }
```

- `"low"` — reduces planning depth; good for small focused tasks
- `"medium"` — complex multi-file refactors; more thorough planning
