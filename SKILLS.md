# Skill Catalog

Every skill in this repo — what it does, when to reach for it, and how to invoke it.
28 skills: **20 engineering**, **8 productivity**.

## How invocation works

| Badge | Meaning |
|---|---|
| **`/slash`** | User-invoked only (`disable-model-invocation: true`). Claude will *not* reach for it on its own — you type it. |
| **auto** | Claude may pull it in automatically when the task matches its description. You can also invoke it by name. |

15 skills are slash-only, 13 are auto. Nothing loads at session start on its own — if you want an always-on behaviour (like `/i-have-adhd`), invoke it yourself at the top of the session.

**First run in a new repo:** `/setup-skills` once, to configure the issue tracker (GitHub / Jira / local markdown), triage labels, and doc layout the engineering skills expect.

**Lost?** `/which-skill` is the router — it walks you to the right one.

---

# Engineering (20)

## Start here

### `/which-skill` — slash
The router over everything in this repo. Describes the **main flow** (idea → ship), the on-ramps that merge onto it, and what's standalone. Reach for it when you know you want a skill but not which one.
*Bundle: `PHASE-BOUNDARIES.md` — when to continue vs `/clear` vs `/handoff` vs subagent vs `/compact`.*

### `/setup-skills` — slash
One-time per-repo configuration: which issue tracker you use (GitHub, Jira, or local markdown), the triage label vocabulary, and where `CONTEXT.md` + ADRs live. Run it before the other engineering skills, which read the files it writes.
*Bundle: seed templates for `issue-tracker-{github,jira,local}.md`, `triage-labels.md`, `domain.md`.*

## The main flow: idea → ship

These chain in order. Keep steps 1–3 in one context window, then `/clear` between each `/implement`.

### `/grill-with-docs` — slash
A relentless interview that sharpens a vague idea into a solid plan **and leaves a paper trail** — writing ADRs and glossary entries into the repo as decisions land. The stateful twin of `/grill-me`. Start here when you're in a working directory.

### `/to-spec` — slash
Turns the conversation you've just had into a written spec and publishes it to your tracker. No interview — pure synthesis of what's already been discussed. Use when the thinking is done and you want it recorded.

### `/to-tickets` — slash
Breaks a plan or spec into **tracer-bullet tickets**, each declaring what blocks it. On Jira/GitHub those become native blocking links; on a local tracker, one markdown file per ticket. Use when the work spans more than one session.

### `/implement` — slash
Builds one ticket or spec. Drives `/dbt-test` internally (grain test first, then the business rules), then closes out with `/code-review` before committing. The workhorse.

