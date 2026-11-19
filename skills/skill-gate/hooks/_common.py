#!/usr/bin/env python3
"""Shared helpers for the skill-gate hooks.

State lives in ~/.claude/skill-gate/<session_id>.json:
  { "required": {"tdd": "prompt text that named it", ...},
    "invoked":  {"tdd": "<iso time>", ...},
    "reads":    {"/abs/path": <mtime at read>, ...} }
"""
import json, os, re, sys, time
from pathlib import Path

STATE_DIR = Path(os.environ.get("SKILL_GATE_STATE", Path.home() / ".claude" / "skill-gate"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Tools whose use counts as "writing code"
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Where skills live. Any directory under these that contains SKILL.md is a skill.
SKILL_ROOTS = [
    Path.home() / ".claude" / "skills",
    Path.cwd() / ".claude" / "skills",
]
for extra in os.environ.get("SKILL_GATE_ROOTS", "").split(":"):
    if extra:
        SKILL_ROOTS.append(Path(extra).expanduser())


def read_event():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def state_path(session_id):
    return STATE_DIR / f"{session_id or 'nosession'}.json"


def load_state(session_id):
    p = state_path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"required": {}, "invoked": {}, "reads": {}}


def save_state(session_id, st):
    state_path(session_id).write_text(json.dumps(st, indent=1))


def installed_skills():
    """name -> SKILL.md path for every installed skill (plugins included)."""
    found = {}
    for root in SKILL_ROOTS:
        if not root.exists():
            continue
        for md in root.rglob("SKILL.md"):
            name = md.parent.name
            # frontmatter name wins over directory name
            try:
                head = md.read_text(errors="ignore")[:2000]
                m = re.search(r"^name:\s*([A-Za-z0-9_:.-]+)", head, re.M)
                if m:
                    name = m.group(1)
            except Exception:
                pass
            found.setdefault(name, str(md))
            found.setdefault(md.parent.name, str(md))
    return found


def skills_named_in(text, known):
    """Skills the prompt refers to: /name, bare name, or 'use the X skill'."""
    hits = set()
    low = text.lower()
    for name in known:
        n = name.lower()
        short = n.split(":")[-1]
        pats = [
            rf"(^|\s)/{re.escape(n)}\b",
            rf"(^|\s)/{re.escape(short)}\b",
            rf"\b{re.escape(short)}\s+skill\b",
            rf"\bskill\s+{re.escape(short)}\b",
            rf"\buse\s+{re.escape(short)}\b",
            rf"\bwith\s+{re.escape(short)}\b",
            rf"\bfollow\s+{re.escape(short)}\b",
        ]
        if any(re.search(p, low) for p in pats):
            hits.add(name)
    return sorted(hits)


def block(reason):
    """Exit 2: Claude Code blocks the action and feeds stderr back to Claude."""
    sys.stderr.write(reason.rstrip() + "\n")
    sys.exit(2)


def add_context(text):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": text}}))
    sys.exit(0)
