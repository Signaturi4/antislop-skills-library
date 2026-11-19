# Tagging reference

## Allow-list format (`tag_pool.json`)

```json
{
  "project": {"shop-app": {"desc": "project found at projects/shop-app", "added": "2026-11-06", "reason": "survey"}},
  "role":    {"developer": {"desc": "writes code: frontend, backend, scripts"}},
  "subject": {"research/personas": {"desc": "personas, ICP, customer segments"}}
}
```

- The `desc` is what the model reads: make it concrete (nouns people would find in the doc), not a synonym of the name.
- Sub-subjects use a slash: `research/personas`. The navigation index groups by the top part (`research`).
- `none-fits` is added by the script at ask time; never store it in the pool.
- Keep each facet small: about 10-25 tags. More tags spread probability thin and make every tag weaker.

## Kev (System-One API) request shape

One request per doc, one `choice` question per facet; the answer carries `probabilities` for every option, which is what makes 1-3 tags per facet possible.

```json
{"state": "File path: research/notes/personas.md\n\nContent start:\n...",
 "model": "kev-latest",
 "questions": {"subject": {"type": "choice", "instructions": "What subject is it about?",
                           "criteria": {"research/personas": "personas, ICP...", "none-fits": "none of the other options fits"}}}}
```

Kev models trained for one domain still follow `criteria` descriptions, but run the 15-doc pilot and read the result before the full batch. Put the file path in `state`: folder names are the strongest project signal.

## Tuning

- Too many docs get 3 tags: raise `--threshold` (0.3-0.35).
- Too many new tags: lower `--floor` (e.g. 0.15) or `--max-new`; improve descriptions of the tags that should have matched.
- After editing the pool, re-tag only affected docs: delete their lines from `tags.jsonl` (or run with `--only <path part>` after removing them) and run again.

## Graph queries (`graph.db`)

```sql
-- docs about API reference, best first
select n.path, e.weight from edges e join nodes n on n.id = e.src
where e.dst = 'subject:backend-api/reference' order by e.weight desc;

-- research docs similar to one doc (same project + subject group)
select n.path, e.weight from edges e join nodes n on n.id = e.dst
where e.src = 'doc:research/notes/personas.md' and e.rel = 'shares_tags' order by e.weight desc;

-- tag usage, to spot tags nobody uses or one tag that eats everything
select dst, count(*) from edges where rel like 'has_%' group by dst order by 2 desc;
```
