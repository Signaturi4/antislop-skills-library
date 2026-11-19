#!/usr/bin/env python3
"""Propose folder moves from tags: project -> one of 7 fixed areas. Writes a plan; moves nothing.

Usage: plan_moves.py ROOT --index DIR [--target projects] [--areas areas.json]
Rules (learned on a real 3,000-doc run where a naive plan would have broken skills and agents):
- Only business docs move. A doc's top subject maps to one of 7 areas (strategy, sales, marketing, research, design,
  operations, reference); the detailed subject stays a tag, never a folder, so no project gets more than 7 folders.
- Technical docs (subject maps to `reference`) inside a git repo stay next to their code.
- Working files never move: SKILL.md, AGENTS.md, CLAUDE.md, GEMINI.md, README.md, INDEX.md, prompts, templates,
  anything inside a skill folder (a folder with SKILL.md above it) or inside .claude / .agents / .github.
- Docs move toward the root only (target depth <= source depth), never into a repo.
- Unsure project -> review list, not a move: project tag is a fallback (general / other-client / score 0), or the
  path names a different known project than the tag.
Output: DIR/moves.plan.json ([{src, dst, why}]), DIR/review.json and DIR/PLAN.md for the owner to approve.
"""
import argparse, collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import repo_of  # noqa: E402

AREAS = {  # top-level subject -> area folder; anything unlisted -> reference
    "strategy": "strategy", "sales": "sales", "marketing": "marketing", "research": "research", "design": "design",
    "operations": "operations", "legal-compliance": "operations", "docs-meta": "operations",
}
KEEP_NAMES = {"skill.md", "agents.md", "claude.md", "gemini.md", "readme.md", "index.md", "license.md", "changelog.md"}
KEEP_DIRS = {".claude", ".agents", ".github", ".cursor", "node_modules"}
UNSURE = {"general", "other-client"}

ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--index", required=True)
ap.add_argument("--target", default="projects"); ap.add_argument("--areas", help="JSON {subject: area} overrides")
a = ap.parse_args(); ROOT = os.path.abspath(a.root)
if a.areas:
    AREAS.update(json.load(open(a.areas)))
projects = set(json.load(open(os.path.join(a.index, "tag_pool.json")))["project"])


def working_file(rel):
    name = os.path.basename(rel).lower()
    if name in KEEP_NAMES or re.search(r"prompt|template|\.tmpl\.", name):
        return True
    parts = rel.split(os.sep)
    if KEEP_DIRS & set(parts):
        return True
    d = os.path.dirname(os.path.join(ROOT, rel))
    while d.startswith(ROOT) and d != ROOT:  # inside a skill folder
        if os.path.exists(os.path.join(d, "SKILL.md")):
            return True
        d = os.path.dirname(d)
    return False


def path_project(rel):
    """Known project named by a folder in the path (deepest wins), else None."""
    hits = [s for s in rel.split(os.sep)[:-1] if s in projects and s not in UNSURE]
    return hits[-1] if hits else None


plan, review, skipped, taken = [], [], collections.Counter(), set()
for line in open(os.path.join(a.index, "tags.jsonl")):
    d = json.loads(line); src = d["path"]
    if not os.path.exists(os.path.join(ROOT, src)):
        continue
    if working_file(src):
        skipped["working file (skill, agent config, readme, prompt, template)"] += 1; continue
    (proj, score) = d["tags"]["project"][0]
    area = AREAS.get(d["tags"]["subject"][0][0].split("/")[0], "reference")
    in_repo = repo_of(os.path.join(ROOT, src), ROOT)
    if area == "reference" and in_repo:
        skipped["technical doc stays with its code"] += 1; continue
    pp_ = path_project(src)
    if proj in UNSURE or score == 0 or (pp_ and pp_ != proj):
        review.append({"src": src, "tag": proj, "path_says": pp_, "insight": d.get("insight", "")})
        skipped["unsure project: review list"] += 1; continue
    folder = os.path.join(a.target, proj)
    if repo_of(os.path.join(ROOT, folder), ROOT):  # the project folder is a repo: docs go to a sibling folder
        folder = os.path.join(a.target, f"{proj}-docs")
    dst = os.path.join(folder, area, os.path.basename(src))
    if dst in taken:
        dst = os.path.join(folder, area, f"{os.path.basename(os.path.dirname(src))}-{os.path.basename(src)}")
    if os.path.normpath(dst) == os.path.normpath(src):
        continue
    if dst.count(os.sep) > src.count(os.sep):
        skipped["would move deeper (not toward the root)"] += 1; continue
    taken.add(dst)
    plan.append({"src": src, "dst": dst, "why": f"project {proj}, area {area}" + (", extracted from repo" if in_repo else "")})

json.dump(plan, open(os.path.join(a.index, "moves.plan.json"), "w"), indent=1)
json.dump(review, open(os.path.join(a.index, "review.json"), "w"), indent=1)
by = collections.defaultdict(list)
for m in plan:
    by[os.path.dirname(m["dst"])].append(m)
out = ["# Proposed moves (approve or edit moves.plan.json, then run move.py --apply)", "",
       f"{len(plan)} moves, {len(review)} to review. Not moved: " + (", ".join(f"{n} {k}" for k, n in skipped.items()) or "none"), ""]
kids = collections.defaultdict(set)  # folders each parent would hold after the moves (existing + new)
for f in by:
    parts = f.split(os.sep)
    for i in range(1, len(parts)):
        kids[os.sep.join(parts[:i])].add(parts[i])
for parent, new in sorted(kids.items()):
    p = os.path.join(ROOT, parent)
    have = {x for x in os.listdir(p) if not x.startswith(".") and os.path.isdir(os.path.join(p, x))} if os.path.isdir(p) else set()
    if len(have | new) > 7:
        out.append(f"WARNING: `{parent}` would hold {len(have | new)} folders (max 7): group projects (e.g. clients / "
                   f"products / internal) or send company-level docs to their own root folder first.")
for folder in sorted(by):
    out.append(f"## {folder} ({len(by[folder])})")
    out += [f"- `{m['src']}`" for m in by[folder][:30]]
    if len(by[folder]) > 30:
        out.append(f"- ... {len(by[folder]) - 30} more")
if review:
    out += ["", "## Review: project unsure (not moved)"]
    out += [f"- `{r['src']}`: tag `{r['tag']}`" + (f", path says `{r['path_says']}`" if r["path_says"] else "") for r in review[:60]]
    if len(review) > 60:
        out.append(f"- ... {len(review) - 60} more in review.json")
open(os.path.join(a.index, "PLAN.md"), "w").write("\n".join(out) + "\n")
print(f"{len(plan)} moves, {len(review)} to review -> {a.index}/PLAN.md; not moved: {dict(skipped)}")
