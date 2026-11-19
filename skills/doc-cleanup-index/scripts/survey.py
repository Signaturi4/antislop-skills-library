#!/usr/bin/env python3
"""Inventory .md/.html/.pdf docs under ROOT and seed the tag allow-list.

Usage: survey.py ROOT --index DIR [--prune NAME ...]
Writes DIR/inventory.jsonl and, if missing, DIR/tag_pool.json (starter roles/subjects + projects discovered from
top-level folders and git repo names). Prints counts per top folder and extension. Secret files are never listed.
"""
import argparse, collections, json, os, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import walk_docs, repo_of, is_repo  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("--index", required=True); ap.add_argument("--prune", nargs="*", default=[])
a = ap.parse_args()
root = os.path.abspath(a.root); os.makedirs(a.index, exist_ok=True)
cnt = collections.Counter(); projects = {}
with open(os.path.join(a.index, "inventory.jsonl"), "w") as out:
    for p in walk_docs(root, a.prune):
        rel = os.path.relpath(p, root); repo = repo_of(p, root)
        st = os.stat(p)
        out.write(json.dumps({"path": rel, "ext": os.path.splitext(p)[1].lower(), "size": st.st_size,
                              "mtime": int(st.st_mtime), "repo": os.path.relpath(repo, root) if repo else None}) + "\n")
        cnt[(rel.split(os.sep)[0] if os.sep in rel else ".", os.path.splitext(p)[1].lower())] += 1


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"^\d+[-_ ]*", "", s.lower())).strip("-")


# projects: git repos anywhere (depth <= 3) + folders under any top-level folder whose name says project(s)
for r, ds, _ in os.walk(root):
    depth = os.path.relpath(r, root).count(os.sep)
    ds[:] = [d for d in ds if not d.startswith(".") and d not in ("node_modules",)]
    for d in ds:
        full = os.path.join(r, d)
        if is_repo(full) or re.search(r"project|client|repo", os.path.basename(r), re.I):
            if slug(d):
                projects[slug(d)] = {"desc": f"project found at {os.path.relpath(full, root)}", "added": time.strftime("%F"),
                                     "reason": "survey"}
    if depth >= 2:
        ds[:] = []
pool_path = os.path.join(a.index, "tag_pool.json")
if not os.path.exists(pool_path):
    starter = json.load(open(os.path.join(os.path.dirname(__file__), "..", "references", "tag_pool.starter.json")))
    starter["project"].update(projects)
    json.dump(starter, open(pool_path, "w"), indent=1)
    print(f"seeded {pool_path}: " + ", ".join(f"{k} {len(v)}" for k, v in starter.items()))
else:
    print(f"kept existing {pool_path}; projects found now: {', '.join(sorted(projects))}")
print(f"{sum(cnt.values())} docs")
for (top, ext), n in sorted(cnt.items(), key=lambda x: -x[1])[:30]:
    print(f"{n:6} {top} {ext}")
