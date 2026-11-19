#!/usr/bin/env python3
"""Runs evals/evals.json against the real hook scripts with simulated Claude Code events.

Isolated: HOME points to a temp folder with three fake skills, and SKILL_GATE_STATE to a temp state dir,
so nothing in the real ~/.claude is read or written. Exit code 0 only when every expectation passes.

    python3 evals/run_evals.py
"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
tmp = Path(tempfile.mkdtemp(prefix="skill-gate-eval-"))
home = tmp / "home"
for name in ("using-superpowers", "subagent-driven-development", "tdd"):
    d = home / ".claude" / "skills" / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test skill\n---\n")
env = {**os.environ, "HOME": str(home), "SKILL_GATE_STATE": str(tmp / "state")}
work = tmp / "work"
work.mkdir()
target = work / "file.txt"
target.write_text("one\n")
results = []


def hook(script, event):
    p = subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(event), text=True,
                       capture_output=True, env=env, cwd=str(work), timeout=10)
    return p.returncode, p.stdout, p.stderr


def prompt(sid, text):
    return hook("on_prompt.py", {"session_id": sid, "prompt": text})


def pre_edit(sid):
    return hook("pre_tool.py", {"session_id": sid, "tool_name": "Edit", "tool_input": {"file_path": str(target)}})


def post(sid, tool, inp):
    return hook("post_tool.py", {"session_id": sid, "tool_name": tool, "tool_input": inp})


def stop(sid, active=False):
    return hook("on_stop.py", {"session_id": sid, "stop_hook_active": active})


def check(eval_id, label, ok):
    results.append((eval_id, label, bool(ok)))


# 1: named with "skill <name>"
s = "e1"
rc, out, _ = prompt(s, "apply skill :: skill using-superpowers — Use when starting any conversation")
check(1, "reminder names using-superpowers", rc == 0 and "SKILL GATE" in out and "using-superpowers" in out)
post(s, "Read", {"file_path": str(target)})
rc, _, err = pre_edit(s)
check(1, "edit blocked while not invoked", rc == 2 and "SKILL GATE" in err)
post(s, "Skill", {"skill": "using-superpowers"})
rc, _, _ = pre_edit(s)
check(1, "edit allowed after Skill ran", rc == 0)

# 2: named with a slash; Stop blocks once
s = "e2"
prompt(s, "use this skill create agents for each /subagent-driven-development")
st = json.loads((tmp / "state" / f"{s}.json").read_text())
check(2, "recorded as required", "subagent-driven-development" in st["required"])
rc, out, _ = stop(s)
check(2, "stop blocks while pending", rc == 0 and json.loads(out or "{}").get("decision") == "block")
rc, out, _ = stop(s, active=True)
check(2, "stop_hook_active does not block", rc == 0 and out.strip() == "")

# 3: nothing named
s = "e3"
rc, out, _ = prompt(s, "please run the tests and check the logs then pause")
check(3, "no reminder", rc == 0 and out.strip() == "")
post(s, "Read", {"file_path": str(target)})
rc, _, _ = pre_edit(s)
check(3, "edit after read allowed", rc == 0)

# 4: read gate
s = "e4"
prompt(s, "edit the file")
rc, _, err = pre_edit(s)
check(4, "edit without read blocked", rc == 2 and "not been Read" in err)
post(s, "Read", {"file_path": str(target)})
time.sleep(0.05)
target.write_text("two\n")
os.utime(target, (time.time() + 2, time.time() + 2))
rc, _, err = pre_edit(s)
check(4, "changed on disk blocked", rc == 2 and "changed on disk" in err)
post(s, "Read", {"file_path": str(target)})
rc, _, _ = pre_edit(s)
check(4, "fresh read clears", rc == 0)

# 5: skip skills
s = "e5"
prompt(s, "use the tdd skill for this")
prompt(s, "actually skip skills")
post(s, "Read", {"file_path": str(target)})
rc, _, _ = pre_edit(s)
check(5, "skip skills clears the gate", rc == 0)

passed = sum(ok for _, _, ok in results)
for eid, label, ok in results:
    print(f"{'PASS' if ok else 'FAIL'}  eval {eid}: {label}")
evals = {e for e, _, _ in results}
evals_ok = {e for e in evals if all(ok for x, _, ok in results if x == e)}
print(f"\n{passed}/{len(results)} expectations, {len(evals_ok)}/{len(evals)} evals pass")
sys.exit(0 if passed == len(results) else 1)
