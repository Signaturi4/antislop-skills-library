---
name: doc-cleanup-index
description: Clean up and index all documentation of a workspace or set of repos in one safe, repeatable run - inventory every .md, .html and .pdf, enforce max 7 folders per level, extract non-technical docs out of child folders and repos toward the root (never down into a repo), copy -> verify -> Trash moves with git mv and link/path rewriting, broken-link scan, tag every doc with 1-3 project, 1-3 role and 1-3 subject(/sub-subject) tags in batches with a cheap or local model against a curated allow-list that grows only when nothing fits, then build a SQLite graph (docs and tags as nodes) and a project -> area navigation index. Use it whenever someone says "clean up the docs", "reorganise the folders", "max 7 per level", "pull the docs out of the repos", "scan all the links", "tag every doc", "make a tag pool", "graph DB of my notes", "index to find research / API docs for a new project", or wants a messy docs tree made navigable, even if they do not say "skill".
---

# doc-cleanup-index

Turn a messy tree of docs (workspace folders plus git repos) into a clean, navigable one: a fixed folder rule, docs pulled up to where people look for them, every doc tagged, and an index you can query ("research similar to this", "API docs I can reuse").

tldr: survey -> structure check -> link scan -> tag (cheap model, allow-list) -> graph + navigation -> plan moves (owner approves) -> move -> relink -> re-check -> PR.

## Headline rules (and why)

1. **Docs move toward the root, never down.** Extract docs from child folders and from repositories up into the root's folders; never move a root doc into a repo or deeper. People and agents look for docs from the top; a doc buried in a repo is invisible to anyone not working in that repo, and pushing docs down hides them again. `plan_moves.py` and `move.py` both refuse downward moves and moves into a repo the doc was not in (`--allow-down` exists only for an explicit owner decision).
2. **Docs that only explain code stay next to that code** (READMEs, API references, setup inside a repo). They change with the code; moving them breaks that link. `plan_moves.py` keeps docs whose top subject is technical when they live in a repo.
3. **Max 7 folders per level** at every level outside repos. At 8, split by topic (project, then area of work), never by date or "misc". Each repo gets the same check inside it, separately.
4. **Nothing is permanently deleted.** Copy, verify byte-for-byte, then move the source to the Trash; the owner empties it. Shell `rm -rf` is often refused by permission classifiers anyway.
5. **Plan first.** The owner approves the move plan before anything moves. Big changes go on a branch with a PR; never merge or push to main.
6. **Files are never modified by tagging.** Tags live in a separate index folder.

## Inputs

- `ROOT`: the workspace root. `INDEX_DIR`: where the index lives (default `ROOT/.index`, hidden so it does not count as a folder).
- Backend for tagging: `kev` (local System-One API, `KEV_API`, default `http://localhost:8009`), `claude` (cheap model via `claude -p`, `CHEAP_MODEL`, default `claude-haiku-5-5`) or `keyword` (free, offline, weaker).
- Target folder for project docs inside the root (default `projects`).
Ask only for what the request, the session and CLAUDE.md do not answer.

## Steps

Scripts are in `scripts/` (stdlib Python 3.9+; `pdftotext` from poppler for PDFs; `rsync`; `git`). Run them with `python3 <skill>/scripts/<name>.py`.

1. **Survey.** `survey.py ROOT --index INDEX_DIR`. Lists `.md`, `.html`, `.pdf` (prunes `node_modules`, `.git`, venvs, `dist`, `build`, `raw`, archives, offline site mirrors; never lists `.env`, `*.env`, keys). Seeds `tag_pool.json` from `references/tag_pool.starter.json` plus projects discovered from git repo names and folders under project/client folders. Also look for unpublished work before touching repos: `git log --branches --not --remotes`, `git stash list`, `git status` per repo.
2. **Structure check.** `check_structure.py ROOT [--max 7] [--write --desc desc.json]` fails on any level with more than 7 folders and writes `INDEX.md`. Run it inside each repo too.
3. **Link scan.** `link_scan.py ROOT --out INDEX_DIR/broken-links.md`: relative markdown links and html `href`s, broken ones listed.
4. **Tag.** Default: `tag_batch.py ROOT --index INDEX_DIR --estimate` (token count and cost, no calls), pilot with `--limit 25 --workers 1`, then the full run in the background. It sends compact digests (defrost sections matched by sha256, else headings / first page), 25 docs per `claude -p` call with a cheap model, 4 calls in parallel, and also writes a one-sentence key `insight` per doc. Measured: about $0.004 per 25 docs with Haiku 5.5. A local model is the alternative below: on a Mac with under ~32 GB RAM a 4B Kev swaps and takes minutes per doc, so check `latency_ms` on one request before a full run.
   Local alternative:  Start the model first if local (Kev: `uv run --extra serve python -m kev.serve --run <weights> --port 8009`; it needs about 3 minutes to load; wait for `/v1/models`). Pilot: `tag_docs.py ROOT --index INDEX_DIR --backend kev --limit 15`, read the tags, fix the pool descriptions if tags are off, then run the rest in the background (resumable; same-mtime docs are skipped).
   - Facets: `project` (1-3), `role` (who it is for or by; 1-3), `subject` (1-3, may be `subject/sub-subject`, e.g. `research/personas`). Tags with probability >= `--threshold` (0.25) are kept, best first, max 3, min 1.
   - **Allow-list growth:** each facet also offers `none-fits`. When it wins or the top probability is under `--floor` (0.2), a cheap model proposes ONE kebab-case tag with a description; a near-duplicate of an existing tag reuses that tag instead; a new tag is appended to `tag_pool.json` with `added` and `reason`, and the doc is asked again. `--max-new` (10) caps growth per run. When a facet passes ~25 tags the script warns: review the pool, merge near-duplicates, and re-run with `--only` for affected docs.
   - The script stops after 5 consecutive backend failures (server down or still loading).
   - See `references/tagging.md` for the Kev request shape and how to tune the pool.
