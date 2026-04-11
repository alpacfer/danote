# Token Efficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce per-session input token consumption ~40% by compressing controllable context files and adopting runtime discipline patterns.

**Architecture:** Three levers — (1) compress static context files loaded every session, (2) compress rule files loaded on file edits, (3) apply runtime discipline for tool results and skill invocations.

**Tech Stack:** caveman:compress skill, Claude Code settings.json, existing hook infrastructure.

---

## Token Audit (baseline)

Per-session mandatory loads:

| Source | Size | Controllable |
|---|---|---|
| CLAUDE.md | 3,303 B | Yes |
| AGENTS.md | 3,954 B | Yes |
| Rules (3 files, contextual) | 4,057 B | Yes |
| Superpowers CLAUDE.md (plugin) | 6,490 B | No |
| using-superpowers SKILL (SessionStart) | 5,421 B | No |
| System prompt | ~15 KB | No |

Controllable total: **~11 KB per session**. Target: compress to ~5–6 KB (45% reduction).

Per skill invocation (on-demand): 3–8 KB each. Minimize skill loads.

---

## Task 1: Compress CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`
- Backup created automatically by caveman:compress at `CLAUDE.md.human-backup`

- [ ] **Step 1: Invoke caveman:compress on CLAUDE.md**

```
/compress CLAUDE.md
```

Or via Skill tool: `Skill({ skill: "caveman:compress", args: "CLAUDE.md" })`

- [ ] **Step 2: Verify backup created**

```bash
ls -la CLAUDE.md CLAUDE.md.human-backup
```

Expected: both files exist; `CLAUDE.md` smaller than `CLAUDE.md.human-backup`.

- [ ] **Step 3: Verify no semantic loss**

Read `CLAUDE.md` and compare against backup. All commands, paths, architecture layers, hook names, and agent table must still be present. Abbreviations and caveman grammar are fine — missing facts are not.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "chore: compress CLAUDE.md to reduce per-session input tokens"
```

---

## Task 2: Compress AGENTS.md

**Files:**
- Modify: `AGENTS.md`
- Backup: `AGENTS.md.human-backup`

- [ ] **Step 1: Invoke caveman:compress on AGENTS.md**

```
/compress AGENTS.md
```

Or: `Skill({ skill: "caveman:compress", args: "AGENTS.md" })`

- [ ] **Step 2: Verify backup**

```bash
ls -la AGENTS.md AGENTS.md.human-backup
```

- [ ] **Step 3: Verify semantic fidelity**

Check that all sections survive: Verification sequence, Architecture map, Change policy, Documentation Sync rules, Maintainability guardrails (size limits, refactor triggers), Self-verification checklist, Quick file lookup.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "chore: compress AGENTS.md to reduce per-session input tokens"
```

---

## Task 3: Compress Rule Files

**Files:**
- Modify: `.claude/rules/frontend.md`, `.claude/rules/api-design.md`, `.claude/rules/testing.md`
- Backups auto-created

These load only when editing matching file types, but they load on nearly every frontend or backend task.

- [ ] **Step 1: Compress all three rule files**

```
/compress .claude/rules/frontend.md
/compress .claude/rules/api-design.md
/compress .claude/rules/testing.md
```

Run each separately (compress one, verify, then next).

- [ ] **Step 2: Verify frontend.md**

Must retain: component/hook boundary rules, shadcn-first install workflow, TypeScript `any` ban, file size table (300/450 targets), `@/*` alias.

- [ ] **Step 3: Verify api-design.md**

Must retain: routes-thin rule, DTO-first policy, schema location (`api/schemas/v1/`), layering order.

- [ ] **Step 4: Verify testing.md**

Must retain: pytest and vitest patterns, no-mock-database rule (if present), test file size limits.

- [ ] **Step 5: Commit**

```bash
git add .claude/rules/
git commit -m "chore: compress rule files to reduce per-edit-session input tokens"
```

---

## Task 4: Runtime Token Hygiene (documentation + settings)

**Files:**
- Modify: `~/.claude/settings.json` (global)
- Create: `docs/token-efficiency.md` (reference)

These are behavioral changes, not content compression.

### 4a: Review effortLevel setting

- [ ] **Step 1: Check current effortLevel**

```bash
cat ~/.claude/settings.json | grep effortLevel
```

Current: `"effortLevel": "medium"`

- [ ] **Decision gate:** `effortLevel` controls how aggressively Claude plans multi-step tasks. "low" reduces thinking tokens; "medium" improves output on complex tasks. For this codebase (complex NLP + frontend), keep `"medium"` unless the user finds quality acceptable at `"low"`. **No change recommended** — document as a manual toggle instead.

### 4b: Document runtime practices

- [ ] **Step 2: Create `docs/token-efficiency.md`**

```markdown
# Token Efficiency Guide

## What loads every session (fixed cost)
- System prompt: ~15KB (Anthropic-controlled)
- Superpowers plugin CLAUDE.md: ~6.5KB (plugin-controlled)
- using-superpowers SKILL injected at SessionStart: ~5.4KB (plugin-controlled)
- CLAUDE.md + AGENTS.md: compressed to ~5KB

## Runtime practices that reduce variable costs

### Tool result size
- Grep: always set `head_limit` (default 250 is usually fine; set lower for broad searches)
- Read: use `offset`+`limit` for large files — never read a 500-line file to find a 10-line function
- Bash: pipe long outputs through `head -N`

### Skill loading
- Each skill invocation loads 3–8KB into context
- Don't invoke skills "just in case" — the 1% rule applies only when genuinely uncertain
- Prefer lightweight skills (caveman:caveman-commit) over heavy ones (brainstorming) for simple tasks

### Session hygiene
- Use `/compact` when context grows large (mid-session summary)
- Use `/clear` between unrelated tasks
- The session-context.sh hook re-injects a 10-line summary after compaction — lean by design

### Skill discipline
- writing-plans + brainstorming together load ~20KB. Only use for genuinely new features.
- For bug fixes, use superpowers:systematic-debugging (~4KB) not brainstorming.
- For commits, use caveman:caveman-commit (small) not a full workflow.

## effortLevel toggle
`~/.claude/settings.json`: `"effortLevel": "low"` reduces planning depth on simple tasks.
Switch to `"medium"` for complex multi-file refactors. Switch back after.
```

- [ ] **Step 3: Commit**

```bash
git add docs/token-efficiency.md
git commit -m "docs: add token efficiency guide for Claude Code sessions"
```

---

## Expected Outcome

| Source | Before | After |
|---|---|---|
| CLAUDE.md | 3,303 B | ~1,500 B |
| AGENTS.md | 3,954 B | ~1,800 B |
| Rules (3 files) | 4,057 B | ~1,800 B |
| **Controllable total** | **~11KB** | **~5KB** |
| **Savings per session** | — | **~6KB (~1,500 tokens)** |

Skill invocation discipline provides additional variable savings of 3–8KB per avoided skill load.