### `/code-review` — auto
Reviews everything since a fixed point (commit, branch, tag, merge-base) along **two axes in parallel sub-agents**: *Standards* (does it follow this repo's documented conventions?) and *Spec* (does it do what the ticket asked?). Reports side by side. Use before merging, or any time you want a branch or PR reviewed.

## dbt & data modeling

### `/dbt-model-design` — auto
The shared vocabulary for designing models: **grain**, **layer** (staging → intermediate → marts), **materialization**, **contract**, **exposure**. Also the principles — one model/one grain, layer discipline, DRY into `int_` models or macros, and the materialization decision table. Reach for it when deciding where logic belongs or what shape a model should be. Other dbt skills speak this language.

### `/dbt-test` — auto
Data-testing strategy. Grain tests (`unique` + `not_null`) come first and always; then generic tests, package tests (`dbt_utils`), singular tests for business invariants, unit tests for complex logic, and source freshness. Covers the anti-patterns too — tautological tests, missing grain tests, testing internals.
*Bundle: `tests.md` (good/bad examples), `unit-tests.md` (dbt 1.8+ unit testing).*

### `/dbt-project-audit` — slash
Scans a whole dbt project for untested grains, undocumented marts, broken layering, fan-out risk, duplicated logic, cost smells (full-refresh tables that should be incremental), and orphan models. Presents findings as a **visual HTML report** with before/after DAG diagrams, then grills you through whichever fix you pick.
*Bundle: `HTML-REPORT.md` — the report scaffold and diagram patterns.*

## On-ramps — situations that generate work

### `/triage` — slash
Moves incoming issues and external PRs through a state machine of triage roles: categorise, verify, grill where under-specified, and write agent-ready briefs. Only for work **you didn't create** — tickets from `/to-tickets` are already agent-ready.
*Bundle: `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md`.*

### `/diagnosing-bugs` — auto
The diagnosis loop for hard problems — the bug that resists a first look, the intermittent flake, the regression between two known-good states, the query that got slow. Refuses to theorise until it has a **tight feedback loop** (one command that reliably goes red), then fixes with a regression test.
*Bundle: `scripts/hitl-loop.template.sh`.*

### `/wayfinder` — slash
For an effort too big to hold in one session — a greenfield build, a migration. Charts a **shared map of decision tickets** on your tracker and resolves them one at a time, producing *decisions, not deliverables*, until the path is clear. Then hands off to `/to-spec`. The heaviest skill here; save it for genuine fog.

## Supporting

### `/domain-modeling` — auto
Builds and sharpens the project's domain language: challenge a fuzzy term, split an overloaded word doing three jobs, record a hard-to-reverse decision as an ADR. Keeps `CONTEXT.md` a clean glossary.
*Bundle: `ADR-FORMAT.md`, `CONTEXT-FORMAT.md`.*

### `/research` — auto
Delegates reading legwork to a background agent: investigates a question against high-trust primary sources and leaves a cited markdown file in the repo. Keep working while it reads.

### `/prototype` — auto
A small, throwaway program that answers **one** design question — does this model feel right, what should this look like. Throwaway is a constraint on how it's written, not a promise to delete it.
*Bundle: `LOGIC.md`, `UI.md`.*

### `/resolving-merge-conflicts` — auto
Works an in-progress merge or rebase conflict hunk by hunk, resolving by **intent** traced to each side's source rather than by picking lines. Never runs `--abort`.

### `/wizard` — auto
Generates an interactive bash script for steps **only a human can do** — provisioning infrastructure, setting up credentials or CI secrets, clicking through an unfamiliar dashboard, a one-off cutover. Not for anything the agent could do itself.
*Bundle: `template.sh`.*

### `/git-guardrails-claude-code` — auto
Installs Claude Code hooks that block dangerous git commands (`push`, `reset --hard`, `clean`, `branch -D`) *before* they execute.
*Bundle: `scripts/block-dangerous-git.sh`.*

### `/karpathy-guidelines` — auto
Behavioural rules that reduce common LLM coding mistakes: state assumptions, keep it minimal, make surgical changes, define verifiable success criteria. The on-demand form of this repo's root `CLAUDE.md` — use one or the other, not both.

---

# Productivity (8)

## Thinking & interrogation

### `/grilling` — auto
The interview **primitive**: rounds of questions, a moving frontier, facts are the agent's job and decisions are yours. `/grill-me` and `/grill-with-docs` are the two named ways in; `/triage`, `/wayfinder`, and `/dbt-project-audit` all run it internally. Invoke directly only when you want the interview with no wrapper.

### `/grill-me` — slash
The same relentless interview as `/grill-with-docs`, but **stateless** — saves nothing, writes no `CONTEXT.md`. Use it when there's no repo underneath: a plan, a career decision, a piece of writing.

## Sessions, context & docs

### `/handoff` — slash
Compacts the current conversation into a portable markdown handoff document another agent can pick up. Narrow by design — for a new harness, a new directory, a colleague, or forking a side task mid-phase.

### `/wait-what` — slash
The corrective for a message that didn't land. Say it mid-conversation, inside any other skill, and the agent re-pitches what it just said in plain English with the context you were missing.

### `/writing-for-agents` — auto
The reference for writing documents **agents** consume: skills, `AGENTS.md`, `CLAUDE.md`, pointed-at docs. Covers cognitive load, what belongs in a doc vs. discoverable from the environment.
*Bundle: `SKILL-MECHANICS.md` — frontmatter, invocation choice, router skills.*

## Learning & comms

### `/teach` — slash
Teaches you a concept or skill across multiple sessions, using the current directory as a stateful workspace — tracks a mission, a glossary, resources, and a learning record.
*Bundle: `MISSION-FORMAT.md`, `GLOSSARY-FORMAT.md`, `RESOURCES-FORMAT.md`, `LEARNING-RECORD-FORMAT.md`.*

### `/to-questionnaire` — slash
For when the blocker isn't in your head or the codebase but in **someone else's**. Interviews you about the *send* (who it's for, what you need back) and writes them a questionnaire aimed at the gap.

## Working style

### `/i-have-adhd` — slash
Shapes output for an ADHD reader: lead with the next action, number multi-step work, restate state across turns, suppress tangents, give specific time estimates, make wins visible. Stays on until you say "stop adhd mode". **Invoke it at the top of a session** — it will not self-activate.

---

# The main flow at a glance

```
                    ┌─ /triage ──────────┐   (incoming issues)
                    ├─ /diagnosing-bugs ─┤   (something's broken)
                    └─ /wayfinder ───────┘   (too big for one session)
                              │
                              ▼
  /grill-with-docs  →  /to-spec  →  /to-tickets  →  /implement  →  /code-review
   (sharpen idea)      (write it)    (split it)      (build it)     (check it)
                                                          │
                                     drives /dbt-test ────┘

  Underneath:  /dbt-model-design · /domain-modeling   (vocabulary layers)
  Upkeep:      /dbt-project-audit                     (finds work to feed the flow)
```

## Quick reference

| Situation | Reach for |
|---|---|
| Don't know which skill | `/which-skill` |
| New repo, first time | `/setup-skills` |
| Vague idea, need to sharpen it | `/grill-with-docs` (in a repo) or `/grill-me` (not) |
| Ready to write it down | `/to-spec` → `/to-tickets` |
| Time to build | `/implement` |
| About to merge | `/code-review` |
| Designing a model's shape | `/dbt-model-design` |
| Adding data quality checks | `/dbt-test` |
| Project-wide health check | `/dbt-project-audit` |
| Something is broken/slow | `/diagnosing-bugs` |
| Issues piling up | `/triage` |
| Huge foggy effort | `/wayfinder` |
| Need facts from primary sources | `/research` |
| Only a human can do this step | `/wizard` |
| That answer didn't land | `/wait-what` |
| Leaving / switching context | `/handoff` |
| Want ADHD-friendly output | `/i-have-adhd` |
