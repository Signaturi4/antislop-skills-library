#!/usr/bin/env python3
"""Run the doc-cleanup-index evals on a throw-away fixture (keyword backend: no model, no network).

Usage: python3 evals/run_evals.py [WORKDIR]   -> prints each assertion PASS/FAIL and the pass rate; exit 1 on any FAIL.
"""
import json, os, sqlite3, subprocess, sys, tempfile

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = os.path.join(K, "scripts")
W = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dci-eval-")
ws, ix, tr = os.path.join(W, "ws"), os.path.join(W, "index"), os.path.join(W, "trash")
res = []


def run(*a, ok=(0,)):
    r = subprocess.run([sys.executable, os.path.join(S, a[0]), *a[1:]], capture_output=True, text=True)
    if r.returncode not in ok:
        print(r.stdout, r.stderr)
    return r


def check(eid, name, cond):
    res.append((eid, name, bool(cond))); print(f"{'PASS' if cond else 'FAIL'} eval {eid}: {name}")


subprocess.run(["bash", os.path.join(K, "evals", "make_fixture.sh"), ws], check=True)
run("survey.py", ws, "--index", ix)
inv = [json.loads(l)["path"] for l in open(os.path.join(ix, "inventory.jsonl"))]
# eval 4: structure
r = run("check_structure.py", ws, "--write", ok=(1,))
check(4, "check fails with exit 1 naming the root level", r.returncode == 1 and r.stdout.startswith(".:"))
check(4, "INDEX.md is written", os.path.exists(os.path.join(ws, "INDEX.md")))
# eval 3: links
run("link_scan.py", ws, "--out", os.path.join(ix, "broken.md"))
check(3, "broken link report names missing.md", "missing.md" in open(os.path.join(ix, "broken.md")).read())
# eval 2: tags
run("tag_docs.py", ws, "--index", ix, "--backend", "keyword")
tags = {d["path"]: d["tags"] for d in map(json.loads, open(os.path.join(ix, "tags.jsonl")))}
check(2, "every doc has 1-3 tags in each of project, role, subject",
      len(tags) == len(inv) and all(1 <= len(t[f]) <= 3 for t in tags.values() for f in ("project", "role", "subject")))
check(2, "a sub-subject tag (with /) is used", any("/" in x for t in tags.values() for x, _ in t["subject"]))
pool = json.load(open(os.path.join(ix, "tag_pool.json")))
new = [k for k, v in pool["subject"].items() if v.get("added") and v.get("reason")]
aq = tags.get("hobbies/aquarium.md", {}).get("subject", [])
check(2, "a new tag is added with added+reason and used by the off-topic doc", new and any(x in new for x, _ in aq))
check(2, ".env is never indexed", not any(p.endswith(".env") for p in inv))
# eval 3: graph
run("build_graph.py", ws, "--index", ix)
db = sqlite3.connect(os.path.join(ix, "graph.db"))
docs = {r[0] for r in db.execute("select path from nodes where kind='doc'")}
rels = {r[0] for r in db.execute("select distinct rel from edges")}
check(3, "html and pdf docs are in the inventory and graph", any(p.endswith(".html") for p in docs) and any(p.endswith(".pdf") for p in docs))
check(3, "graph has has_project/has_role/has_subject and links_to edges", {"has_project", "has_role", "has_subject", "links_to"} <= rels)
nav = open(os.path.join(ix, "NAVIGATION.md")).read()
check(3, "NAVIGATION.md has project and project/subject headings", "\n## " in nav and " / " in nav)
# eval 1: extract toward root
run("plan_moves.py", ws, "--index", ix)
plan = json.load(open(os.path.join(ix, "moves.plan.json")))
mk = [m for m in plan if m["src"].endswith("marketing-plan.md")]
check(1, "plan moves the marketing doc out of the repo", mk and not mk[0]["dst"].startswith("projects/shop-app/"))
check(1, "plan keeps the technical api doc in the repo", not any(m["src"].endswith("docs/api.md") for m in plan))
bad = os.path.join(ix, "bad.plan.json")
json.dump([{"src": "company/strategy.md", "dst": "projects/shop-app/docs/strategy.md"},
           {"src": "company/strategy.md", "dst": "company/x/y/strategy.md"}], open(bad, "w"))
r = run("move.py", ws, "--plan", bad, "--index", ix, "--apply", "--trash", tr)
check(1, "move refuses a move into the repo / deeper", r.stdout.count("REFUSE") == 2 and os.path.exists(os.path.join(ws, "company/strategy.md")))
run("move.py", ws, "--plan", os.path.join(ix, "moves.plan.json"), "--index", ix, "--apply", "--trash", tr)
st = subprocess.run(["git", "-C", os.path.join(ws, "projects/shop-app"), "status", "--short"], capture_output=True, text=True).stdout
in_trash = any(f == "marketing-plan.md" for _, _, fs in os.walk(tr) for f in fs)
check(1, "source is in the Trash and staged as deleted in git", in_trash and st.startswith("D "))
run("relink.py", ws, "--index", ix, "--apply")
dst = os.path.join(ws, mk[0]["dst"]) if mk else ""
import re
links = re.findall(r"\]\(([^)]+)\)", open(dst).read()) if dst and os.path.exists(dst) else []
check(1, "relative link in the moved doc still resolves", links and all(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(dst), l))) for l in links))
p = sum(ok for *_, ok in res)
print(f"\npass rate: {p}/{len(res)} ({100 * p // len(res)}%)  workdir: {W}")
sys.exit(0 if p == len(res) else 1)
