#!/usr/bin/env python3
"""Scaffold the project foundation from an answers file.

Usage:
  python3 setup.py <project-root> --answers answers.json [--dry-run]

What it writes (existing files are never overwritten, except the marked block in CLAUDE.md):
  <governance_dir>/sources-of-truth.md   one home per kind of fact, internal or external
  <governance_dir>/decision-register.md  decisions with id, date, who, why, when to reopen
  <governance_dir>/roles.md              roles, what each owns, who decides what
  <governance_dir>/owner-inputs.md       what agents and people are waiting for
  <governance_dir>/handoff-template.md   hand-over note for each change (module "one-task-one-change")
  CLAUDE.md                              short rule block between markers (replaced on re-run);
                                         lines that only repeat what Claude Code does by itself are left out
  AGENTS.md                              the block with the full wording, only when the file already exists
  .claude/check-structure.py, .claude/structure.json, INDEX.md   (when "structure" is on)
  top-level folders from "folders"       (kind "workspace" only)

Anything missing from the answers becomes a "TBD" row plus an open row in owner-inputs.md,
so the set-up can start with little and be extended later.
Answers format: see assets/answers.example.json. Module texts: see MODULES below.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

BEGIN = "<!-- project-foundation:begin -->"
END = "<!-- project-foundation:end -->"
TBD = "TBD"

# Optional rule modules. Each adds a few lines to the CLAUDE.md block. Keep them short:
# CLAUDE.md loads into every session.
MODULES = {
    "structure": [
        "Max {max} folders in any folder (hidden folders do not count). At {max_plus}, split by topic, never by date or \"misc\".",
        "Nothing new at the root. After adding or moving a folder run `python3 .claude/check-structure.py --write`.",
    ],
    "safe-removal": [
        "Moving: copy, verify the copy, then remove the source. Removal goes to the Trash, never a permanent delete.",
        "Before removing a git clone check for unpushed commits, stashes and uncommitted changes.",
    ],
    "docs-toward-root": [
        "Docs move toward the root, never deeper. Docs that only explain code stay next to that code.",
    ],
    "file-naming": [
        "File names say what, who, when: lowercase words and hyphens, a full `YYYY-MM-DD` date only on one-time documents. No `_v2`, `final` or `copy`.",
    ],
    "task-two-homes": [
        "Every task has two homes: the code host for code and docs, and the home named for \"task status\" in `{gov}/sources-of-truth.md` for status, owner and due date. Link them to each other. On status that home wins.",
    ],
    "confirm-outward": [
        "Ask before anything hard to undo or visible outside the project: merge, deploy, publish, send, pay, delete, change access. A yes covers that one action only.",
    ],
    "privacy": [
        "No personal names, emails, client names or secrets in anything that leaves the project (public repos, issues a client can read, shared documents). Use roles.",
    ],
    "stage-and-production": [
        "Work on the working branch and the test stage, never on the release branch or production. Every change request targets the working branch.",
        "Environments, the data each one holds and who may release are in `{gov}/roles.md`. Real data stays out of the test stage; production is read-only for agents.",
    ],
    "token-budget": [
        "Do exactly what was asked. Read narrowly (search first, then only the lines needed). One check that proves the result. Short answers, result first.",
    ],
    "conductor": [
        "The main session plans, writes briefs and checks reports. Work that needs judgment goes to a worker agent, mechanical work to a cheaper one. Handle everything that is not the owner's decision.",
    ],
    "session-naming": [
        "Name sessions `<role> <project>`: lowercase, 2 to 4 words, one role per session.",
    ],
    "ci-off-laptop": [
        "Heavy or long jobs (full test suites, builds, data jobs) run on the build server, not on a laptop.",
    ],
    "three-lanes": [
        "Every step has one lane. Auto: reversible, low risk, easy to check later; the agent does it and flags what is off. Propose: it leaves the project or is costly to undo; the agent prepares everything and waits for one yes. Human: intent, goals, limits, taste.",
        "When unsure of the lane, use Propose.",
    ],
    "real-checkpoints": [
        "A request for approval shows something worth checking: how much changes (a count), one real example, and what looks off. Never ask for a bare \"approve all?\".",
    ],
    "spec-first": [
        "Before building anything larger than a small fix, write the spec: goal, plan, what is out of scope, open questions. A person reads it before work starts.",
    ],
    "one-task-one-change": [
        "One task is one change request (pull request or equivalent): code, design and docs for that task travel together. It names the task it closes and the decision ids it follows.",
        "Every change request carries a hand-over note from `{gov}/handoff-template.md`: decided, skipped on purpose, still open, checked and not checked. An agent may write it; the author reads and stands behind it. No keys or personal data in it.",
    ],
    "authorship": [
        "Every piece of work has one named author: a person who read it and can explain it without opening the file. Agent output with no such person is a draft, not a result.",
        "Before passing work on, answer three questions: did a person decide this or did the agent; is the decision written down; can the author explain it. A no on any of them means stop and fix that first.",
    ],
    "autonomy-levels": [
        "Agents work at the autonomy level set for their role in `{gov}/roles.md` (1 human-led, 2 agent drafts and a person approves, 3 agent acts inside guardrails, 4 fully autonomous). Level 2 is the default. A higher level is a recorded decision, given per area after the lower level worked.",
    ],
    "skills-per-task": [
        "For any major task check the skills library first and use a fitting skill. Name the skills used in the final report; say so in one line when none fits.",
    ],
}

# What goes into CLAUDE.md when a module only repeats, in part or in full, what Claude Code
# already does without being told (it asks before hard-to-undo or outward actions, commits and
# pushes only when asked, looks before it deletes, does only what was asked, delegates by its
# own rules). AGENTS.md gets the full text from MODULES, because other agents may not.
# An empty list means: nothing project-specific is left, write no line.
CLAUDE_SHORT = {
    "confirm-outward": [],
    "token-budget": [
        "Read narrowly (search first, then only the lines needed). One check that proves the result. Short answers, result first.",
    ],
    "conductor": [
        "Work that needs judgment goes to a worker agent, mechanical work to a cheaper one. The main session writes the briefs and checks every report.",
    ],
}

DEFAULT_MODULES = ["structure", "safe-removal", "file-naming", "confirm-outward", "privacy"]

DEFAULT_DECISION_RIGHTS = ["merge to main", "deploy to production", "spend money", "publish or send outside", "product scope", "grant or change access"]


def cell(value):
    text = str(value).strip() if value not in (None, "") else TBD
    return text.replace("|", "/").replace("\n", " ")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def build(answers, today):
    name = answers.get("name") or TBD
    owner = answers.get("owner_role") or "owner"
    kind = answers.get("kind", "repo")
    folders = answers.get("folders", [])
    gov = answers.get("governance_dir") or ("docs" if kind == "repo" or not folders else f"{folders[0]['name']}/governance")
    limit = int(answers.get("max_folders", 7))
    modules = answers.get("modules", DEFAULT_MODULES)
    unknown = [m for m in modules if m not in MODULES]
    if unknown:
        sys.exit(f"Unknown modules: {', '.join(unknown)}. Known: {', '.join(MODULES)}")

    open_inputs = []  # (what is needed, why)

    # --- sources of truth
    src_rows = []
    for s in answers.get("sources", []):
        row = [s.get("topic"), s.get("home"), s.get("kind"), s.get("location"), s.get("owner"), s.get("read_via"), s.get("wins_over")]
        if s.get("kind") not in ("internal", "external"):
            row[2] = TBD
        if any(cell(v) == TBD for v in row[:5]):
            open_inputs.append((f"Complete the source-of-truth row for \"{cell(s.get('topic'))}\"", "agents cannot tell which place wins"))
        src_rows.append(row)
    if not src_rows:
        for topic in ("task status", "code and technical docs", "decisions", "requirements and scope", "people and roles", "money (prices, invoices, budget)"):
            src_rows.append([topic, TBD, TBD, TBD, TBD, TBD, TBD])
        open_inputs.append(("Name the home for each kind of fact in sources-of-truth.md", "no source of truth is defined yet"))

    sources_md = f"""# Sources of truth: {name}

