# Skill Cook

Claude Code skills for analytics engineering, wired to GitHub, Jira, or local issue tracking.

**Six skills install by default.** That is deliberate: a skill library you can hold in your head gets used, and one with thirty entries gets ignored. Another 22 sit in `extras/` and install by name whenever you want them.

## Install

```bash
./install.sh          # macOS, Linux, Git Bash
```
```powershell
.\install.ps1         # Windows PowerShell
```

Start a new Claude Code session, then type `/grill-me`. If it autocompletes, it worked.

| Want | Command |
| --- | --- |
| The starter six | `./install.sh` |
| One project only | `./install.sh --project /path/to/repo` |
| Something from extras | `./install.sh wayfinder to-spec` |
| See every name | `./install.sh --list` |
| All 28 | `./install.sh --all` |

Re-run it any time to add more. PowerShell takes the same arguments (`-Project`, `-List`, `-All`).

## The starter six

Nothing here needs setup, and none of it writes to your repo unless you ask it to.

| Skill | What it does |
| --- | --- |
| `/grill-me` | Interviews you about a plan until every open decision is settled. The one to try first. |
| `/grill-with-docs` | Same interview, but inside a repo, writing a `CONTEXT.md` glossary and ADRs as decisions land. |
| `/wait-what` | That last answer did not land. Re-pitches it in plain English. Seven lines, zero risk, the fastest way to see what a skill is. |
| `/handoff` | Running low on context? Writes a handoff document so a fresh session can pick the work up. |
| `grilling` | The interview engine behind the two grill skills. Not typed directly. |
| `domain-modeling` | Keeps `CONTEXT.md` and ADRs honest. Reached by `/grill-with-docs`. |

The last two carry no slash of their own; the first four call them.

## Extras

Everything else lives in `extras/`, grouped for browsing. It is held back rather than removed: the spec-and-ticket flow, dbt skills, debugging discipline, and the writing tools are all there and all one command away.

See **[SKILLS.md](SKILLS.md)** for the full catalog and [worked flows](SKILLS.md#flows), and **[TEAM-GUIDE.md](TEAM-GUIDE.md)** if you are new to skills.

A few worth knowing about before you install them:

- `/to-spec`, `/to-tickets`, `/triage`, `/wayfinder` need `/setup-skills` run once in that repo first, to record which issue tracker it uses.
- `code-review` overrides Claude Code's built-in `/code-review`. The installer says so when it applies.
- `git-guardrails-claude-code` writes hooks into your Claude Code settings.
- `karpathy-guidelines` is the on-demand twin of this repo's `CLAUDE.md`. Use one or the other, never both.

## Layout

```
skills/          installed by default, one folder per skill
extras/          everything else, grouped into engineering/ and productivity/
install.sh       installer (bash)
install.ps1      installer (PowerShell)
CLAUDE.md        optional always-on coding rules
```

`skills/` is flat on purpose. **Claude Code discovers skills at exactly one level:** `<skills-dir>/<skill-name>/SKILL.md`. It does not recurse, so a folder of folders installs as nothing. `extras/` keeps its grouping only because the installer flattens on the way in.

## `CLAUDE.md`

Optional, and separate from the skills. It holds always-on rules that reduce common LLM coding mistakes: state your assumptions, keep it simple, make surgical changes, define success criteria. Unlike a skill, it costs tokens on every turn.

```bash
cp CLAUDE.md ~/.claude/CLAUDE.md          # all your projects
cp CLAUDE.md /path/to/project/CLAUDE.md   # one project
```

## Licenses

MIT. Derived from [mattpocock/skills](https://github.com/mattpocock/skills), [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), and [i-have-adhd](https://github.com/ayghri/i-have-adhd). See [LICENSE](LICENSE).
