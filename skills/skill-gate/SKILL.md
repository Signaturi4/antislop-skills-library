---
name: skill-gate
description: Enforces that any skill named in a prompt is actually invoked before code is written, and that files are Read before Edit (and re-read if changed on disk). Use when setting up, checking or debugging skill enforcement, or when asked why an edit was blocked by SKILL GATE or READ GATE.
---

# skill-gate

Four hooks turn "the prompt named a skill" into "the skill ran", using the same
mechanic as the read-before-edit rule: record evidence, block the action that
needs it, tell Claude exactly what to do instead.

| Hook | Matcher | Does |
|---|---|---|
| UserPromptSubmit | all prompts | Finds installed skills named in the prompt (`/tdd`, `tdd skill`, `use tdd`). Records them as required. Injects a reminder to invoke them before editing. |
| PreToolUse | Edit, Write, MultiEdit, NotebookEdit | Blocks (exit 2) while a required skill is uninvoked. Blocks Edit on a file not Read this session or changed on disk since the last Read. |
| PostToolUse | Skill, Read, Edit, Write | Marks skills invoked; records file mtimes at Read/Write time. |
| Stop | end of turn | Refuses to end the turn while a named skill was never invoked. Fires once (stop_hook_active guard). |

State per session: `~/.claude/skill-gate/<session_id>.json`.

## Install

`bash install.sh` copies the hooks to `~/.claude/hooks/skill-gate/` and the report script to
`~/.claude/scripts/`, then merges `settings.hooks.json` into `~/.claude/settings.json` (backup:
`settings.json.bak`). Entries already present are not added twice. Restart Claude Code so the hooks load.

## Tests

`python3 evals/run_evals.py` runs the cases in `evals/evals.json` against the real hook scripts with a
temporary `HOME` and state dir, so the real `~/.claude` is not touched.

## When an edit is blocked

- `SKILL GATE: ... not been invoked` -> call the Skill tool with that name, follow the SKILL.md, retry.
- `READ GATE: ... not been Read` -> Read the file, retry.
- `READ GATE: ... changed on disk` -> Read it again, retry.
- Skill really does not apply -> say so in one line; the user replies `skip skills` to clear the gate for that session.

## Measuring

`python3 ~/.claude/scripts/skill_usage_report.py --since 2026-11-01`
prints named vs triggered per skill. Baseline before install: 63.5% of prompts
that named a skill never triggered it. Target: under 10%.

Add `--library <path to skills repo>` to list skills that ran locally but are
missing from the library.

## Limits

- Detection is by name match against installed skills, so a skill must be
  installed (`~/.claude/skills`, `.claude/skills`, or dirs in `SKILL_GATE_ROOTS`)
  to be gated.
- Subagents started with the Agent tool run their own hooks only if the same
  settings apply; the gate is per session_id.
- Hooks shell out to python3; keep them under the 10 s timeout.
