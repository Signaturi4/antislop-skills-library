#!/usr/bin/env python3
"""Batched tagging + key insight per doc with a cheap Claude model, using defrost sections as compact digests.

Usage:
  tag_batch.py ROOT --index DIR --estimate            token count and cost, no model calls
  tag_batch.py ROOT --index DIR [--batch 25] [--workers 4] [--limit N] [--max-new 15]

Why it is cheap: the model never sees whole files. Each doc becomes a digest of at most --digest-chars
(title, heading path and first words of each section). Sections come from defrost memories
(~/.kev-memory/*/knowledge.sqlite, matched by file sha256 so moved files still match); docs defrost has not
indexed get the same digest built from their own headings (md), h1-h3 (html) or first page (pdf).
Many docs go into one call (--batch), calls run in parallel (--workers), the tag pool is sent once per call.

Output: DIR/tags.jsonl, one line per doc: {"path", "mtime", "tags": {facet: [[tag, score], ...]}, "insight", "src"}
(resumable: docs with the same mtime are skipped). New tags are added to DIR/tag_pool.json only when nothing fits,
after a near-duplicate check, at most --max-new per run. Files are never modified; secret files never read.
Backend: `claude -p` (already-authenticated CLI, no key handled here), CHEAP_MODEL default claude-haiku-5-5.
"""
import argparse, concurrent.futures as cf, difflib, glob, hashlib, html, json, os, re, sqlite3, subprocess, sys, threading, time

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("--index", required=True)
ap.add_argument("--batch", type=int, default=25); ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--digest-chars", type=int, default=700); ap.add_argument("--limit", type=int)
ap.add_argument("--max-new", type=int, default=15); ap.add_argument("--only")
ap.add_argument("--estimate", action="store_true")
ap.add_argument("--price-in", type=float, default=0.10, help="USD per million input tokens")
ap.add_argument("--price-out", type=float, default=0.50, help="USD per million output tokens")
ap.add_argument("--memories", default=os.path.expanduser("~/.kev-memory"))
a = ap.parse_args()

ROOT = os.path.abspath(a.root); FACETS = ("project", "role", "subject")
POOL_P = os.path.join(a.index, "tag_pool.json"); OUT = os.path.join(a.index, "tags.jsonl")
MODEL = os.environ.get("CHEAP_MODEL", "claude-haiku-5-5")
FALLBACK = {"project": "general", "role": "anyone", "subject": "docs-meta"}
pool = json.load(open(POOL_P))
for f in FACETS:  # accept {"tag": "desc"} as well as {"tag": {"desc": ...}}
    pool[f] = {k: (v if isinstance(v, dict) else {"desc": v}) for k, v in pool[f].items()}
lock = threading.Lock()

# defrost: sha256 -> list of (heading_path, text)
SECT = {}
for db in glob.glob(os.path.join(a.memories, "*", "knowledge.sqlite")):
    if ".previous" in db:
        continue
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = c.execute("select d.sha256, s.heading_path, s.text from sections s join docs d on d.id = s.doc_id "
                         "order by d.sha256, s.ordinal").fetchall()
        for sha, hp, txt in rows:
            SECT.setdefault(sha, []).append((hp or "", txt or ""))
    except sqlite3.Error:
        pass


