# Worked examples

Two set-ups taken from real projects and stripped to roles. Use them to see what a filled table looks like, not as a template to copy whole. Each has an answers file in `assets/` that `setup.py` runs as is.

## Example 1: small agency workspace

Answers file: `assets/answers.agency-workspace.json`.

**Situation.** A founder, a developer, a designer and a sales person. One folder on the founder's machine holds documents and several git repos. Agents do much of the work; the founder gives every outward yes.

**Sources of truth**

| Topic | Home | Kind | Read via | Wins over |
|---|---|---|---|---|
| Task status, owner, due date | team task board | external | board connector | git history, chat, daily notes |
| Code and technical docs | git repositories | internal | files, change requests | copies in documents |
| Strategy decisions | decision register | internal | file | chat, agent memory |
| Team and roles | roles file | internal | file | the people page on the board |
| How the agency operates, past work | operations knowledge base | external | search tool, read only, access by role | what an agent remembers |
| Proposals and client messages | freelance marketplace account | external | marketplace connector, read only | local drafts |
| Reusable skills | skills library repository | internal | files | installed copies on a laptop |
| Credentials | secrets store | external | nobody | any file |
| Prices and invoices | TBD | TBD | TBD | TBD |

What to notice:
- Task status is external and code is internal, so every task has two homes that link to each other. This came from a real failure: a daily report built from git alone was out of date.
- The knowledge base answers "how do we" and "why did we" questions. An agent that is denied access tells the owner and does not retry.
- The last row is honest. Nobody had named the home for prices, so it is `TBD` with an open input.

**Roles and decision rights**

| Role | Owns | Does not do |
|---|---|---|
| owner | strategy, architecture, deals, money, client reports | build work that another role owns |
| developer | code, pipelines, tests, technical docs | merge to the release branch, deploy production |
| designer | screens, flows; tests each change on the live test stage | billing, client reports, board admin |
| sales | proposals, first contact | send without the owner's yes |

| Action | Decides | What an agent may do |
|---|---|---|
| Merge to the release branch | owner | open a change request, then stop |
| Spend money | owner | show the cost, then stop |
| Send a proposal or client message | owner | write the draft, then stop |
| Manual step in a tool (billing, access, DNS) | owner | ask; after a yes for that step, do it; stop at passwords and payment confirmation |

**Agent roles**

| Agent role | Works for | Level | Stops for |
|---|---|---|---|
| conductor | owner | 2 | merge, deploy, money, publishing, product choices |
| worker | the role that owns the area | 2 | anything outside its brief |
| mechanical | the role that owns the area | 3 | a step that needs judgment |
| sales drafts | sales | 2 | sending |

**Decision register (extract)**

| Id | Decision | Status | Why | Reopen when |
|---|---|---|---|---|
| D-001 | The board is the home for task status, git for code and docs | decided | a report built from git alone was out of date | board and git disagree more than once a week |
| D-002 | The freelance marketplace is sales channel one | decided | one channel gets all proposal effort until it pays | cost per signed deal above 5% of deal value for a month |
| D-004 | The designer reviews by testing on the live stage; no separate review step | decided | a second review step slowed delivery and found less | a defect reaches production that a code review would have caught |
| D-006 | Boosted listings: how many, what budget | open | the ads budget is not set | n/a |

**Owner inputs (extract)**

| Id | What is needed | Kind | Where |
|---|---|---|---|
| A1 | Pick the proposal to send | decision | sales folder |
| A2 | Add a DNS record for the stage | click | DNS provider |
| A3 | Rotate a leaked server token | click | server provider console |

A morning brief reads the open rows and shows them as "agents waiting on you".

**Modules on:** `structure`, `safe-removal`, `docs-toward-root`, `file-naming`, `task-two-homes`, `confirm-outward`, `skills-per-task`, `three-lanes`, `real-checkpoints`, `authorship`, `autonomy-levels`, `conductor`, `session-naming`, `ci-off-laptop`.

## Example 2: client product with a test stage and production