5. **Graph and navigation.** `build_graph.py ROOT --index INDEX_DIR` builds `graph.db` (nodes: docs and tags; edges `has_project`, `has_role`, `has_subject` weighted by probability, `links_to`, `shares_tags`) and `NAVIGATION.md` (project -> subject -> docs, roles shown, low-confidence tags marked `?`). For a visual graph, hand `graph.db` or the doc folders to the `graphify` skill. Query examples are in `references/tagging.md`.
6. **Plan moves.** `plan_moves.py ROOT --index INDEX_DIR --target projects` writes `PLAN.md`, `moves.plan.json` and `review.json`; nothing moves. Only business docs move: the top subject maps to one of 7 fixed areas (strategy, sales, marketing, research, design, operations, reference), the detailed subject stays a tag, never a folder. Never moved: working files (SKILL.md and anything in a skill folder, AGENTS.md, CLAUDE.md, README.md, prompts, templates, .claude/.agents/.github), technical docs inside a repo. Unsure project (fallback tag, or the path names a different project than the tag) goes to the review list. The plan warns when a parent would pass 7 folders: group projects (clients / products / internal) or send company-level docs to their own root folder before moving. Why: on a real 3,000-doc run the naive plan proposed 1,897 moves, about 1,000 of them skill files that would have broken the skills; the fixed plan proposed 607.
   **View the graph in the IDE:** `graph_vault.py ROOT --index INDEX_DIR` writes `INDEX_DIR/graph/` (one note per tag linking its docs with insights). Open it with the Foam extension (`foam.foam-vscode`, on Open VSX for VS Code forks; command "Foam: Show Graph") or as an Obsidian vault. Add `foam.files.ignore` in `.vscode/settings.json` for archives, node_modules and raw data so the graph stays readable.
7. **Move.** `move.py ROOT --plan INDEX_DIR/moves.plan.json --index INDEX_DIR` (dry run), then `--apply`. Same repo + tracked: `git mv`. Otherwise copy, byte-compare (symlinks compared by target, so a broken absolute symlink does not crash the check; repoint such links relatively), source to the Trash, and `git rm --cached` when it was tracked. Appends `moves.json`. After moving a whole repo that has worktrees, run `git worktree repair`.
8. **Relink.** `relink.py ROOT --index INDEX_DIR --extra-dirs <skills dir> <memory dir> <scripts dir>` (dry run), then `--apply`. Rewrites relative links (resolved from each file's old location) and plain-text path references (root-relative and absolute). Then grep for the old folder names once: repo-relative mentions inside moved docs and paths in configs outside the scanned dirs (cron or launchd scripts, `~/.claude.json` project keys, memory indexes) need a manual edit in the same run.
9. **Re-check and ship.** Re-run steps 2, 3 and 5. In repos: run `gitleaks protect --staged` before committing moved or imported docs (pasted tokens in old notes are common; redact them in the copy and tell the owner to rotate). Commit on a branch, open a PR, report.

## Report (short, result first)

- Docs found (by type), tags per facet and how many new tags were added (list them), docs with a `?` tag.
- Broken links before and after.
- Moves proposed, applied, refused (with reason), anything left in place and why.
- PR links, where the index lives, open questions for the owner.

## What this skill does not do

- It does not rewrite doc content; for how to write findable pages use the `extraction-ready-docs` skill.
- It does not decide doc/code conflicts or merge PRs.
- Plain-text references in files it was not pointed at are found only by the final grep.
- With `--backend keyword`, tags are rough and new tags are folder-name slugs; use it offline or for tests.
- If ROOT itself is a git repo, every path counts as inside that repo; run per sub-tree instead.
