# Skill Cook

A unified, drop-in collection of Claude Code skills, merged from three sources:

- **[Matt Pocock — mattpocock/skills](https://github.com/mattpocock/skills)** (MIT) — 35 engineering/productivity skills
- **[Andrej Karpathy CLAUDE.md — multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)** (MIT) — behavioral guidelines as both a skill and a `CLAUDE.md`
- **[i-have-adhd — ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)** (MIT) — ADHD-friendly output shaping

Everything is flattened into a single `skills/` folder (no name collisions) so it drops straight into `.claude/`.

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

> **`CLAUDE.md` vs `karpathy-guidelines`:** the same Karpathy rules exist in two forms. The root `CLAUDE.md` is **always-on** context (costs tokens every turn). The `karpathy-guidelines` skill is **on-demand**. Use one or the other, not both.

## Skills

### Matt Pocock — Engineering
| Skill | What it does |
|---|---|
| `ask-matt` | Router over these skills — asks which one fits your situation. |
| `code-review` | Reviews changes since a fixed point on Standards + Spec axes, in parallel sub-agents. |
| `codebase-design` | Shared vocabulary for designing deep modules. |
| `diagnosing-bugs` | Diagnosis loop for hard bugs and performance regressions. |
| `domain-modeling` | Build/sharpen a project's domain model (CONTEXT.md, ADRs). |
| `grill-with-docs` | Relentless interview to sharpen a plan; produces ADRs + glossary. |
| `implement` | Implement work from a spec or set of tickets. |
| `improve-codebase-architecture` | Scan for deepening opportunities → visual HTML report → grill. |
| `prototype` | Build a throwaway prototype to answer a design question. |
| `research` | Investigate against primary sources, capture findings as Markdown. |
| `resolving-merge-conflicts` | Resolve an in-progress git merge/rebase conflict. |
| `setup-matt-pocock-skills` | One-time config (issue tracker, triage labels, doc layout). |
| `tdd` | Test-driven development / red-green-refactor. |
| `to-spec` | Turn the conversation into a spec, publish to the tracker. |
| `to-tickets` | Break a plan/spec into tracer-bullet tickets with blocking edges. |
| `triage` | Move issues/PRs through a triage state machine into agent-ready briefs. |
| `wayfinder` | Plan huge work as a map of decision tickets, resolved one at a time. |
| `wizard` | Generate an interactive bash wizard for human-only steps. |

### Matt Pocock — Productivity
| Skill | What it does |
|---|---|
| `grill-me` | Relentless interview to sharpen a plan or design. |
| `grilling` | Stress-test your thinking about a plan, decision, or idea. |
| `handoff` | Compact the conversation into a handoff doc for another agent. |
| `teach` | Teach you a new skill or concept in this workspace. |
| `to-questionnaire` | Turn a decision you can't answer into a questionnaire for someone else. |
| `wait-what` | "That last message didn't land" — re-pitch it. |
| `writing-for-agents` | Writing docs for agents (skills, AGENTS.md, CLAUDE.md). |

### Matt Pocock — Misc
| Skill | What it does |
|---|---|
| `git-guardrails-claude-code` | Hooks to block dangerous git commands before they run. |
| `migrate-to-shoehorn` | Migrate test `as` assertions to @total-typescript/shoehorn. |
| `scaffold-exercises` | Create exercise directory structures that pass linting. |
| `setup-pre-commit` | Set up Husky + lint-staged pre-commit hooks. |

### Matt Pocock — Experimental (author's `in-progress`)
Kept but unpolished — treat as WIP.
| Skill | What it does |
|---|---|
| `claude-handoff` | Hand the conversation to a fresh background agent. |
| `loop-me` | Grill you about specs for workflows you want to build. |
| `setup-ts-deep-modules` | Wire dependency-cruiser into a TS repo for deep modules. |
| `writing-beats` | Assemble raw material into a journey of beats. |
| `writing-fragments` | Mine raw writing fragments, no structure yet. |
| `writing-shape` | Shape raw material into an article, paragraph by paragraph. |

### Karpathy
| Skill | What it does |
|---|---|
| `karpathy-guidelines` | Behavioral guidelines to reduce common LLM coding mistakes (on-demand form of `CLAUDE.md`). |

### ADHD
| Skill | What it does |
|---|---|
| `i-have-adhd` | Lead with the next action, number multi-step work, restate state, suppress tangents, make wins visible. `/i-have-adhd` … "stop adhd mode". |

## What was left out

Matt Pocock's `deprecated/` skills were excluded (the author retired them). To pull them in later:
```bash
git clone --depth 1 https://github.com/mattpocock/skills.git /tmp/mp
cp -r /tmp/mp/skills/deprecated/*/ ~/.claude/skills/
```

## Licenses

All three sources are MIT-licensed. Original copyrights: Matt Pocock, Ayoub Ghriss, and the andrej-karpathy-skills contributors. See each source repository for full license text.
