# Skill Cook

28 Claude Code skills for **analytics engineering** — SQL, dbt and Snowflake —
wired to **GitHub, Jira, or local** issue tracking. Drop the `skills/` folder
into `.claude/` and go.

## Install

**Personal (all your projects):**
```bash
./install.sh
```
```powershell
.\install.ps1
```

**One project only:**
```bash
./install.sh --project /path/to/project
```

**Just a few, to start:**
```bash
./install.sh grill-me wait-what dbt-test
```

Run `./install.sh --list` to see every name. Add the always-on Karpathy rules separately if you want them: `cp CLAUDE.md ~/.claude/CLAUDE.md` (see the note below).

Start a new Claude Code session, then type `/grill-me`. If it autocompletes, the install worked.

> **Heads-up:** installing `code-review` shadows Claude Code's built-in `/code-review`. Delete `~/.claude/skills/code-review` to get the built-in back, or leave it out of the install.

> **First run:** `/setup-skills` configures the issue tracker (GitHub, Jira, or local markdown), triage labels, and doc layout the engineering skills expect. Run it once per repo.

> **`CLAUDE.md` vs `karpathy-guidelines`:** the same Karpathy rules exist in two forms. The root `CLAUDE.md` is **always-on** (costs tokens every turn); the `karpathy-guidelines` skill is **on-demand**. Use one or the other, not both.

## Skills

> **📖 See [SKILLS.md](SKILLS.md)** for the full catalog — what each skill does, when to reach for it, invocation type, and how they chain together.

Organized into two folders for navigation. **Claude Code does not discover skills recursively:** it looks for `<skills-dir>/<skill-name>/SKILL.md`, exactly one level deep. That is why the install script flattens these buckets rather than copying them across as-is. Once installed, invocation is always by the skill's own name (`/dbt-test`, etc.), and the bucket is invisible.

```
skills/
├── engineering/     # build, review, data modeling, git, coding guidelines
└── productivity/    # thinking, writing, comms, working style
```

### `skills/engineering/` (20)
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
| `git-guardrails-claude-code` | Hooks to block dangerous git commands before they run. |
| `karpathy-guidelines` | Reduce common LLM coding mistakes (on-demand form of `CLAUDE.md`). |

### `skills/productivity/` (8)
| Skill | What it does |
|---|---|
| `grill-me` | Relentless interview to sharpen a plan or design. |
| `grilling` | Stress-test your thinking about a plan, decision, or idea. |
| `handoff` | Compact the conversation into a handoff doc for another agent. |
| `teach` | Teach you a new skill or concept in this workspace. |
| `to-questionnaire` | Turn a decision you can't answer into a questionnaire for someone else. |
| `wait-what` | "That last message didn't land" — re-pitch it. |
| `writing-for-agents` | Writing docs for agents (skills, AGENTS.md, CLAUDE.md). |
| `i-have-adhd` | Lead with the next action, number steps, restate state, make wins visible. `/i-have-adhd` … "stop adhd mode". |

## Licenses

MIT. Derived from [mattpocock/skills](https://github.com/mattpocock/skills), [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), and [i-have-adhd](https://github.com/ayghri/i-have-adhd) — see [LICENSE](LICENSE).
