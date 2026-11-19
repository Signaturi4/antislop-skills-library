#!/usr/bin/env python3
"""UserPromptSubmit hook.

Detects skills the prompt names, records them as REQUIRED for this session,
and injects a reminder so the model invokes them with the Skill tool before
it writes code. This is the step that turns "named a skill" into "ran it".
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import *

ev = read_event()
sid = ev.get("session_id")
prompt = ev.get("prompt", "") or ""
known = installed_skills()
named = skills_named_in(prompt, known)

st = load_state(sid)

# A prompt that explicitly waives the gate
if "skip skills" in prompt.lower() or "no-skill-gate" in prompt.lower():
    st["required"] = {}
    save_state(sid, st)
    sys.exit(0)

if named:
    for n in named:
        st["required"][n] = prompt[:200]
    save_state(sid, st)
    pending = [n for n in st["required"] if n not in st["invoked"]]
    add_context(
        "SKILL GATE: this prompt names the skill(s) " + ", ".join(named) + ". "
        "Invoke each with the Skill tool and follow its SKILL.md BEFORE any Edit/Write. "
        "Edits are blocked until these are invoked: " + ", ".join(pending) + ". "
        "If a named skill truly does not apply, say why in one line and the user can reply 'skip skills'."
    )

sys.exit(0)
