# Set-up questions

Ask only what the project itself does not answer. Look first, then ask.

## Look first

| Fact | Where to look |
|---|---|
| Name, purpose | `README.md`, `package.json`, `pyproject.toml`, the folder name |
| Kind (repo or workspace) | `.git` at the root means repo; a folder that holds several repos and documents is a workspace |
| Existing rules | `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/` |
| Roles | `CODEOWNERS`, `git shortlog -sn`, a team page |
| External systems | `.mcp.json`, CI config, links in the README (board, CRM, tracker) |
| Decisions already made | ADRs, `docs/decisions*`, dated lines in `CLAUDE.md` |
| Folder layout | the top two levels of the tree |

## Round 1: must know (ask at most four at a time)

1. **What is this project and who is it for?** One sentence. Skip when the README says it.
2. **Who decides?** Name the role that gives the final yes on merge, deploy, money and publishing. One role, or one per action.
3. **Who works here?** Roles, what each owns, what each must not do. People or agents.
4. **Where does task status live?** A board outside the project (which tool), issues in the repo, or a file.

## Round 2: sources of truth

For each topic ask "where is the one place this is right?" and "is that place inside the project or outside it?"

| Topic | Typical internal home | Typical external home |
|---|---|---|
| Task status, owner, due date | `TODO.md`, issues file | task board |
| Code and technical docs | the git repository | none |
| Requirements and scope | a spec or SOW file | the client's document |
| Decisions | `decision-register.md` | none |
| Roles and decision rights | `roles.md` | HR system |
| Customer or user data | none | CRM, product database |
| Money: prices, invoices, budget | a pricing file | accounting tool |
| Brand, design | a design-system folder | design tool file |
| Credentials | never a file in the project | password manager, secrets store |
| Research and evidence | a research folder with dated files | survey or analytics tool |

For every external home also ask: how does an agent read it (connector, export, nobody), and may an agent write to it.

## Round 3: optional rule modules

Offer the list, with the default set preselected; the user removes what does not fit.

| Module | Rule in one line | Default |
|---|---|---|
| `structure` | max 7 folders per level, checker script, generated `INDEX.md` | on |
| `safe-removal` | copy, verify, then Trash; never a permanent delete | on |
| `file-naming` | what-who-when names, full dates, no `_v2` or `final` | on |
| `confirm-outward` | ask before merge, deploy, publish, send, pay, delete | on |
| `privacy` | roles instead of names in anything that leaves the project | on |
| `docs-toward-root` | docs move up to where people look; code docs stay with code | workspace |
| `task-two-homes` | code host for work, board for status, linked both ways | when a board exists |
| `skills-per-task` | use a library skill for major tasks and name it | when a skills library exists |
| `token-budget` | scoped work, narrow reads, one check, short answers | off |
| `conductor` | main session plans and checks, worker agents do the work | off |
| `session-naming` | sessions named `<role> <project>` | off |
| `ci-off-laptop` | heavy jobs run on the build server | off |

## No answer

Do not block on an unanswered question and do not guess. Leave the field empty in the answers file: the script writes `TBD` in the table and adds an open row to `owner-inputs.md`. Tell the user how many rows are open.