Each kind of fact has **one home**. Every other place links to the home and never keeps its own copy.

## Rules

1. **One home per topic.** Find the topic in the table before you write a fact down. If it has a home, write it there.
2. **Internal or external.** Internal means a file in this project. External means a system outside it (a task board, a CRM, an accounting tool, a client's system). The table says which.
3. **External homes are read, not copied by hand.** Read them through the tool in "read via". A copy inside the project is either a snapshot with the date in its file name, never edited, or a mirror: a mirror says which home it follows, never overrules it, and is updated in the same change as the home.
4. **The home wins.** When two places disagree, the home is right. When the home itself looks wrong, show both versions to the {owner} and ask; do not pick a side.
5. **No home yet.** Add a row with `{TBD}`, add a line to `owner-inputs.md`, and ask. Do not invent a home.
6. **Generated files are not homes.** Indexes and reports name the command that makes them and are never edited by hand.
7. **Cite the home.** Every claim about users, numbers, money or decisions says where it came from. With no source, write "no source yet".
8. **No access means no check.** When the tool that reads a home is not connected, say so. Never state that something matches a home you did not read.

## Table

{table(["Topic", "Home", "Kind", "Where", "Owner", "Read via", "Wins over"], src_rows)}

- **Kind**: `internal` or `external`.
- **Read via**: a path, a command, or the connector an agent uses.
- **Wins over**: the places that hold the same fact and lose in a conflict.

## Generated files

{table(["File", "Made by", "How often"], [["INDEX.md", "`python3 .claude/check-structure.py --write`", "after a folder is added or moved"]] if "structure" in modules else [[TBD, TBD, TBD]])}
"""

    # --- decisions
    dec_rows = []
    for i, d in enumerate(answers.get("decisions", []), 1):
        dec_rows.append([d.get("id") or f"D-{i:03d}", d.get("date") or today, d.get("decision"), d.get("status") or "decided", d.get("decided_by") or owner, d.get("why"), d.get("reopen_when") or "not set", d.get("review") or "none", d.get("replaces") or "none"])
    for row in dec_rows:
        if str(row[3]).strip() == "open":
            open_inputs.append((f"Decide {row[0]}: {cell(row[2])}", "an open decision in the register"))
    if not dec_rows:
        dec_rows.append(["D-001", today, "Project foundation set up: sources of truth, roles, decision register", "decided", owner, "one place to look for how the project runs", "the files stop being read or kept current", "none", "none"])

    decisions_md = f"""# Decision register: {name}

The home for decisions. A decision that is not here does not bind anyone.

## Rules

1. One row per decision. Newest at the bottom. Ids never change and are never reused.
2. Write down who decided and why. "Why" is what lets someone judge later whether the decision still holds.
3. Agents record decisions; they do not make them. Who may decide what is in `roles.md`.
4. A decision is not edited after the fact. To change it, add a new row and set the old one to `replaced by D-...`.
5. A rule in `CLAUDE.md` or in a skill that comes from a decision names its id.
6. Status is one of `decided` (in force), `open` (waiting for the person who decides), `killed` (stopped, reason kept) or `replaced by D-...`. A row with status `open` also gets a row in `owner-inputs.md`, so the person sees it.
7. "Reopen when" names the event or number that puts the decision back on the table. A decision with a review date is read again on that date.

## Register

{table(["Id", "Date", "Decision", "Status", "Decided by", "Why", "Reopen when", "Review", "Replaces"], dec_rows)}
"""

    # --- roles
    role_rows = []
    for r in answers.get("roles", []):
        role_rows.append([r.get("role"), r.get("who"), r.get("owns"), r.get("decides"), r.get("does_not")])
    if not role_rows:
        role_rows.append([owner, TBD, "direction, priorities, final decisions", "everything not given to another role", TBD])
        open_inputs.append(("List the roles in roles.md: who owns what", "work cannot be routed without roles"))
    rights = answers.get("decision_rights") or [{"action": a, "decides": owner} for a in DEFAULT_DECISION_RIGHTS]
    right_rows = [[x.get("action"), x.get("decides"), x.get("consulted") or "none", x.get("agent_may") or "prepare and propose, then stop"] for x in rights]

    agent_rows = [[a.get("agent"), a.get("works_for"), a.get("does"), a.get("level") or 2, a.get("stops_for")] for a in answers.get("agents", [])]
    agents_md = ""
    if agent_rows:
        agents_md = f"""## Agent roles

One agent session has one role. Each agent role works for a human role, which answers for its output.

{table(["Agent role", "Works for", "Does", "Autonomy level", "Stops for"], agent_rows)}

Autonomy levels: 1 human-led; 2 the agent drafts and prepares, a person approves; 3 the agent acts inside guardrails, a person can override; 4 fully autonomous. Raising a level is a decision for the register.

"""

    env_rows = [[e.get("name"), e.get("purpose"), e.get("branch"), e.get("data"), e.get("deploys"), e.get("agent_may")] for e in answers.get("environments", [])]
    envs_md = ""
    if env_rows:
        envs_md = f"""## Environments

{table(["Environment", "Used for", "Branch", "Data", "Who deploys", "What an agent may do"], env_rows)}

"""
    elif "stage-and-production" in modules:
        open_inputs.append(("List the environments in roles.md: branch, data and who deploys each", "the stage-and-production rule points at a table that is empty"))

    roles_md = f"""# Roles and responsibilities: {name}

The home for who does what and who decides what.

## Roles

{table(["Role", "Who", "Owns", "Decides", "Does not do"], role_rows)}

One role can be one person, several people, or an agent. Use the role name, not a person's name, in anything that leaves the project.

## Who decides what

{table(["Action", "Decides", "Consulted", "What an agent may do"], right_rows)}

## Three lanes for every step

| Lane | Who acts | A step belongs here when |
|---|---|---|
| Auto | the agent, alone; it flags what is off | reversible, low risk, rule-based or easy to check later |
| Propose | the agent prepares, a person gives one yes | it leaves the project (send, publish, spend, delete) or is costly to undo |
| Human | a person | intent, goals, limits, taste, policy |

Every action in "Who decides what" is Propose or Human. When unsure, use Propose. A request for a yes shows a count, a real example and what looks off, so the yes is a check and not a habit.

{envs_md}{agents_md}## Rules

1. Work goes to the role that owns the area. Do not assign work outside a role's "owns" column.
2. An action in the table above needs a yes from the role in "decides". The yes covers that one action.
3. An agent that stops for a decision adds a row to `owner-inputs.md` and carries on with whatever does not depend on the answer.
4. A change to this file is a decision: record it in `decision-register.md`.
5. Every piece of work has one named author, a person who can explain it. An agent is never the author.
"""

    # --- owner inputs
    for q in answers.get("open_questions", []):
        open_inputs.append((q, "asked during set-up"))
    input_rows = [[f"A{i}", today, what, "decision" if what.startswith("Decide ") else "answer", why, f"`{gov}/`", "project-foundation set-up", "open"] for i, (what, why) in enumerate(open_inputs, 1)]
    if not input_rows:
        input_rows.append(["A1", today, "(example) Confirm the list of roles", "decision", "example row, remove it", f"`{gov}/roles.md`", "set-up", "done"])

    inputs_md = f"""# Owner inputs: {name}

What agents and people are waiting for. One row per decision, answer or manual step that only a person can give.

## Rules

1. Add a row when you stop for a decision. Say what you need, what it blocks and where the person acts.
2. Kind is `decision` (a choice only that person may make), `answer` (a fact only they know) or `click` (a manual step in a tool: billing, access, a setting). No passwords or keys in a row.
3. Ids never change. When the answer arrives, set the status to `done` and put the answer in the decision register if it is a decision.
4. Read the open rows at the start of a working session.

## Inputs

{table(["Id", "Date", "What is needed", "Kind", "Why", "Where", "Asked by", "Status"], input_rows)}
"""

    # --- CLAUDE.md block
    def make_block(full):
      lines = [
        BEGIN,
        f"## Project foundation ({name})",
        "",
        f"- Sources of truth: `{gov}/sources-of-truth.md`. One home per kind of fact. Find the home before writing a fact down; link, do not copy. When two places disagree the home wins; when the home looks wrong, show both and ask.",
        f"- Decisions: `{gov}/decision-register.md`. Record decisions there with who, why and when to reopen. Agents record, they do not decide.",
        f"- Roles: `{gov}/roles.md`. It says who owns what and whose yes each action needs.",
        f"- Waiting on a person: add a row to `{gov}/owner-inputs.md`, then carry on with what does not depend on it. Read the open rows at the start of a session.",
      ]
      for m in modules:
        texts = MODULES[m] if full or m not in CLAUDE_SHORT else CLAUDE_SHORT[m]
        for text in texts:
            lines.append("- " + text.format(max=limit, max_plus=limit + 1, gov=gov))
      if folders and kind == "workspace":
        lines += ["", "| Folder | Put here |", "|---|---|"] + [f"| `{f['name']}/` | {cell(f.get('desc'))} |" for f in folders]
      lines.append(END)
      return "\n".join(lines) + "\n"

    block = {"CLAUDE.md": make_block(False), "AGENTS.md": make_block(True)}

    files = {
        f"{gov}/sources-of-truth.md": sources_md,
        f"{gov}/decision-register.md": decisions_md,
        f"{gov}/roles.md": roles_md,
        f"{gov}/owner-inputs.md": inputs_md,
    }
    if "one-task-one-change" in modules:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "handoff.template.md"), encoding="utf-8") as f:
            files[f"{gov}/handoff-template.md"] = f.read()
    structure = None
    if "structure" in modules:
        desc = {f["name"]: f.get("desc", "") for f in folders}
        structure = {"title": name, "max": limit, "desc": desc}
    return files, block, structure, [f["name"] for f in folders] if kind == "workspace" else [], len(open_inputs)


def put_block(path, block, dry):
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if BEGIN in old and END in old:
        new = old[: old.index(BEGIN)] + block.rstrip("\n") + old[old.index(END) + len(END):]
        action = "replaced block in"
    else:
        new = (old.rstrip("\n") + "\n\n" if old.strip() else "") + block
        action = "added block to"
    if not dry:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new if new.endswith("\n") else new + "\n")
    return action


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--answers", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")
    with open(args.answers, encoding="utf-8") as f:
        answers = json.load(f)
    today = datetime.date.today().isoformat()
    files, block, structure, folders, n_open = build(answers, today)
    dry = args.dry_run
    log = []

    for name in folders:
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            log.append(f"create folder  {name}/")
            if not dry:
                os.makedirs(path)

    for rel, text in files.items():
        path = os.path.join(root, rel)
        if os.path.exists(path):
            log.append(f"keep (exists)  {rel}")
            continue
        log.append(f"write          {rel}")
        if not dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    log.append(f"{put_block(os.path.join(root, 'CLAUDE.md'), block['CLAUDE.md'], dry)} CLAUDE.md")
    if os.path.exists(os.path.join(root, "AGENTS.md")):
        log.append(f"{put_block(os.path.join(root, 'AGENTS.md'), block['AGENTS.md'], dry)} AGENTS.md (full wording)")

    if structure is not None:
        cdir = os.path.join(root, ".claude")
        checker = os.path.join(cdir, "check-structure.py")
        cfg = os.path.join(cdir, "structure.json")
        if not dry:
            os.makedirs(cdir, exist_ok=True)
            shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_structure.py"), checker)
        log.append("write          .claude/check-structure.py")
        if os.path.exists(cfg):
            log.append("keep (exists)  .claude/structure.json")
        else:
            log.append("write          .claude/structure.json")
            if not dry:
                with open(cfg, "w", encoding="utf-8") as f:
                    json.dump(structure, f, indent=2, ensure_ascii=False)
                    f.write("\n")

    print(("DRY RUN, nothing written\n" if dry else "") + "\n".join(log))
    print(f"\nOpen inputs written to owner-inputs.md: {n_open}")
    if structure is not None and not dry:
        print("Next: python3 .claude/check-structure.py --write")


if __name__ == "__main__":
    main()
