#!/usr/bin/env python3
"""Tag every doc in DIR/inventory.jsonl with 1-3 tags per facet (project, role, subject) from DIR/tag_pool.json.

Usage: tag_docs.py ROOT --index DIR [--backend kev|claude|keyword] [--threshold 0.25] [--floor 0.2]
                   [--max-new 10] [--limit N] [--only SUBSTR] [--no-grow]
Backends:
  kev      local System-One API (KEV_API, default http://localhost:8009); `choice` questions give probabilities.
  claude   cheap model through the `claude -p` CLI (CHEAP_MODEL, default claude-haiku-5-5); returns JSON scores.
  keyword  zero-cost token-overlap scorer: offline fallback and test fixture backend.
Picking: per facet keep tags with p >= threshold, best first, max 3, min 1 (the top one).
Growing the allow-list: when `none-fits` wins or the top p < floor, the proposer (CHEAP_MODEL via `claude -p`, or a
slug of the folder name with --backend keyword) suggests ONE kebab-case tag; near-duplicates (similar name) reuse the
existing tag. New tags are appended to tag_pool.json with `added` and `reason`, and the doc is asked again.
Output: DIR/tags.jsonl, resumable (a doc with the same mtime is skipped). Docs themselves are never modified.
Stops after 5 consecutive backend failures (server down, model still loading: Kev needs ~3 min to load).
"""
import argparse, difflib, html, json, os, re, subprocess, sys, time, urllib.request

FACETS = ("project", "role", "subject")
FALLBACK = {"project": "general", "role": "anyone", "subject": "docs-meta"}
NONE = "none-fits"
ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("--index", required=True)
ap.add_argument("--backend", default="kev", choices=["kev", "claude", "keyword"])
ap.add_argument("--threshold", type=float, default=0.25); ap.add_argument("--floor", type=float, default=0.2)
ap.add_argument("--max-new", type=int, default=10); ap.add_argument("--limit", type=int)
ap.add_argument("--only"); ap.add_argument("--no-grow", action="store_true")
a = ap.parse_args()
ROOT = os.path.abspath(a.root)
POOL_P = os.path.join(a.index, "tag_pool.json"); OUT = os.path.join(a.index, "tags.jsonl")
pool = json.load(open(POOL_P))
CHEAP = os.environ.get("CHEAP_MODEL", "claude-haiku-5-5")
TOK = re.compile(r"[a-z0-9]+")


def text_of(p, n=1800):
    try:
        if p.lower().endswith(".pdf"):
            t = subprocess.run(["pdftotext", "-l", "3", "-q", p, "-"], capture_output=True, text=True, timeout=30).stdout
        else:
            t = open(p, errors="ignore").read(200_000)
            if p.lower().endswith((".html", ".htm")):
                t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
                t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    except Exception as e:  # noqa: BLE001
        t = f"(unreadable: {type(e).__name__})"
    return re.sub(r"\s+", " ", t).strip()[:n]


def options(facet):
    o = {k: v["desc"] for k, v in pool[facet].items()}
    o[NONE] = "none of the other options fits this document"
    return o