def clip(s, n):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def digest(path):
    """(digest text, source) - defrost sections when indexed, else headings from the file itself."""
    raw = open(path, "rb").read()
    secs = SECT.get(hashlib.sha256(raw).hexdigest())
    n = a.digest_chars
    if secs:
        parts = [f"{hp}: {clip(t, 120)}" for hp, t in secs[:10]]
        return clip(" | ".join(parts), n), "defrost"
    if path.lower().endswith(".pdf"):
        t = subprocess.run(["pdftotext", "-l", "2", "-q", path, "-"], capture_output=True, text=True, timeout=30).stdout
        return clip(t, n), "pdf"
    t = raw[:300_000].decode("utf-8", "ignore")
    if path.lower().endswith(".html"):
        title = re.findall(r"(?is)<title>(.*?)</title>", t)[:1]
        heads = re.findall(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", t)[:10]
        body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", t)
        out = " | ".join(html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in title + heads)
        return clip(out + " || " + html.unescape(body), n), "html"
    heads = [l.strip("# ").strip() for l in t.splitlines() if l.startswith("#")][:12]
    first = next((p for p in re.split(r"\n\s*\n", t) if p.strip() and not p.lstrip().startswith(("#", "---"))), "")
    return clip(" | ".join(heads) + " || " + first, n), "md"


def system_prompt():
    tags = {f: {k: v["desc"] for k, v in pool[f].items()} for f in FACETS}
    return ("You tag documents for a navigation index. For EACH document return one JSON object per line (JSONL, no "
            "prose, no code fence): {\"i\": <doc number>, \"project\": [..], \"role\": [..], \"subject\": [..], "
            "\"insight\": \"<one sentence: the key finding or what the doc is useful for, max 30 words>\"}. "
            "Pick 1 to 3 tags per facet from the allowed list, best first. Prefer a specific subject with a slash "
            "(e.g. research/personas) when it fits. Only if NOTHING fits a facet, put ONE new tag as "
            "\"new:<kebab-name>=<short description>\" in that facet's list; it must be reusable for other docs. "
            "The file path is a strong hint for project.\nAllowed tags: " + json.dumps(tags))


def call(batch):
    """batch: list of (i, rel, digest). Returns (list of parsed dicts, usage dict)."""
    user = "\n".join(f"[{i}] path: {rel}\n{dg}" for i, rel, dg in batch)
    cmd = ["claude", "-p", "--model", MODEL, "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--disable-slash-commands", "--no-session-persistence", "--output-format", "json",
           "--system-prompt", system_prompt()]
    r = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=300)
    j = json.loads(r.stdout)
    rows = []
    for line in j.get("result", "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows, {"cost": j.get("total_cost_usd", 0), "usage": j.get("usage", {})}


new_count = 0


def resolve(facet, tags, rel):
    """Keep allowed tags; turn one new:<name>=<desc> into a pool tag (near-duplicate reuse, capped)."""
    global new_count
    out = []
    for t in tags[:3]:
        t = str(t).strip()
        if t.startswith("new:"):
            name, _, desc = t[4:].partition("=")
            name = re.sub(r"[^a-z0-9/]+", "-", name.lower()).strip("-")
            with lock:
                near = difflib.get_close_matches(name, list(pool[facet]), n=1, cutoff=0.8)
                if near:
                    t = near[0]
                elif name and new_count < a.max_new:
                    pool[facet][name] = {"desc": desc.strip() or name, "added": time.strftime("%F"), "reason": f"none fit {rel}"}
                    json.dump(pool, open(POOL_P, "w"), indent=1); new_count += 1; t = name
                    print(f"NEW {facet}:{name}", flush=True)
                else:
                    continue
        if t in pool[facet] and t not in [x for x, _ in out]:
            out.append((t, round(1.0 - 0.25 * len(out), 2)))
    return out or [(FALLBACK[facet], 0.0)]


done = {}
if os.path.exists(OUT):
    for line in open(OUT):
        d = json.loads(line); done[d["path"]] = d["mtime"]
todo = [d for d in map(json.loads, open(os.path.join(a.index, "inventory.jsonl")))
        if done.get(d["path"]) != d["mtime"] and (not a.only or a.only in d["path"])][: a.limit]

items, src_count = [], {}
for d in todo:
    try:
        dg, src = digest(os.path.join(ROOT, d["path"]))
    except Exception as e:  # noqa: BLE001
        dg, src = f"(unreadable: {type(e).__name__})", "none"
    src_count[src] = src_count.get(src, 0) + 1
    items.append((d, dg, src))
batches = [items[i:i + a.batch] for i in range(0, len(items), a.batch)]

if a.estimate:
    sys_tok = len(system_prompt()) / 4
    doc_tok = sum(len(dg) + len(d["path"]) + 15 for d, dg, _ in items) / 4
    tin = sys_tok * len(batches) + doc_tok
    tout = 70 * len(items)
    cost = tin / 1e6 * a.price_in + tout / 1e6 * a.price_out
    print(f"docs {len(items)} in {len(batches)} calls (batch {a.batch}); digest sources {src_count}")
    print(f"input ~{tin / 1e6:.2f} M tokens (pool {sys_tok:.0f} tok/call), output ~{tout / 1e6:.2f} M tokens")
    print(f"estimated cost ~${cost:.2f} at ${a.price_in}/M in, ${a.price_out}/M out (CLI overhead per call not included)")
    sys.exit(0)

spent, n, fails, t0 = 0.0, 0, 0, time.time()
out_f = open(OUT, "a")


def run(batch):
    rows, info = call([(k, d["path"], dg) for k, (d, dg, _) in enumerate(batch)])
    by_i = {r.get("i"): r for r in rows if isinstance(r, dict)}
    recs = []
    for k, (d, dg, src) in enumerate(batch):
        r = by_i.get(k)
        if not r:
            continue  # left untagged: picked up by the next run
        recs.append({"path": d["path"], "mtime": d["mtime"], "src": src, "insight": str(r.get("insight", ""))[:300],
                     "tags": {f: resolve(f, r.get(f) or [], d["path"]) for f in FACETS}})
    return recs, info


with cf.ThreadPoolExecutor(a.workers) as ex:
    for fut in cf.as_completed([ex.submit(run, b) for b in batches]):
        try:
            recs, info = fut.result()
        except Exception as e:  # noqa: BLE001
            fails += 1; print(f"FAIL batch: {type(e).__name__}: {str(e)[:150]}", file=sys.stderr)
            if fails >= 5:
                ex.shutdown(cancel_futures=True); sys.exit("5 failed batches: check `claude -p` auth/model")
            continue
        fails = 0; spent += info["cost"] or 0
        with lock:
            for rec in recs:
                out_f.write(json.dumps(rec) + "\n")
            out_f.flush(); n += len(recs)
        print(f"{n}/{len(items)} docs, ${spent:.3f}, {time.time() - t0:.0f}s", flush=True)
print(f"tagged {n} of {len(items)} docs, cost ${spent:.3f}, new tags {new_count}; digest sources {src_count}")
for f in FACETS:
    if len(pool[f]) > 25:
        print(f"WARN {f} has {len(pool[f])} tags: review and merge near-duplicates in {POOL_P}")
