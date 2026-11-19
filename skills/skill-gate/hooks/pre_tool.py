#!/usr/bin/env python3
"""PreToolUse hook (matcher: Edit|Write|MultiEdit|NotebookEdit|Read|Skill).

Two gates, same mechanic as read-before-edit:

1. Skill gate: if the session has REQUIRED skills that were never invoked,
   block the write and tell Claude which Skill call is missing.
2. Read-before-edit gate: block Edit/MultiEdit on a file that was not Read in
   this session, or that changed on disk since it was last Read.

Read and Skill calls are only recorded here; PostToolUse marks them done.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import *

ev = read_event()
sid = ev.get("session_id")
tool = ev.get("tool_name", "")
inp = ev.get("tool_input", {}) or {}
st = load_state(sid)

if tool in WRITE_TOOLS:
    pending = [n for n in st["required"] if n not in st["invoked"]]
    if pending:
        block(
            "SKILL GATE: the user asked for skill(s) " + ", ".join(pending) +
            " but they have not been invoked in this session. "
            "Call the Skill tool with skill=\"" + pending[0] + "\" (and the others) first, "
            "follow the returned SKILL.md, then retry this edit."
        )

    path = inp.get("file_path") or inp.get("notebook_path")
    if tool in {"Edit", "MultiEdit", "NotebookEdit"} and path and os.path.exists(path):
        seen = st["reads"].get(path)
        mtime = os.path.getmtime(path)
        if seen is None:
            block(f"READ GATE: {path} has not been Read in this session. Read it before editing.")
        if mtime > seen + 0.001:
            block(f"READ GATE: {path} changed on disk since you last Read it. Read it again before editing.")

sys.exit(0)
