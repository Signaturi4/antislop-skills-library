#!/usr/bin/env python3
"""Stop hook: refuse to finish the turn while a named skill was never invoked.

Only fires once per turn (stop_hook_active guard) so it cannot loop.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from _common import *

ev = read_event()
if ev.get("stop_hook_active"):
    sys.exit(0)
st = load_state(ev.get("session_id"))
pending = [n for n in st["required"] if n not in st["invoked"]]
if pending:
    print(json.dumps({
        "decision": "block",
        "reason": "SKILL GATE: skill(s) " + ", ".join(pending) +
                  " were named by the user but never invoked. Invoke them with the Skill tool "
                  "and apply them, or state in one line why they do not apply."
    }))
sys.exit(0)
