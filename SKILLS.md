# Skill Catalog

Every skill in this repo: what it does, when to reach for it, and how to invoke it.

28 skills. **Six install by default** (`skills/`), the other **22 are held back** in `extras/` so the starting point stays small. Everything here installs by name:

```bash
./install.sh --list          # every name
./install.sh <name> ...      # add any of them, from either group
./install.sh --all           # all 28
```

New to skills? Read [TEAM-GUIDE.md](TEAM-GUIDE.md) instead. This page is the reference.

## How invocation works

| Badge | Meaning |
|---|---|
| **`/slash`** | User-invoked only (`disable-model-invocation: true`). Claude will *not* reach for it on its own. You type it. |
| **auto** | Claude may pull it in automatically when the task matches its description. You can also invoke it by name. |

15 skills are slash-only, 13 are auto. An auto skill costs a little context on every turn, because its description stays loaded so Claude knows it exists; a slash-only skill costs nothing until you type it. That is the main reason not to install all 28 by reflex.

Nothing turns itself on at session start. For an always-on behaviour like `/i-have-adhd`, invoke it yourself at the top of the session.

---

# The starter set (6)

Installed by default. No setup, no repo writes unless you ask.

### `/grill-me` — slash
A relentless interview about a plan or design, worked as rounds of numbered questions, each with a recommended answer, until every open decision is settled. Stateless: it saves nothing. Reach for it before building anything you have not fully thought through, in or out of a repo.

### `/grill-with-docs` — slash
The same interview, aimed at a repo. As decisions land it writes them down: terms into a `CONTEXT.md` glossary, hard-to-reverse choices into ADRs. Strictly better than `/grill-me` when you are in a working directory, because it leaves a paper trail the next session can read.

### `/wait-what` — slash
Fire it the moment an answer does not land. Claude re-pitches what it just said in plain English, using the project's own vocabulary. Seven lines long, and the quickest way to understand what a skill is.

### `/handoff` — slash
Compacts the current conversation into a handoff document so a fresh session, or another person, can pick the work up. Reach for it when a session is getting long, when you are switching machines, or at the end of the day.

### `grilling` — auto
The interview engine: the design tree, the frontier, rounds of questions. Facts are the agent's job, decisions are yours. `/grill-me` and `/grill-with-docs` both call it. You can invoke it directly if you want the interview with no wrapper.

### `domain-modeling` — auto
The active discipline behind the glossary: challenge a fuzzy term, resolve an overloaded word, stress-test a definition against edge cases, and record decisions as ADRs. Called by `/grill-with-docs`.
*Bundle: `CONTEXT-FORMAT.md`, `ADR-FORMAT.md`.*

---

# Extras (22)

Held back, not removed. Install any by name.

## Getting started with the rest

### `/which-skill` — slash
The router over everything here. Describes the main flow (idea to ship), the on-ramps that merge onto it, and what is standalone. Reach for it when you know you want a skill but not which one.
*Bundle: `PHASE-BOUNDARIES.md`, when to continue vs `/clear` vs `/handoff` vs subagent vs `/compact`.*

### `/setup-skills` — slash
One-time per-repo configuration: which issue tracker you use (GitHub, Jira, or local markdown), the triage label vocabulary, and where `CONTEXT.md` and ADRs live. **Required before `/to-spec`, `/to-tickets`, `/triage` and `/wayfinder`**, which read the files it writes.
*Bundle: seed templates for `issue-tracker-{github,jira,local}.md`, `triage-labels.md`, `domain.md`.*

## The main flow: idea to ship

These chain in order. Keep the first steps in one context window, then `/clear` between each `/implement`. All of them need `/setup-skills` first.

### `/to-spec` — slash
Turns the conversation you just had into a written spec on the tracker. No second interview: it synthesises what is already known, settles which modules and seams you are touching, and publishes.

### `/to-tickets` — slash
Breaks a plan or spec into tracer-bullet tickets, each a narrow but complete slice, each declaring what blocks it. Handles wide mechanical refactors as expand-migrate-contract instead of forcing them into a slice.

