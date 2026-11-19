#!/usr/bin/env python3
"""Check an overview brief page: source lines, claim headlines, ledgered numbers, deny-list terms, dark tokens.

Usage: check_brief.py page.html --ledger ledger.json [--deny deny-list.txt]
Exit 0 and print CLEAN when nothing is flagged; otherwise list the hits and exit 1.
ledger.json: a list of {"value": "59%", "claim": "...", "source": "...", "date": "YYYY-MM-DD"}.
"""
import argparse, html, json, re, sys
from pathlib import Path

NUM = re.compile(r"[$€£]?\d[\d,]*(?:\.\d+)?\s?(?:%|k|K|h|GB)?")


def norm(v: str) -> str:
    v = v.replace(",", "").replace(" ", "").lower().lstrip("$€£")
    return v.rstrip("hgb").rstrip("%k") or v


def visible(fragment: str) -> str:
    fragment = re.sub(r"<(style|script|svg|nav)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r'<div class="eyebrow">.*?</div>', " ", fragment, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--deny")
    a = ap.parse_args()
    page = Path(a.page).read_text()
    ledger = json.loads(Path(a.ledger).read_text())
    allowed = {norm(str(e["value"])) for e in ledger}
    for e in ledger:  # also allow every number that appears inside a ledger value ("$2k-4k")
        allowed |= {norm(m) for m in NUM.findall(str(e["value"]))}
    hits = []
    sections = re.findall(r"<section\b[^>]*?id=\"([^\"]+)\"[^>]*>(.*?)</section>", page, flags=re.S)
    if not sections:
        hits.append("no <section id=...> blocks found")
    for sid, body in sections:
        if 'class="src' not in body and not re.search(r"\bFrom (the |our )?\w", visible(body)):
            hits.append(f"[{sid}] no source line (add a .src line or a 'From <source>' intro)")
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", body, flags=re.S)
        if h2 and len(visible(h2.group(1)).split()) < 3:
            hits.append(f"[{sid}] headline is a label, write the claim as a sentence: {visible(h2.group(1)).strip()!r}")
    text = visible(page)
    for raw in sorted(set(NUM.findall(text))):
        n = norm(raw)
        if re.fullmatch(r"\d", n) or re.fullmatch(r"(19|20)\d\d", n) or n in ("10",):
            continue  # single digits, years, section numbers
        if n not in allowed:
            hits.append(f"number not in ledger: {raw.strip()}")
    if a.deny and Path(a.deny).expanduser().exists():
        for term in Path(a.deny).expanduser().read_text().splitlines():
            term = term.strip()
            if term and not term.startswith("#") and re.search(term, text, flags=re.I):
                hits.append(f"deny-list term on the page: {term}")
    if "prefers-color-scheme" not in page:
        hits.append("no dark-mode token block (@media (prefers-color-scheme: dark))")
    if hits:
        print("\n".join(hits))
        return 1
    print("CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
