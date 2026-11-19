#!/usr/bin/env python3
"""PostToolUse hook (matcher: Skill|Read|Edit|Write|MultiEdit|NotebookEdit).

Records what actually happened so the gates in pre_tool.py have evidence:
- Skill invoked  -> mark it done
- Read           -> remember the file's mtime at read time
- Edit/Write     -> refresh the file's mtime (our own write is not a foreign change)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from _common import *

ev = read_event()
sid = ev.get("session_id")
tool = ev.get("tool_name", "")
inp = ev.get("tool_input", {}) or {}
st = load_state(sid)

if tool == "Skill":
    name = str(inp.get("skill", "")).lstrip("/")
    st["invoked"][name] = time.strftime("%Y-%m-%dT%H:%M:%S")
    st["invoked"][name.split(":")[-1]] = st["invoked"][name]
    # also count plugin-prefixed form if the user named it bare, and vice versa
    for req in list(st["required"]):
        if req.split(":")[-1] == name.split(":")[-1]:
            st["invoked"][req] = st["invoked"][name]

elif tool in {"Read"} | WRITE_TOOLS:
    path = inp.get("file_path") or inp.get("notebook_path")
    if path and os.path.exists(path):
        st["reads"][path] = os.path.getmtime(path)

save_state(sid, st)
sys.exit(0)
