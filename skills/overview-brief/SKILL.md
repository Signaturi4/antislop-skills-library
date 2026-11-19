---
name: overview-brief
description: Build or refresh one high-level overview document of a company, agency or project for a reader with no context - co-founder or new-hire onboarding, partner or investor overview, team kickoff, "explain the whole org on one page". Gathers the scattered sources (manifesto or vision, brand story, research reports, team board, unit economics, go-to-market plan, infra notes, project-memory search), splits them into a fixed section set (why, offer, buyers, story, org, economics, GTM, infra, rules, first steps), puts every number in a sourced fact ledger, anonymises people and clients for the audience, styles it in the project's own design tokens, and publishes one HTML page plus a Markdown copy. Use it whenever someone asks for an overview, summary of everything, onboarding doc, company brief, pitch-the-story document, "explain this to someone new", or wants an existing overview updated with new numbers, even if they never say "brief".
---

# overview-brief

tldr: audience -> section set -> source inventory -> fact ledger -> write sections (claim headline + source line) -> style in house tokens -> check script -> publish HTML + Markdown. Update mode changes only stale sections and keeps the URL.

A good overview lets a smart stranger answer three questions after ten minutes: why does this exist, how does it make money, and where do I start. Everything below serves that.

## 1. Fix the audience first

Ask (or infer from the request) who reads it and what they may see. The audience decides the section set and the sensitivity tier, so settle it before reading sources.

| Audience | Sections (from `references/section-catalog.md`) | Tier |
| --- | --- | --- |
| Co-founder / partner | all ten | internal: client names allowed only if the user says so; people as roles |
| New hire | why, today, story, org, rules, first steps (+ infra for engineers) | internal |
| Investor / advisor | why, today, buyers, economics, GTM, team | external: no client names, no servers, no models |
| Client / public pitch | why, today, buyers, story, how we work | public: outcomes only, no internals |

## 2. Inventory the sources, read narrowly

Look for these source types; each maps to sections. Read headings first (`grep -n '^#'`), then only the sections you need. Search the project memory (defrost `search`, or any MCP knowledge base) with one question per section, e.g. "team roles and KPIs", "unit economics margin", "active projects".

| Source type | Typical file | Feeds |
| --- | --- | --- |
| Vision / manifesto | `*Manifesto*.md`, `vision.md` | why, story |
| Brand story / messaging | `brand-story.md`, pillars | story, buyers |
| Research report | `final-report.md`, personas | buyers |
| Team board / roles | task board, Notion export, team memory | org |
| Unit economy / pricing | finance notes, price ladder, plan | economics |
| Sales / GTM plan | channel brief, pipeline | GTM |
| Infra notes / repo | runbooks, IaC repo, server memory | infra |
| Rules | CLAUDE.md, principles, manifesto lines | how we work |

When two sources disagree (vision says vertical X, revenue comes from Y), say so in the text and list it under open decisions. Do not pick a side silently.

## 3. Build the fact ledger before writing

Every number, date and named target goes into `ledger.json` (scratch, not published): `{"value": "59%", "claim": "margin, one-client month", "source": "team board", "date": "2026-11-03"}`. Write only numbers that are in the ledger. Research numbers keep their scope words ("in the studied slice"). No ledger entry, no number; write the claim without it or leave it out. This is the single rule that keeps an inspiring document honest.

## 4. Write each section in the same anatomy

Read `references/patterns.md` for the full pattern list. The core anatomy:

1. eyebrow: `N · Section name`
2. headline: a claim sentence ("Interviews close, volume is the gap"), never a label ("Metrics")
3. intro: one or two sentences, naming where it comes from ("From the team board (3 Nov).")
4. body in the component that fits the content shape (principles -> 3 cards, staged progression -> ladder, funnel -> bars, pricing -> table, system -> diagram + status table, rules -> two-column list, next steps -> ordered list)
5. source line: small text with source names and dates

Tone: aspiring in sections 1 and 4 (quote the manifesto and the brand story's belief line once each, as pull quotes), plain and factual everywhere else. Name tensions and gaps openly; a reader trusts a document that shows its limits.

## 5. Sensitivity pass

For the tier from step 1: people -> roles ("the founder", "Design Lead"); clients -> descriptors ("a B2B compliance-tech company"); servers, IPs, model names, internal hostnames -> plain functions ("the agency worker", "production"). Keep a private deny-list (`~/.claude/skill-deny-list.txt`) and run the check script on it.

## 6. Style in the house tokens

Find the project's design system first (tokens in `globals.css`, a design-system doc, an existing deck): display face, text face, accent ramp, canvas. Use them as CSS custom properties with a dark-mode block. Start from `assets/brief-template.html` (sticky section rail, hero, section cards, table, ladder, funnel, status pills, diagram styles) and replace the token values. If no design system exists, keep the template defaults and say so. When publishing as a claude.ai Artifact, follow the Artifact page contract (load `artifact-design` or use its quickstart).

## 7. Check, then publish

Run `python3 scripts/check_brief.py <page.html> --ledger ledger.json [--deny ~/.claude/skill-deny-list.txt]`. It flags: sections without a source line, claim headlines that are single words, numbers not in the ledger, deny-list terms, and a missing dark-mode token block. Fix every hit, then publish (Artifact, or the place the user named) and write the Markdown copy next to the sources (`<topic>-brief-<YYYY-MM-DD>.md`, e.g. via an html-to-markdown converter, then delete the nav-rail lines).

Tell the user: the link, who cannot open it yet (artifacts start private), the open decisions the document surfaced.

## Update mode

For "update the overview": read the existing page (or its Markdown), rebuild the ledger from current sources, diff values and dates, and change only the sections whose facts moved. Keep the same file path or URL so the link stays. List what changed in two to five lines.

## What this skill does not do

It does not invent strategy. Proposals (a new channel, a price) appear only when a source states them or the user asks; label them "proposal". It does not replace the detailed documents it links to.
