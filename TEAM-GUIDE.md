# Claude Code Skills: Team Guide

Six skills, about ten minutes to get going. No prior experience with skills needed.

## What is a skill?

A skill is a saved instruction set that Claude Code loads on demand. Instead of re-explaining how you want something done, you type `/grill-me` and Claude follows an agreed process.

Think of them as team conventions Claude can actually execute. Not snippets, workflows.

You invoke these by typing them. Claude does not fire them at you unannounced.

## Install

```bash
git clone <this-repo> && cd "Skill Cook"
./install.sh                    # macOS, Linux, Git Bash
```
```powershell
.\install.ps1                   # Windows PowerShell
```

Start a new Claude Code session and type `/grill-me`. If it autocompletes, you are done.

That installs six skills. Nothing else changes, nothing needs configuring, and none of them touch your repo unless you ask.

## Try this first

Pick a piece of work you are about to start and have not fully thought through. Then:

```
/grill-me
```

Claude will interview you about it, one round of numbered questions at a time, each with its recommended answer. Keep going until it runs out of questions.

Most people find it surfaces two or three decisions they had not noticed they were making. That is the whole point: the expensive mistake is not bad code, it is building the right thing badly understood.

If any answer Claude gives you does not land, type `/wait-what` and it will re-pitch in plain English.

## The six

| Skill | Reach for it when |
| --- | --- |
| `/grill-me` | You are about to build something and the plan is still fuzzy. Works anywhere, saves nothing. |
| `/grill-with-docs` | Same, but inside a repo. It also builds a `CONTEXT.md` glossary of our terms and records decisions as ADRs, so the next session starts informed. |
| `/wait-what` | An answer did not land. Stops everything and re-pitches it plainly. |
| `/handoff` | The session is getting long or you are stopping for the day. Writes a handoff doc a fresh session can resume from. |

Two more install alongside these but are not typed directly: `grilling` (the interview engine) and `domain-modeling` (keeps the glossary honest). The four above call them.

### Why the glossary matters

`/grill-with-docs` writes a `CONTEXT.md`: a short glossary of the terms a project actually uses. It sounds like busywork, and it is the highest-leverage thing here.

Without it, you spend a sentence every session explaining what a term means. With it, you say the word. Claude also starts naming models, columns and tests consistently, because it has a vocabulary to be consistent with.

## When you want more

Another 22 skills ship in `extras/`, held back so this page stays readable. They cover the spec-and-ticket workflow, dbt model design and testing, a debugging discipline, and more.

```bash
./install.sh --list             # see every name
./install.sh diagnosing-bugs    # add one
```

Worth knowing before you reach for them:

- `/to-spec`, `/to-tickets`, `/triage` and `/wayfinder` need `/setup-skills` run once in that repo first, so they know whether we are tracking work in GitHub, Jira, or local files.
- `code-review` replaces Claude Code's built-in `/code-review`. The built-in is good; only take ours if you want the two-axis version.
- `git-guardrails-claude-code` changes your Claude Code settings to block dangerous git commands.

The full catalog, with what each one does and how they chain, is in [SKILLS.md](SKILLS.md).

## Optional: always-on coding rules

`CLAUDE.md` in this repo holds four rules that reduce common Claude mistakes: state assumptions instead of guessing, keep it simple, make surgical changes, define success criteria before starting.

```bash
cp CLAUDE.md ~/.claude/CLAUDE.md
```

Unlike a skill, this applies to every turn of every session, and costs tokens accordingly. Try the skills first and add this later if you want it.

## If something does not work

**Typed a slash command and nothing happened?** Start a new session; skills load at startup. If it still does not autocomplete, re-run the installer and check it reports six skills.

**Not sure which to use?** There are only four you type. If in doubt, `/grill-me`.
