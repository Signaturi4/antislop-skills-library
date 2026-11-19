# Antislop Skills Library

Agent skills that keep a project from turning into slop: one home for every fact, decisions written down, clear roles, a tidy folder tree and docs that can be found.

Each skill is a folder with a `SKILL.md` and, where needed, scripts, references and templates. They work with Claude Code and any agent that reads the Agent Skills format.

## Presentation and resources

| File | What it is |
|---|---|
| [**The future of AI is augmented** (PDF)](presentation/the-future-of-ai-is-augmented.pdf) | The talk behind this library: why unread AI output piles up and how a team keeps a person in charge. 20 slides. |
| [**AI learning resources** (PDF)](resources/ai-learning-resources-overview.pdf) | Free courses, lectures and channels for learning AI and the maths behind it. For each one: who it is for, when to use it, what you get. |

## Start here

Run `project-foundation` on a new project first. It asks a few questions and writes the operating rules. The other skills build on what it sets up.

## Skills

| Skill | What it does | Use it when |
|---|---|---|
| [`project-foundation`](skills/project-foundation) | Sets up sources of truth (internal or external), a decision register, roles and decision rights, an owner-inputs log, the folder rule with a checker, and a short rule block in `CLAUDE.md` | starting a project, repo or workspace; two copies of the same fact keep appearing |
| [`extraction-ready-docs`](skills/extraction-ready-docs) | Rules for how doc pages are written and how doc files are named, versioned and moved, with an installer and linters | writing or reorganising docs; docs are hard to search |
| [`doc-cleanup-index`](skills/doc-cleanup-index) | Cleans up a messy tree of docs: inventory, max 7 folders per level, safe moves, tags, navigation index | a workspace has grown without rules |
| [`overview-brief`](skills/overview-brief) | Builds one overview document of a company or project for a reader with no context | onboarding a person, partner or new session |
| [`skill-gate`](skills/skill-gate) | Makes sure a skill named in a prompt is invoked before code is written, and files are read before they are edited | agents skip the skills they were told to use |

## Collected skills

Seven skills by other authors that fight the same problem, copied unchanged into [`third-party/`](third-party) with each author's licence. Author, source and licence for every skill: [SOURCES.md](SOURCES.md).

| Skill | What it removes |
|---|---|
| `unslop` | AI-looking user interfaces |
| `narrative-deslop` | AI habits in stories and scripts |
| `install-anti-slop` | sloppy TypeScript and JavaScript, through a lint plugin |
| `zero-tech-debt` | compatibility cruft and accidental complexity |
| `verification-before-completion` | "done" claims with no proof |
| `grill-me` | vague plans |
| `the-fool` | untested ideas |

## Install

Copy a skill folder into your skills directory:

```sh
git clone https://github.com/Signaturi4/antislop-skills-library.git
cp -R antislop-skills-library/skills/project-foundation ~/.claude/skills/
```

Use `<project>/.claude/skills/` instead to install for one project only. Then ask the agent: "set up this project with project-foundation".

## What `project-foundation` writes

```
<project>/
  CLAUDE.md                      short rule block, replaced on re-run
  INDEX.md                       generated folder index
  .claude/check-structure.py     folder rule checker
  .claude/structure.json         folder descriptions and the limit
  docs/  (or <folder>/governance/)
    sources-of-truth.md          one home per kind of fact, internal or external
    decision-register.md         what was decided, by whom, when, why
    roles.md                     who owns what, whose yes each action needs
    owner-inputs.md              what is waiting for a person
```

Unknown answers become `TBD` rows and open inputs, so set-up can start small and grow.

## Principles

1. One home per fact. Everything else links to it.
2. Say whether a home is inside the project or outside it.
3. Agents record decisions; people make them.
4. Ask before anything that is hard to undo or leaves the project.
5. Short rules in `CLAUDE.md`, full rules in files that are read only when needed.
6. Nothing is permanently deleted without a person's yes.

## License

MIT. See [LICENSE](LICENSE).
