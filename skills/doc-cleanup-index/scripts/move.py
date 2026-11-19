#!/usr/bin/env python3
"""Execute an approved move plan safely: copy -> verify -> source to Trash; git mv inside one repo.

Usage: move.py ROOT --plan moves.plan.json --index DIR [--apply] [--trash DIR] [--allow-down]
Dry run by default (prints what it would do). Per move:
- Guard: refuses moves into a git repo the source is not in, and moves deeper than the source (docs go toward the
  root; --allow-down only for an explicit owner decision).
- Same repo, tracked file: `git mv` (history kept). Otherwise copy, byte-compare (symlinks compared by target, so a
  broken absolute symlink does not crash the check), then move the source to the Trash (never a permanent delete).
  A source tracked in a repo is then removed from the index with `git rm --cached` (commit on a branch, open a PR).
- Before touching a repo it warns about unpushed commits, stashes and uncommitted changes.
Appends to DIR/moves.json (root-relative old -> new file paths) for relink.py, and to DIR/moves.log.
"""
import argparse, filecmp, json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import repo_of, trash_dir  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--plan", required=True)
ap.add_argument("--index", required=True); ap.add_argument("--apply", action="store_true")
ap.add_argument("--trash"); ap.add_argument("--allow-down", action="store_true")
a = ap.parse_args(); ROOT = os.path.abspath(a.root)
TRASH = os.path.join(a.trash or trash_dir(), f"doc-cleanup-{time.strftime('%F')}")
mp = os.path.join(a.index, "moves.json"); moves = json.load(open(mp)) if os.path.exists(mp) else {}
logf = open(os.path.join(a.index, "moves.log"), "a")
checked = set()


def log(m):
    print(m); logf.write(m + "\n")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def repo_check(repo):
    if repo in checked:
        return
    checked.add(repo)
    for what, args in (("unpushed commits", ["log", "--branches", "--not", "--remotes", "--oneline"]),
                       ("stashes", ["stash", "list"]), ("uncommitted changes", ["status", "--short"])):
        out = git(repo, *args).stdout.strip()
        if out:
            log(f"WARN {os.path.relpath(repo, ROOT)} has {what} ({len(out.splitlines())} lines)")


def same(x, y):
    if os.path.islink(x) or os.path.islink(y):
        return os.path.islink(x) and os.path.islink(y) and os.readlink(x) == os.readlink(y)
    if os.path.isdir(x):
        fx = sorted(os.path.relpath(os.path.join(r, f), x) for r, _, fs in os.walk(x) for f in fs)
        fy = sorted(os.path.relpath(os.path.join(r, f), y) for r, _, fs in os.walk(y) for f in fs)
        return fx == fy and all(same(os.path.join(x, f), os.path.join(y, f)) for f in fx)
    return filecmp.cmp(x, y, shallow=False)


for m in json.load(open(a.plan)):
    s, d = os.path.join(ROOT, m["src"]), os.path.join(ROOT, m["dst"])
    if not os.path.lexists(s):
        log(f"SKIP missing {m['src']}"); continue
    if os.path.exists(d):
        log(f"SKIP target exists {m['dst']}"); continue
    rs, rd = repo_of(s, ROOT), repo_of(d, ROOT)  # works for paths that do not exist yet
    if rd and rd != rs:
        log(f"REFUSE {m['src']} -> {m['dst']}: target is inside a repo the source is not in (docs move toward the root)"); continue
    if m["dst"].count(os.sep) > m["src"].count(os.sep) and not a.allow_down:
        log(f"REFUSE {m['src']} -> {m['dst']}: deeper than the source (docs move toward the root)"); continue
    tracked = rs and git(rs, "ls-files", "--error-unmatch", os.path.relpath(s, rs)).returncode == 0
    how = "git mv" if tracked and rs == rd else "copy-verify-trash" + (" + git rm --cached" if tracked else "")
    if not a.apply:
        print(f"WOULD {how}: {m['src']} -> {m['dst']}"); continue
    if rs:
        repo_check(rs)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    if how == "git mv":
        r = git(rs, "mv", os.path.relpath(s, rs), os.path.relpath(d, rs))
        if r.returncode:
            log(f"FAIL git mv {m['src']}: {r.stderr.strip()}"); continue
    else:
        if os.path.isdir(s):
            subprocess.run(["rsync", "-a", s + "/", d + "/"], check=True)
        else:
            shutil.copy2(s, d, follow_symlinks=False)
        if not same(s, d):
            log(f"DIFF {m['src']} -> {m['dst']}: copy kept, source NOT removed"); continue
        t = os.path.join(TRASH, m["src"]); os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.move(s, t)
        if tracked:
            git(rs, "rm", "-r", "-q", "--cached", os.path.relpath(s, rs))
    moves[m["src"]] = m["dst"]
    log(f"OK {how}: {m['src']} -> {m['dst']}")
json.dump(moves, open(mp, "w"), indent=1)
print(f"{'applied' if a.apply else 'dry run'}; move map: {mp}")
