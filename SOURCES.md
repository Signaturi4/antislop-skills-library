# Sources

Where each skill in this library comes from.

## Written for this library (`skills/`)

| Skill | Origin | Licence |
|---|---|---|
| `project-foundation` | this repository | MIT |
| `extraction-ready-docs` | this repository | MIT |
| `doc-cleanup-index` | this repository | MIT |
| `overview-brief` | this repository | MIT |
| `skill-gate` | this repository | MIT |

## Collected from other authors (`third-party/`)

Copied unchanged. Each folder keeps the author's licence text. Credit and thanks go to the authors; for the latest version use the source.

| Skill | What it removes | Author | Source | Licence |
|---|---|---|---|---|
| `unslop` | AI-looking user interfaces: spacing, colour, icons, copy, type, layout | Damir Sokolovsky | https://heydamir.design/unslop | CC-BY-4.0 (`LICENSE.txt`) |
| `narrative-deslop` | AI habits in stories and scripts (written in Russian, English triggers) | imuha54-cmd | https://github.com/imuha54-cmd/narrative-deslop | MIT (`LICENSE`) |
| `install-anti-slop` | sloppy TypeScript and JavaScript, through an Oxlint plugin | Dillon Mulroy | https://github.com/dmmulroy/anti-slop | MIT (`LICENSE.upstream.txt`) |
| `verification-before-completion` | "done" claims with no proof: run the check, then report | Jesse Vincent | https://github.com/obra/superpowers | MIT (`LICENSE.upstream.txt`) |
| `grill-me` | vague plans: the agent questions you until the plan is clear | Matt Pocock | https://github.com/mattpocock/skills | MIT (`LICENSE.upstream.txt`) |
| `the-fool` | untested ideas: devil's advocate, pre-mortem, red team | Jeffallan | https://github.com/Jeffallan/claude-skills | MIT (`LICENSE.upstream.txt`) |
| `zero-tech-debt` | compatibility cruft and accidental complexity: rework a change as if the intended design existed from day one | Makisuo (earliest public copy found, 2026-05-15; the same text also appears in other repositories) | https://github.com/Makisuo/skills | MIT (`LICENSE.upstream.txt`) |

## Built into Claude Code (not copied here)

| Command | What it does |
|---|---|
| `/simplify` | reviews changed code for reuse, simplification and efficiency, then applies the fixes |
| `/code-review` | reviews a diff or pull request for correctness bugs |

These ship with Claude Code, so there is nothing to install.
