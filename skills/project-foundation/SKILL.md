---
name: project-foundation
description: Set up the operating rules of a project or workspace in one run - a sources-of-truth table (one home per kind of fact, each marked internal or external), a decision register, roles and who decides what, an owner-inputs log, a folder structure with a max-7-per-level checker and generated index, and a short rule block in CLAUDE.md. Asks the key questions when the project does not answer them, writes TBD rows for what is still unknown, and can be extended later. Use it whenever someone starts a new project, repo or workspace, says "set up this project", "project setup guide", "define the source of truth", "where does X live", "who decides what", "roles and responsibilities", "decision log", "organise this folder like the other one", asks to copy the way one project is run to another, or when agents keep finding two versions of the same fact.
---

# project-foundation

A project goes wrong in a predictable way: the same fact lives in three places, nobody wrote down who decided what, and an agent picks the wrong copy. This skill writes down four things so that does not happen, and wires them into `CLAUDE.md` so every session reads them.

| File | Answers |
|---|---|
| `sources-of-truth.md` | Where is the one place this fact is right? Is that place inside the project or outside it? |
| `decision-register.md` | What was decided, by whom, when and why? |
| `roles.md` | Who owns what, and whose yes does each action need? |
| `owner-inputs.md` | What is waiting for a person? |

Optional modules add the folder rule, safe removal, file naming and other working rules. A second group of modules is about people working with agents, see "Working with agents" below.

## Modes

- **Set up**: nothing is in place. Run all steps.
- **Extend**: the files exist. Go to "Extend later".
- **Audit**: the user asks whether a project follows the rules. Read the four files and the tree, list what is missing or contradicts, change nothing until asked.

## Step 1: look before asking

Read what the project already says: `README.md`, `CLAUDE.md`, `AGENTS.md`, the top two folder levels, `.mcp.json`, `CODEOWNERS`, existing ADRs or decision notes. The table in `references/questions.md` lists where each fact usually is. Existing hand-written rules are kept; if they cover the same ground as a module, leave the module off rather than writing the rule twice.

## Step 2: ask the key questions

Use `references/questions.md`. Three short rounds, at most four questions at a time:

1. Must know: what the project is, who decides, who works here, where task status lives.
2. Sources of truth: for each kind of fact, the one home and whether it is internal or external.
3. Modules: show the list with the defaults preselected; the user removes what does not fit.

Skip every question the project already answered. Do not guess and do not block: an unanswered field stays empty and becomes a `TBD` row plus an open row in `owner-inputs.md`.

Record answers in a JSON file shaped like `assets/answers.example.json`. Keep it in a temporary folder, not in the project.

## Step 3: show the plan, then write

```sh
python3 <skill-dir>/scripts/setup.py <project-root> --answers <answers.json> --dry-run
python3 <skill-dir>/scripts/setup.py <project-root> --answers <answers.json>
python3 <project-root>/.claude/check-structure.py --write     # when the structure module is on
```

Show the dry-run list to the user before the real run. The script:

- writes the four files into the governance folder (`docs/` in a repo, `<first folder>/governance/` in a workspace, or `governance_dir` from the answers);
- never overwrites a file that exists;
- puts one marked block at the end of `CLAUDE.md` and replaces that block on a re-run (also in `AGENTS.md` when the project has one);
- creates the top-level folders for a workspace;
- installs `.claude/check-structure.py` and `.claude/structure.json`.

It does not move, rename or delete anything. When the existing tree breaks the folder rule, list the proposed moves and wait for a yes.

## Step 4: check and report

1. Run the structure check and read its output.
2. Read `sources-of-truth.md` once as a stranger: can you tell where task status lives and how to read it?
3. Report, result first: files written, files kept, modules on, number of `TBD` rows, open inputs, and anything in the tree that breaks a rule. Tell the user to commit the files so teammates and later sessions get them.

## Sources of truth: the rules that matter

These go into the file; know them when filling the table.

- **One home per topic.** Every other place links to the home.
- **Internal or external is stated, never implied.** Internal is a file in the project. External is a system outside it. An agent treats them differently: it edits an internal home, and it reads an external home through the tool named in "read via".
- **No mirrors.** A copy of an external home inside the project is a dated snapshot and is never edited.
- **The home wins a conflict.** When the home itself looks wrong, show both versions and ask the person who owns the topic.
- **A row needs an owner.** A home nobody owns goes stale; ask who keeps it right.
- **Credentials have an external home only.** Name the secrets store; never a file in the project.

A good row: `task status | task board | external | <tool and board name> | owner | board connector | git history, chat`.
A bad row: `tasks | Notion and GitHub | both | ...` (two homes means no home; split it into "status" and "code").

## Working with agents: why these modules exist

When two people each hand work to an agent, text piles up that nobody read and the result holds choices nobody made. Four things go missing: an author, recorded decisions, a visible process and a shared understanding. The files above bring back decisions and process. These modules bring back the rest; offer them whenever agents do real work in the project.

| Module | What it restores | What it adds |
|---|---|---|
| `three-lanes` | a person holds every decision | each step is Auto, Propose or Human; the table goes into `roles.md` |
| `real-checkpoints` | a yes that means something | an approval request shows a count, one real example and what looks off |
| `spec-first` | shared understanding | goal, plan, out of scope and open questions, read by a person before building |
| `one-task-one-change` | visible process, traceability | one task is one change request that names its task and decision ids and carries a hand-over note (`handoff-template.md`) |
| `authorship` | an author | one named person per piece of work, and three questions before passing it on |
| `autonomy-levels` | control over how far agents go | a level from 1 to 4 per agent role; level 2 by default, raised by a recorded decision |

Agent roles go into the answers file under `agents` (agent role, the human role it works for, what it does, level, what it stops for). `roles.md` then gets an "Agent roles" table. One session has one agent role, and the human role it works for answers for its output.

A checkpoint is worth having only if the person can catch something at it. "Approve all?" with nothing to look at gets a yes by habit; "3 files change, here is the new error message, no timeout is set" gets read.

## Extend later

The four files are living documents. Edit them directly; do not re-run the script to change them.

| Change | Do this |
|---|---|
| New kind of fact | add a row to `sources-of-truth.md`; `TBD` plus an owner-inputs row when the home is unknown |
| A `TBD` got answered | fill the row, set the owner-inputs row to `done` |
| New decision | add a row to `decision-register.md`; never edit an old row, replace it |
| New agent role, or a higher autonomy level | edit the "Agent roles" table in `roles.md` and record it as a decision |
| New role or a change of who decides | edit `roles.md` and record it as a decision |
| New folder | add it, add its line to `.claude/structure.json`, run the checker with `--write` |
| Turn a module on or off | change `modules` in the answers file and re-run `setup.py`; only the `CLAUDE.md` block changes |

## Works with

- `extraction-ready-docs`: how pages are written and how doc files are named, versioned and moved. Run its installer after this skill when the project has many docs.
- `doc-cleanup-index`: cleans up an existing messy tree to fit the folder rule, with tags and a navigation index.
- `overview-brief`: one overview page of the project for a new reader, built from the files this skill writes.
- `skill-gate`: makes sure a skill named in a prompt is really used.

## Limits

- It writes rules; it does not enforce them, apart from the folder check.
- It does not connect external systems. It records which tool reads them.
- It does not decide for the team. Unknowns stay `TBD`.
