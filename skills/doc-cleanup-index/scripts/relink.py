#!/usr/bin/env python3
"""Rewrite references after moves, from DIR/moves.json (root-relative old -> new).

Usage: relink.py ROOT --index DIR [--extra-dirs PATH ...] [--apply]
1. Relative links in .md (`](x)`) and .html (`href="x"`) under ROOT: each link is resolved from the file's OLD location
   (so links inside moved files work too) and rewritten to the target's new relative path.
2. Plain-text path references (backticks, scripts, configs: .md .sh .py .json .yaml .yml .toml .txt) under ROOT and
   --extra-dirs (skills, memory, cron scripts): old folder and file paths, root-relative and absolute, are replaced
   by the new ones, longest first. Only strings containing a `/` are replaced, to avoid false hits.
Filenames with spaces are fine (os.walk, no shell splitting). Dry run prints counts; --apply writes.
"""
import argparse, json, os, re, posixpath as pp, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import PRUNE  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--index", required=True)
ap.add_argument("--extra-dirs", nargs="*", default=[]); ap.add_argument("--apply", action="store_true")
a = ap.parse_args(); ROOT = os.path.abspath(a.root)
moves = json.load(open(os.path.join(a.index, "moves.json")))
inv = {v: k for k, v in moves.items()}
pairs = dict(moves)
for o, n in moves.items():  # folder pairs: strip the common path suffix, keep the pair if every move under it agrees
    oc, nc = o.split("/"), n.split("/")
    while len(oc) > 1 and len(nc) > 1 and oc[-1] == nc[-1]:
        oc, nc = oc[:-1], nc[:-1]
    if len(oc) < len(o.split("/")):
        op, np_ = "/".join(oc), "/".join(nc)
        if op != np_ and all(v == np_ + k[len(op):] for k, v in moves.items() if k.startswith(op + "/")):
            pairs.setdefault(op, np_)
plain = sorted(((o, n) for o, n in pairs.items() if "/" in o), key=lambda x: -len(x[0]))
LINK = re.compile(r"(\]\(<?|href=[\"'])([^)\s#\"'>]+)")
TEXT = (".md", ".sh", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".html")


def new_of(old):
    if old in moves:
        return moves[old]
    for o, n in plain:
        if old == o or old.startswith(o + "/"):
            return n + old[len(o):]
    return old


def files(base):
    for r, ds, fs in os.walk(base):
        ds[:] = [d for d in ds if d not in PRUNE and not d.startswith(".")]
        for f in fs:
            if f.endswith(TEXT):
                yield os.path.join(r, f)


links = refs = changed = 0
for base in [ROOT] + [os.path.abspath(os.path.expanduser(x)) for x in a.extra_dirs]:
    for p in files(base):
        try:
            txt = open(p).read()
        except (UnicodeDecodeError, OSError):
            continue
        new = txt
        if p.startswith(ROOT + os.sep) and p.endswith((".md", ".html")):
            rel = os.path.relpath(p, ROOT); old_rel = inv.get(rel, rel)

            def sub(m):
                global links
                t = m.group(2).replace("%20", " ")
                if re.match(r"^[a-zA-Z][a-zA-Z+.-]*:|^/", t):
                    return m.group(0)
                tgt = new_of(pp.normpath(pp.join(pp.dirname(old_rel), t)))
                if not os.path.exists(os.path.join(ROOT, tgt)):
                    return m.group(0)
                r2 = pp.relpath(tgt, pp.dirname(rel) or ".")
                if r2 == t.rstrip("/"):
                    return m.group(0)
                links += 1
                return m.group(1) + (r2.replace(" ", "%20") if "%20" in m.group(2) else r2)
            new = LINK.sub(sub, new)
        for o, n in plain:
            for old_s, new_s in ((os.path.join(ROOT, o), os.path.join(ROOT, n)), (o, n)):
                k = len(re.findall(r"(?<![\w/.-])" + re.escape(old_s) + r"(?![\w-])", new))
                if k:
                    new = re.sub(r"(?<![\w/.-])" + re.escape(old_s) + r"(?![\w-])", new_s.replace("\\", "\\\\"), new); refs += k
        if new != txt:
            changed += 1
            if a.apply:
                open(p, "w").write(new)
print(f"{'rewrote' if a.apply else 'would rewrite'} {links} links and {refs} path references in {changed} files")