def ask_kev(rel, txt):
    q = {f: {"type": "choice", "criteria": options(f), "instructions": {
        "project": "Which project is this document about? The file path is a strong hint.",
        "role": "Who is this document written for or by?",
        "subject": "What subject is it about? Prefer the most specific option (with a slash) that fits."}[f]} for f in FACETS}
    body = {"state": f"File path: {rel}\n\nContent start:\n{txt}", "model": "kev-latest", "questions": q}
    req = urllib.request.Request(os.environ.get("KEV_API", "http://localhost:8009") + "/v1/systemone",
                                 json.dumps(body).encode(), {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        ans = json.load(r)["answers"]
    return {f: ans[f]["probabilities"] for f in FACETS}


def ask_claude(rel, txt):
    prompt = ("Score how well each tag fits the document, 0 to 1. Reply with JSON only: "
              '{"project": {tag: score}, "role": {...}, "subject": {...}}, include only tags scoring >= 0.1.\n'
              f"Tags: {json.dumps({f: options(f) for f in FACETS})}\n\nFile path: {rel}\nContent start:\n{txt}")
    out = subprocess.run(["claude", "-p", "--model", CHEAP, prompt], capture_output=True, text=True, timeout=180).stdout
    return json.loads(out[out.index("{"): out.rindex("}") + 1])


def ask_keyword(rel, txt):
    words = TOK.findall((rel + " " + rel + " " + txt).lower())
    bag = set(words)
    res = {}
    for f in FACETS:
        sc = {}
        for tag, desc in options(f).items():
            if tag == NONE:
                continue
            name = set(TOK.findall(tag)); d = set(TOK.findall(desc.lower())) - {"and", "or", "the", "a", "in", "of"}
            sc[tag] = 0.6 * len(name & bag) / max(len(name), 1) + 0.4 * len(d & bag) / max(len(d), 1)
        tot = sum(sc.values())
        res[f] = {k: v / tot for k, v in sc.items()} if tot else {}
        res[f][NONE] = 0.0 if tot else 1.0
    return res


ASK = {"kev": ask_kev, "claude": ask_claude, "keyword": ask_keyword}[a.backend]


def pick(probs):
    ranked = sorted(((p, t) for t, p in probs.items() if t != NONE), reverse=True)
    if not ranked:
        return []
    keep = [(t, round(p, 3)) for p, t in ranked if p >= a.threshold][:3]
    return keep or [(ranked[0][1], round(ranked[0][0], 3))]


def needs_new(probs):
    top = max(probs, key=probs.get) if probs else NONE
    return top == NONE or probs.get(top, 0) < a.floor


def propose(facet, rel, txt):
    """One new kebab-case tag (name, desc) or None."""
    if a.backend == "keyword":
        if facet != "subject":  # projects come from the survey, roles are a fixed list: keyword never invents them
            return None
        parts = [s for s in rel.split(os.sep)[:-1] if s]
        name = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^\d+[-_ ]*", "", (parts[-1] if parts else "misc").lower())).strip("-")
        return (name, f"proposed from folder of {rel}") if name else None
    prompt = (f"Existing {facet} tags: {json.dumps(options(facet))}. None fits this document. Propose ONE new {facet} tag: "
              'kebab-case, broad enough to reuse for other docs. Reply JSON only: {"name": "...", "desc": "..."}.\n'
              f"File path: {rel}\nContent start:\n{txt[:1200]}")
    try:
        out = subprocess.run(["claude", "-p", "--model", CHEAP, prompt], capture_output=True, text=True, timeout=120).stdout
        j = json.loads(out[out.index("{"): out.rindex("}") + 1])
        name = re.sub(r"[^a-z0-9/]+", "-", j["name"].lower()).strip("-")
        return (name, j.get("desc", "")) if name else None
    except Exception:  # noqa: BLE001
        return None


def add_tag(facet, name, desc, rel):
    near = difflib.get_close_matches(name, list(pool[facet]), n=1, cutoff=0.8)
    if near:
        return near[0], False
    pool[facet][name] = {"desc": desc, "added": time.strftime("%F"), "reason": f"none fit {rel}"}
    json.dump(pool, open(POOL_P, "w"), indent=1)
    return name, True


done = {}
if os.path.exists(OUT):
    for line in open(OUT):
        d = json.loads(line); done[d["path"]] = d["mtime"]
inv = [json.loads(l) for l in open(os.path.join(a.index, "inventory.jsonl"))]
n = fails = new = 0; t0 = time.time(); added = []
with open(OUT, "a") as out:
    for d in inv:
        rel = d["path"]
        if (a.only and a.only not in rel) or done.get(rel) == d["mtime"]:
            continue
        p = os.path.join(ROOT, rel); txt = text_of(p)
        try:
            probs = ASK(rel, txt)
            for f in FACETS:
                if not a.no_grow and new < a.max_new and needs_new(probs.get(f, {})):
                    prop = propose(f, rel, txt)
                    if prop:
                        name, is_new = add_tag(f, prop[0], prop[1], rel)
                        if is_new:
                            new += 1; added.append(f"{f}:{name}")
                        probs = ASK(rel, txt)
                        if needs_new(probs.get(f, {})):  # the model still prefers none-fits: use the proposal
                            probs[f] = {**probs.get(f, {}), name: max([a.threshold] + list(probs.get(f, {}).values()))}
        except Exception as e:  # noqa: BLE001
            fails += 1; print(f"FAIL {rel}: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
            if fails >= 5:
                sys.exit("5 failures in a row: is the backend up? (Kev needs ~3 min to load)")
            continue
        fails = 0
        tags = {f: pick(probs.get(f, {})) for f in FACETS}
        for f in FACETS:  # min 1 tag per facet: fall back to the generic tag when nothing scored
            if not tags[f] and FALLBACK[f] in pool[f]:
                tags[f] = [(FALLBACK[f], 0.0)]
        rec = {"path": rel, "mtime": d["mtime"], "tags": tags}
        out.write(json.dumps(rec) + "\n"); out.flush(); n += 1
        if n % 50 == 0:
            print(f"{n} docs, {time.time() - t0:.0f}s", flush=True)
        if a.limit and n >= a.limit:
            break
print(f"tagged {n} docs in {time.time() - t0:.0f}s; new tags: {', '.join(added) or 'none'}")
for f in FACETS:
    if len(pool[f]) > 25:
        print(f"WARN {f} has {len(pool[f])} tags: review and merge near-duplicates in {POOL_P}")