### `/implement` — slash
Builds the work described by a spec or ticket, testing at pre-agreed seams and closing out with a review before committing.

### `code-review` — auto
Reviews the diff since a fixed point on two axes at once: **Standards** (does it follow this repo's conventions, plus a code-smell baseline) and **Spec** (does it do what the ticket asked). Runs both as parallel sub-agents so neither colours the other.
**Note:** installing this overrides Claude Code's built-in `/code-review`.

## dbt and data modelling

### `dbt-model-design` — auto
The vocabulary for model design: grain, layering across staging, intermediate and marts, materialization, and where DRY helps versus hurts. Reach for it when designing or refactoring a model.

### `dbt-test` — auto
What to test and how. The grain test comes first, every model, every time; then referential integrity, business rules, and source freshness. Covers generic, package, singular and unit tests, and the anti-patterns worth knowing.
*Bundle: `tests.md`, `unit-tests.md`.*

### `/dbt-project-audit` — slash
Scans a whole project for untested grains, layering violations and cost smells, presents them as a visual HTML report, then grills you through whichever fix you pick.
*Bundle: `HTML-REPORT.md`.*

## When something comes up

### `/triage` — slash
Moves incoming issues through a state machine of triage roles, verifying the claim, grilling where the request is thin, and writing agent-ready briefs. For issues you did not write. Needs `/setup-skills`.
*Bundle: `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md`.*

### `diagnosing-bugs` — auto
A disciplined loop for hard bugs and performance regressions. It refuses to theorise until it has a **tight** feedback loop that already goes red on this specific bug, then minimises, hypothesises, instruments, fixes, and locks it down with a regression test.
*Bundle: `scripts/hitl-loop.template.sh`.*

### `/wayfinder` — slash
For an effort too big for one session and still wrapped in fog. Charts a shared map of decision tickets on the tracker and resolves them one at a time until the route is clear. Produces decisions, not deliverables. The most demanding thing here. Needs `/setup-skills`.

## Supporting

### `research` — auto
Sends a background agent to investigate a question against primary sources and leave a cited Markdown file behind. You keep working while it reads.

### `prototype` — auto
Throwaway code that answers one design question. Kept as a primary source on its own branch once the answer is folded back in.
*Bundle: `LOGIC.md`, `UI.md`.*

### `resolving-merge-conflicts` — auto
Works an in-progress merge or rebase hunk by hunk, resolving by intent traced back to each side's original reason rather than by picking lines. Never aborts.

### `wizard` — auto
Generates an interactive bash script for steps only a human can take: provisioning, credentials, CI secrets, clicking through an unfamiliar dashboard, a one-off cutover.
*Bundle: `template.sh`.*

### `git-guardrails-claude-code` — auto
Sets up Claude Code hooks that block dangerous git commands (force push, `reset --hard`, `clean`, `branch -D`) before they execute. **Writes to your Claude Code settings.**
*Bundle: `scripts/block-dangerous-git.sh`.*

### `karpathy-guidelines` — auto
The on-demand twin of this repo's `CLAUDE.md`: state assumptions, keep it simple, make surgical changes, define success criteria. Use this **or** the always-on `CLAUDE.md`, never both.

## Thinking, writing and comms

### `/teach` — slash
Teaches you a concept across multiple sessions, using the current directory as a stateful workspace with lessons, a glossary and learning records.
*Bundle: `MISSION-FORMAT.md`, `GLOSSARY-FORMAT.md`, `LEARNING-RECORD-FORMAT.md`, `RESOURCES-FORMAT.md`.*

### `/to-questionnaire` — slash
When the answer lives in someone else's head, this writes them a questionnaire. It interviews you about the **send** (who it is for, what you need back) rather than the subject, and aims the questions at the gap.

### `/i-have-adhd` — slash
Reshapes output: answer first, numbered steps, state restated each turn, no filler, wins made visible. Stays on until you say "stop adhd mode". Invoke at the top of a session.

### `writing-for-agents` — auto
How to write documents agents read well: skills, `CLAUDE.md`, and anything reached by a pointer. Read it before adding or editing a skill in this repo.
*Bundle: `SKILL-MECHANICS.md`.*