Answers file: `assets/answers.client-product.json`.

**Situation.** A product built for a client by a project lead, a developer and a designer. The repository is delivered to the client: a push to the release branch publishes it, with internal paths and names removed, and releases production.

**Sources of truth**

| Topic | Home | Kind | Read via | Wins over |
|---|---|---|---|---|
| Agreed scope and task ids | signed scope of work | internal | file | older drafts, chat, the backlog |
| Tasks, findings, open work | issue tracker of the repository | external | code host command line | task lists in plans and docs |
| Business data | the product database | external | the product API, read only | spreadsheets, exports, messages |
| API contract | generated from code | internal | file; regenerate, never hand-edit | hand-written endpoint lists |
| Design: layouts, tokens, components, copy | design file | external | design tool connector | the published design-system page, code styles |
| Decisions and open questions | decision register | internal | file | chat, change-request comments |
| How built code behaves | the code | internal | files | docs that describe it |
| The client's sales system | client CRM | external | nobody (no access yet) | any deal number typed by hand |

What to notice:
- Here task status lives in the issue tracker, not on a board. The `task-two-homes` rule reads the status home from this table, so the same rule fits both examples.
- The design file is the home and the published design-system page is a mirror. The mirror is updated in the same change and never overrules the file. When file, mirror and code disagree, the agent shows all three and the project lead decides.
- "No access yet" is written down. Nothing is built that needs the client's sales system until the decision is reopened.
- A doc that disagrees with the code is reported, not fixed silently: the person decides which side is right.

**Environments**

| Environment | Branch | Data | Who deploys | What an agent may do |
|---|---|---|---|---|
| local | your own branch | seeded sample data | anyone | everything |
| stage | the working branch; a push deploys by itself | synthetic only | a merge into the working branch | deploy, test, read logs |
| production | the release branch; a push also publishes to the client | real | project lead only | read only |

**Roles and decision rights**

| Action | Decides | What an agent may do |
|---|---|---|
| Merge to the release branch | project lead | open a change request into the working branch, then stop |
| Release to production | project lead | prepare the notes and the checklist, then stop |
| Run a paid job (collection, enrichment, model scoring) | project lead | show the cost preview; run only after a yes for that run |
| Change scope | client and project lead | write the open question into the register |
| Remove inherited code | project lead | say what replaced it and ask |

The backlog rule that goes with these roles: every task, finding and open question that needs work is one issue. Its title starts with the task id from the signed scope; its body says what, why, how to accept it and the owner role (technical to developer, design to designer, scope to project lead). A change request says which issue it closes. No personal names or emails in issues, because the client can read them.

**Decision register (extract)**

| Id | Decision | Status | Why | Reopen when |
|---|---|---|---|---|
| D-001 | The signed scope of work is the only scope; the larger draft is superseded | decided | only the signed document is agreed with the client | a new scope is signed |
| D-002 | The product database is the only home for business data | decided | two copies of a list disagreed | never without a new decision |
| D-003 | The design file is the home for design; the published page follows it | decided | replaces an earlier decision that named the published page | the design tool is dropped |
| D-004 | The client's sales system is on hold | decided | no access | the client provides access |
| D-006 | Inherited template code is reference only: not fixed, not tested, not built on | decided | the new system replaces it part by part | a reference part is needed in production |
| D-007 | Score threshold per customer segment | open | raised in review, affects acceptance | n/a |

Rules in `CLAUDE.md` cite these ids ("the sales system is on hold (D-004)"), so a reader can find why a rule exists and when it ends.

**Where documents go.** This team files docs by phase of work (engage, research, design, execute, test) and keeps everything made for one change in one folder for that change, closed when the change ships. That is one team's habit, not a module; write it into `CLAUDE.md` by hand if the project wants it.

**Modules on:** `file-naming`, `confirm-outward`, `stage-and-production`, `spec-first`, `authorship`, `three-lanes`, `real-checkpoints`, `autonomy-levels`, `skills-per-task`, `ci-off-laptop`.
