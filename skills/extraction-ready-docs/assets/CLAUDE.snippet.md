## ⚠️ IMPORTANT: documentation rules (read before writing, editing, moving or renaming any doc)

**Before you create or change any documentation file (`*.md`, `*.rst`, `docs/**`, READMEs, ADRs), read
`docs/DOC_RULES.md` (how to write a page) and `docs/KNOWLEDGE_RULES.md` (where files live, names, versions,
sources).** Short version:

1. **One topic per section**, with a heading that names it; 60–400 words per section.
2. **Self-contained:** name the subject in the first sentence; no "it / this / see above" across sections.
3. **Exact names:** backtick every identifier and path exactly as in code; one name per concept (`docs/GLOSSARY.md`).
4. **Plain sentences:** active voice, ≤ 25 words, one fact or step each; options, defaults and limits go in tables.
5. **Facts:** end reference and explanation sections with 3–7 lines: `- Subject → relation → Object (qualifier)`.
   Facts and prose state what the code does today; mark decided-but-unbuilt policy "not built yet" where stated.
6. **One home, clear names:** check `docs/README.md` before creating a file and extend the existing one; name files
   what-who-when in lowercase hyphens with full `YYYY-MM-DD` dates; never make `_v2` / `final` / `.bak` copies;
   never move or rename files unasked.
7. **Lifecycle mode: {{MODE}}** — {{MODE_RULE}}
8. **Sources:** a file with `source: true` lists where each fact came from in `## Sources`; every other file cites
   the source file; never invent a quote, number or reference.
{{CHECK}}
