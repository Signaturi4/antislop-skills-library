#!/usr/bin/env python3
"""Scan relative links in .md (`](target)`) and .html (`href=`) docs under ROOT; report broken ones.

Usage: link_scan.py ROOT [--out FILE]   (exit 0 always; the count is the result)
External links (scheme:), anchors and absolute paths are skipped. `%20` is decoded.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import walk_docs  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--out")
a = ap.parse_args(); root = os.path.abspath(a.root)
LINK = re.compile(r"\]\(<?([^)\s#>]+)|href=[\"']([^\"'#]+)")
total = 0; broken = []
for p in walk_docs(root):
    if p.lower().endswith(".pdf"):
        continue
    for x, y in LINK.findall(open(p, errors="ignore").read(500_000)):
        t = (x or y).replace("%20", " ")
        if re.match(r"^[a-zA-Z][a-zA-Z+.-]*:|^/|^\{", t):
            continue
        total += 1
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), t))):
            broken.append(f"- {os.path.relpath(p, root)} -> `{t}`")
rep = f"# Broken links\n\n{len(broken)} of {total} relative links are broken.\n\n" + "\n".join(broken) + "\n"
if a.out:
    open(a.out, "w").write(rep)
print(f"{len(broken)} broken of {total} relative links" + (f" -> {a.out}" if a.out else ""))
