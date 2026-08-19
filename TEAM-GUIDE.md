# Claude Code Skills — Team Guide

A shared library of **34 reusable workflows** for Claude Code, tuned for our analytics-engineering stack (SQL · dbt · Snowflake) and our tooling (GitHub, Jira).

## What is a "skill"?

A skill is a saved instruction set that Claude Code loads on demand. Instead of re-explaining how we test a dbt model or how we write a ticket, you type `/dbt-test` and Claude follows the agreed process. Think of them as **team conventions Claude can actually execute** — not snippets, but workflows.

Two kinds:
- **`/slash`** — you invoke it deliberately (20 of them)
- **auto** — Claude may pull it in when the task matches (14 of them)

## Why we have this

Most Claude Code skill libraries are written for app developers — TypeScript, unit tests, package boundaries. This one has been rewritten for **our** work: dbt model design, data testing, project audits, and our Athena/Qlik → Snowflake/dbt migration. The generic engineering workflows (specs, tickets, triage, code review) were kept and pointed at GitHub/Jira.

## Install (2 minutes)

```bash
git clone <this-repo> && cd "Skill Cook"
cp -r skills/* ~/.claude/skills/
```

Restart Claude Code. Then in any repo, run `/setup-skills` **once** — it configures which issue tracker that repo uses (GitHub, Jira, or local files) and where docs live.

Lost at any point? Type `/which-skill` and it'll route you.

---

# Engineering skills (20)

### Getting started
| Skill | Summary |
|---|---|
| `/which-skill` | Router — tells you which skill fits your situation. |
| `/setup-skills` | One-time repo setup: issue tracker, triage labels, doc layout. |

### The core loop — idea to shipped
| Skill | Summary |
|---|---|
| `/grill-with-docs` | Interviews you to sharpen a vague idea, writing ADRs + glossary as you go. |
| `/to-spec` | Turns the conversation you just had into a written spec on the tracker. |
| `/to-tickets` | Splits a spec into small tickets, each declaring what blocks it. |
| `/implement` | Builds one ticket — tests first, then a review before commit. |
| `/code-review` | Reviews a branch/PR on two axes at once: our standards, and the spec. |

### dbt & data modeling
| Skill | Summary |
|---|---|
| `/dbt-model-design` | The vocabulary for model design: grain, layering, materialization, DRY. |
| `/dbt-test` | What to test and how: grain tests first, then business rules and freshness. |
| `/dbt-project-audit` | Scans the whole project for untested grains, bad layering, and cost smells → HTML report. |

### When something comes up
| Skill | Summary |
|---|---|
| `/triage` | Turns raw incoming issues into properly specified, ready-to-work tickets. |
| `/diagnosing-bugs` | For hard bugs and slow queries — builds a reliable repro before theorising. |
| `/wayfinder` | For efforts too big for one session — maps the unknowns and resolves them one by one. |

### Supporting
| Skill | Summary |
|---|---|
| `/domain-modeling` | Keeps our terminology straight; records decisions as ADRs. |
| `/research` | Sends a background agent to research a question against primary sources. |
| `/prototype` | Throwaway code to answer one design question. |
| `/resolving-merge-conflicts` | Works a merge/rebase conflict by intent, hunk by hunk. |
| `/wizard` | Generates a guided script for steps only a human can do (credentials, dashboards). |
| `/git-guardrails-claude-code` | Blocks dangerous git commands before they run. |
| `/karpathy-guidelines` | Rules that stop Claude over-engineering or changing code you didn't ask about. |

---

# Productivity skills (14)

### Thinking things through
| Skill | Summary |
|---|---|
| `/grilling` | The interview engine other skills use — stress-tests your reasoning. |
| `/grill-me` | Same interview, but saves nothing. For plans and decisions outside a repo. |
| `/loop-me` | Interviews you about workflows you want to build. *(experimental)* |

### Managing sessions
| Skill | Summary |
|---|---|
| `/handoff` | Writes a handoff doc so another session (or person) can pick up your work. |
| `/claude-handoff` | Hands off to a fresh background agent immediately. *(experimental)* |
| `/wait-what` | "That didn't make sense" — makes Claude re-explain in plain English. |

### Writing
| Skill | Summary |
|---|---|
| `/writing-for-agents` | How to write docs that agents read well (CLAUDE.md, skills, runbooks). |
| `/writing-fragments` | Mine raw ideas on a topic, no structure yet. *(experimental)* |
| `/writing-shape` | Shape rough material into an article. *(experimental)* |
| `/writing-beats` | Build a piece as a sequence of beats. *(experimental)* |

### Learning & comms
| Skill | Summary |
|---|---|
| `/teach` | Teaches you a concept across sessions, tracking what you've learned. |
| `/to-questionnaire` | Writes a questionnaire when the answer lives in someone else's head. |

### Working style
| Skill | Summary |
|---|---|
| `/i-have-adhd` | Answer-first, numbered, no filler output. Invoke at the start of a session. |
| `/task-observer` | Watches a session and logs ideas for improving these skills. |

---

## Where to start

**Your first week — three skills cover most of it:**

1. **`/dbt-test`** — next time you build a model, use it. Grain test first; it catches fan-out bugs before they reach a dashboard.
2. **`/code-review`** — run it before you open a PR. It checks the change against both our conventions and the original ticket.
3. **`/which-skill`** — when you're not sure there's a skill for what you're doing.

**Then, when the situation arises:** `/dbt-project-audit` for a health check on a project, `/diagnosing-bugs` when something's broken, `/to-tickets` when a chunk of work needs splitting.

## Notes

- Skills don't activate on their own at session start — including `/i-have-adhd`. Invoke what you want, when you want it.
- These are **ours to change**. If a skill's process is wrong for how we work, edit its `SKILL.md` — that's the point of keeping them in a repo.
- Full detail on any skill (including bundled reference files and how they chain): see [SKILLS.md](SKILLS.md).

## Credits

Adapted from three MIT-licensed sources: [mattpocock/skills](https://github.com/mattpocock/skills), [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), and [i-have-adhd](https://github.com/ayghri/i-have-adhd). Rewritten here for analytics engineering.
