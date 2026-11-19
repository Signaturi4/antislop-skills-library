#!/usr/bin/env python3
"""Scaffold the project foundation from an answers file.

Usage:
  python3 setup.py <project-root> --answers answers.json [--dry-run]

What it writes (existing files are never overwritten, except the marked block in CLAUDE.md):
  <governance_dir>/sources-of-truth.md   one home per kind of fact, internal or external
  <governance_dir>/decision-register.md  decisions with id, date, who, why
  <governance_dir>/roles.md              roles, what each owns, who decides what
  <governance_dir>/owner-inputs.md       what agents and people are waiting for
  CLAUDE.md                              short rule block between markers (replaced on re-run)
  AGENTS.md                              same block, only when the file already exists
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
        "Every task has two homes: the code host for code and docs, the task board for status, owner and due date. Link them to each other. The board wins on status.",
    ],
    "confirm-outward": [
        "Ask before anything hard to undo or visible outside the project: merge, deploy, publish, send, pay, delete, change access. A yes covers that one action only.",
    ],
    "privacy": [
        "No personal names, emails, client names or secrets in anything that leaves the project (public repos, issues a client can read, shared documents). Use roles.",
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
    "skills-per-task": [
        "For any major task check the skills library first and use a fitting skill. Name the skills used in the final report; say so in one line when none fits.",
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
3. **External homes are read, not mirrored.** Read them through the tool in "read via". A copy inside the project is allowed only as a snapshot with the date in its file name, and it is never edited.
4. **The home wins.** When two places disagree, the home is right. When the home itself looks wrong, show both versions to the {owner} and ask; do not pick a side.
5. **No home yet.** Add a row with `{TBD}`, add a line to `owner-inputs.md`, and ask. Do not invent a home.
6. **Generated files are not homes.** Indexes and reports name the command that makes them and are never edited by hand.
7. **Cite the home.** Every claim about users, numbers, money or decisions says where it came from. With no source, write "no source yet".

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
        dec_rows.append([d.get("id") or f"D-{i:03d}", d.get("date") or today, d.get("decision"), d.get("decided_by") or owner, d.get("why"), d.get("scope") or "project", d.get("replaces") or "none", d.get("status") or "active"])
    if not dec_rows:
        dec_rows.append(["D-001", today, "Project foundation set up: sources of truth, roles, decision register", owner, "one place to look for how the project runs", "project", "none", "active"])

    decisions_md = f"""# Decision register: {name}

The home for decisions. A decision that is not here does not bind anyone.

## Rules

1. One row per decision. Newest at the bottom. Ids never change and are never reused.
2. Write down who decided and why. "Why" is what lets someone judge later whether the decision still holds.
3. Agents record decisions; they do not make them. Who may decide what is in `roles.md`.
4. A decision is not edited after the fact. To change it, add a new row and set the old one to `replaced by D-...`.
5. A rule in `CLAUDE.md` or in a skill that comes from a decision names its id.
6. An open question is not a decision. It goes to `owner-inputs.md`.

## Register

{table(["Id", "Date", "Decision", "Decided by", "Why", "Scope", "Replaces", "Status"], dec_rows)}
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

    roles_md = f"""# Roles and responsibilities: {name}

The home for who does what and who decides what.

## Roles

{table(["Role", "Who", "Owns", "Decides", "Does not do"], role_rows)}

One role can be one person, several people, or an agent. Use the role name, not a person's name, in anything that leaves the project.

## Who decides what

{table(["Action", "Decides", "Consulted", "What an agent may do"], right_rows)}

## Rules

1. Work goes to the role that owns the area. Do not assign work outside a role's "owns" column.
2. An action in the table above needs a yes from the role in "decides". The yes covers that one action.
3. An agent that stops for a decision adds a row to `owner-inputs.md` and carries on with whatever does not depend on the answer.
4. A change to this file is a decision: record it in `decision-register.md`.
"""

    # --- owner inputs
    for q in answers.get("open_questions", []):
        open_inputs.append((q, "asked during set-up"))
    input_rows = [[f"A{i}", today, what, why, "project-foundation set-up", "open"] for i, (what, why) in enumerate(open_inputs, 1)]
    if not input_rows:
        input_rows.append(["A1", today, "(example) Confirm the list of roles", "example row, remove it", "set-up", "done"])

    inputs_md = f"""# Owner inputs: {name}

What agents and people are waiting for. One row per decision, answer or manual step that only a person can give.

## Rules

1. Add a row when you stop for a decision. Say what you need and what it blocks.
2. Ids never change. When the answer arrives, set the status to `done` and put the answer in the decision register if it is a decision.
3. Read the open rows at the start of a working session.

## Inputs

{table(["Id", "Date", "What is needed", "Why", "Asked by", "Status"], input_rows)}
"""

    # --- CLAUDE.md block
    lines = [
        BEGIN,
        f"## Project foundation ({name})",
        "",
        f"- Sources of truth: `{gov}/sources-of-truth.md`. One home per kind of fact. Find the home before writing a fact down; link, do not copy. When two places disagree the home wins; when the home looks wrong, show both and ask.",
        f"- Decisions: `{gov}/decision-register.md`. Record decisions there with who and why. Agents record, they do not decide.",
        f"- Roles: `{gov}/roles.md`. It says who owns what and whose yes each action needs.",
        f"- Waiting on a person: add a row to `{gov}/owner-inputs.md`, then carry on with what does not depend on it. Read the open rows at the start of a session.",
    ]
    for m in modules:
        for text in MODULES[m]:
            lines.append("- " + text.format(max=limit, max_plus=limit + 1))
    if folders and kind == "workspace":
        lines += ["", "| Folder | Put here |", "|---|---|"] + [f"| `{f['name']}/` | {cell(f.get('desc'))} |" for f in folders]
    lines.append(END)
    block = "\n".join(lines) + "\n"

    files = {
        f"{gov}/sources-of-truth.md": sources_md,
        f"{gov}/decision-register.md": decisions_md,
        f"{gov}/roles.md": roles_md,
        f"{gov}/owner-inputs.md": inputs_md,
    }
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

    log.append(f"{put_block(os.path.join(root, 'CLAUDE.md'), block, dry)} CLAUDE.md")
    if os.path.exists(os.path.join(root, "AGENTS.md")):
        log.append(f"{put_block(os.path.join(root, 'AGENTS.md'), block, dry)} AGENTS.md")

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
