# Skill Cook

A unified, personalized collection of Claude Code skills — drop the `skills/`
folder into `.claude/` and go. Built from three sources, then adapted for an
**analytics-engineering** workflow (**SQL · dbt · Snowflake**), with a
**generic (un-branded) voice** and **GitHub + Jira + local** issue trackers.

Sources:

- **[Matt Pocock — mattpocock/skills](https://github.com/mattpocock/skills)** (MIT) — the engineering/productivity workflow skills, de-branded and re-stacked for SQL/dbt
- **[Andrej Karpathy CLAUDE.md — multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)** (MIT) — behavioral guidelines, as both a skill and a root `CLAUDE.md`
- **[i-have-adhd — ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)** (MIT) — ADHD-friendly output shaping
- **task-observer** — a meta-skill (added here) that watches work sessions for skill-improvement opportunities

Everything is flattened into one `skills/` folder (no name collisions).

## Install

**Personal (all your projects):**
```bash
cp -r skills/* ~/.claude/skills/
cp CLAUDE.md ~/.claude/CLAUDE.md   # optional: Karpathy's rules, always-on
```

**One project only:**
```bash
cp -r skills/* /path/to/project/.claude/skills/
cp CLAUDE.md   /path/to/project/.claude/CLAUDE.md   # optional
```

Restart Claude Code (or start a new session) to pick them up. Invoke a skill by name, e.g. `/i-have-adhd`, `/grill-me`, `/code-review`.

> **First run:** `/setup-skills` configures the issue tracker (GitHub, Jira, or local markdown), triage labels, and doc layout the engineering skills expect. Run it once per repo.

> **`CLAUDE.md` vs `karpathy-guidelines`:** the same Karpathy rules exist in two forms. The root `CLAUDE.md` is **always-on** (costs tokens every turn); the `karpathy-guidelines` skill is **on-demand**. Use one or the other, not both.

## How this differs from the originals

- **De-branded.** `ask-matt` → `which-skill`, `setup-matt-pocock-skills` → `setup-skills`, and all first-person "Matt" voice/branding removed. Generic throughout.
- **Re-stacked for analytics engineering.** The software-design trio was repurposed to dbt: `codebase-design` → **`dbt-model-design`** (grain/layering vocabulary), `tdd` → **`dbt-test`** (data-testing strategy), `improve-codebase-architecture` → **`dbt-project-audit`**. Examples use SQL/dbt/pytest-of-data rather than app code.
- **Trackers: GitHub + Jira + local.** `/setup-skills` treats all three as first-class (added a Jira seed template using [`jira-cli`](https://github.com/ankitpokhrel/jira-cli)); GitLab dropped to an "other" option.
- **Removed** skills with no analytics analog: `migrate-to-shoehorn` and `scaffold-exercises` (TS/course-specific), plus `setup-python-modules` and `setup-pre-commit` (Python package/app tooling).

## Skills

### Engineering
| Skill | What it does |
|---|---|
| `which-skill` | Router — asks which skill or flow fits your situation. |
| `setup-skills` | One-time repo config: issue tracker (GitHub/Jira/local), triage labels, doc layout. |
| `code-review` | Reviews changes since a fixed point on Standards + Spec axes, in parallel sub-agents. |
| `dbt-model-design` | Vocabulary for designing dbt models: grain, layering (staging/intermediate/marts), materialization, DRY. |
| `dbt-test` | dbt data-testing strategy: grain tests, generic/singular/unit tests, source freshness. |
| `dbt-project-audit` | Scan a dbt project for structure/test/cost issues → visual HTML report → grill. |
| `diagnosing-bugs` | Diagnosis loop for hard bugs and failing models/queries. |
| `domain-modeling` | Build/sharpen a project's domain model (CONTEXT.md, ADRs). |
| `grill-with-docs` | Relentless interview to sharpen a plan; produces ADRs + glossary. |
| `implement` | Implement work from a spec or set of tickets (drives `dbt-test`, then `code-review`). |
| `prototype` | Build a throwaway prototype to answer a design question. |
| `research` | Investigate against primary sources, capture findings as Markdown. |
| `resolving-merge-conflicts` | Resolve an in-progress git merge/rebase conflict. |
| `to-spec` | Turn the conversation into a spec, publish to the tracker. |
| `to-tickets` | Break a plan/spec into tracer-bullet tickets with blocking edges. |
| `triage` | Move issues/PRs through a triage state machine into agent-ready briefs. |
| `wayfinder` | Plan huge work as a map of decision tickets, resolved one at a time. |
| `wizard` | Generate an interactive bash wizard for human-only steps. |

### Productivity
| Skill | What it does |
|---|---|
| `grill-me` | Relentless interview to sharpen a plan or design. |
| `grilling` | Stress-test your thinking about a plan, decision, or idea. |
| `handoff` | Compact the conversation into a handoff doc for another agent. |
| `teach` | Teach you a new skill or concept in this workspace. |
| `to-questionnaire` | Turn a decision you can't answer into a questionnaire for someone else. |
| `wait-what` | "That last message didn't land" — re-pitch it. |
| `writing-for-agents` | Writing docs for agents (skills, AGENTS.md, CLAUDE.md). |

### Experimental (upstream `in-progress` — treat as WIP)
| Skill | What it does |
|---|---|
| `claude-handoff` | Hand the conversation to a fresh background agent. |
| `loop-me` | Grill you about specs for workflows you want to build. |
| `writing-beats` | Assemble raw material into a journey of beats. |
| `writing-fragments` | Mine raw writing fragments, no structure yet. |
| `writing-shape` | Shape raw material into an article, paragraph by paragraph. |

### Misc
| Skill | What it does |
|---|---|
| `git-guardrails-claude-code` | Hooks to block dangerous git commands before they run. |

### Meta
| Skill | What it does |
|---|---|
| `task-observer` | Watches work sessions and logs skill-improvement opportunities for later review. Bundle: `SKILL.md` + `references/{weekly-review,skill-authoring,environments}.md`. |

### Guidelines & output style
| Skill | What it does |
|---|---|
| `karpathy-guidelines` | Reduce common LLM coding mistakes (on-demand form of `CLAUDE.md`). |
| `i-have-adhd` | Lead with the next action, number steps, restate state, make wins visible. `/i-have-adhd` … "stop adhd mode". |

## Licenses

Matt Pocock, Ayoub Ghriss, and the andrej-karpathy-skills contributors — all MIT. Adaptations here preserve that. See each source repository for full license text.
