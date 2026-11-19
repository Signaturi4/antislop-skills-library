#!/usr/bin/env python3
"""Validator: how often does a prompt that names a skill actually trigger it?

Reads Claude Code transcripts (~/.claude/projects/**/*.jsonl), finds user
prompts that name an installed skill, and checks whether a Skill tool_use for
that skill follows within the same session. Prints the trigger rate overall
and per skill, so the 63.5% miss rate from the usage analysis can be tracked
week over week after the gate is installed.

Usage:
  skill_usage_report.py [--since 2026-10-01] [--projects ~/.claude/projects]
  skill_usage_report.py --library ~/path/to/my-skills   # also lists installed skills missing from the library
"""
import argparse, json, os, sys, glob, datetime
from pathlib import Path
# works from the skill folder (../hooks) and from the installed copy in ~/.claude/scripts
for _d in (Path(__file__).resolve().parent.parent / "hooks", Path.home() / ".claude" / "hooks" / "skill-gate"):
    if (_d / "_common.py").exists():
        sys.path.insert(0, str(_d))
        break
from _common import installed_skills, skills_named_in

ap = argparse.ArgumentParser()
ap.add_argument("--projects", default=str(Path.home() / ".claude" / "projects"))
ap.add_argument("--since", default=None)
ap.add_argument("--library", default=None, help="path to the skills library repo; report skills not in it")
args = ap.parse_args()
since = datetime.datetime.fromisoformat(args.since) if args.since else None

known = installed_skills()
named_total = 0
hit_total = 0
per_skill = {}
ran = {}

for f in glob.glob(os.path.join(args.projects, "**", "*.jsonl"), recursive=True):
    prompts = []   # (ts, skill)
    invoked = []   # (ts, skill)
    with open(f, errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = rec.get("timestamp")
            try:
                t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None) if ts else None
            except Exception:
                t = None
            if since and t and t < since:
                continue
            msg = rec.get("message", {}) or {}
            content = msg.get("content")
            if rec.get("type") == "user" and isinstance(content, str):
                for s in skills_named_in(content, known):
                    prompts.append((t, s))
            elif rec.get("type") == "assistant" and isinstance(content, list):
                for blk in content:
                    if blk.get("type") == "tool_use" and blk.get("name") == "Skill":
                        s = str((blk.get("input") or {}).get("skill", "")).lstrip("/")
                        invoked.append((t, s))
                        ran[s] = ran.get(s, 0) + 1
    for t, s in prompts:
        named_total += 1
        d = per_skill.setdefault(s, [0, 0])
        d[0] += 1
        ok = any(i.split(":")[-1] == s.split(":")[-1] and (t is None or it is None or it >= t) for it, i in invoked)
        if ok:
            hit_total += 1
            d[1] += 1

print(f"Prompts naming a skill: {named_total}")
if named_total:
    print(f"Triggered: {hit_total}  ({100*hit_total/named_total:.1f}%)   Missed: {named_total-hit_total}  ({100*(named_total-hit_total)/named_total:.1f}%)")
print(f"Distinct skills that ran: {len(ran)}\n")
print(f"{'skill':40} {'named':>6} {'ran':>6} {'rate':>6}")
for s, (n, h) in sorted(per_skill.items(), key=lambda kv: -kv[1][0]):
    print(f"{s:40} {n:6} {h:6} {100*h/n:5.0f}%")

if args.library:
    lib = {p.parent.name for p in Path(args.library).expanduser().rglob("SKILL.md")}
    inst = {n.split(":")[-1] for n in known}
    used = {s.split(":")[-1] for s in ran}
    print("\nSkills that RAN but are not in the library:")
    for s in sorted(used - lib):
        print("  -", s, known.get(s, ""))
    print("\nInstalled skills not in the library:")
    for s in sorted(inst - lib):
        print("  -", s)
