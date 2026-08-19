# Environments

Load for setup/activation questions, or when there is no persistent
filesystem. Covers reliable activation, compaction behaviour, handoff-doc
mode for storage-less environments, and where the user-facing docs live.

## Recommended Activation Setup

Description-level matching alone is not enforceable — a skill's description
influences selection but doesn't guarantee the skill loads at session start.
Pair it with one of these:

1. **CLAUDE.md instruction (recommended, portable).** Add to the project or
   user `CLAUDE.md`:

   > At the start of any task-oriented session where you will use tools to
   > produce deliverables, invoke the `task-observer` skill first, and keep
   > its observation discipline active for the whole session.

2. **Session-start hook (strongest).** If the harness supports it (e.g.
   Claude Code `SessionStart` hooks in `.claude/settings.json`), emit a
   reminder or auto-invoke the skill at session start. Harness-executed,
   so it doesn't depend on the model remembering.

3. **Both.** The hook enforces; the CLAUDE.md line documents intent and
   covers harnesses without hooks.

At session start (SKILL.md step 4), if none of the above is present, suggest
adding one — once per session, briefly. Skip if already configured.

## Workspace anchoring

The observation log must live on a **stable** path that outlives a session
(`[workspace folder]/skill-observations/log.md`), not in an ephemeral
checkout. If the cwd is under `.claude/worktrees/`, a temporary clone, or
any teardown-on-exit path, re-anchor on the stable project identity (e.g.
`~/.claude/projects/<project-id>/`) before writing. State written to an
ephemeral checkout is lost at teardown, taking the log with it.

## Compaction behaviour

Long sessions get compacted; the running "current observation number" and
any un-flushed observations held in working memory can be lost across a
compaction boundary. Defences:

- **Flush early and often.** The whole point of logging silently and
  immediately (SKILL.md → How to Log) is that the file, not memory, holds
  state. Don't carry observations across a compaction unwritten.
- **Never trust a remembered counter.** After any compaction, re-derive the
  highest observation number from the live log before appending (SKILL.md →
  Numbering discipline).
- **Re-read before write-back.** Compaction can hide that a parallel session
  advanced the log; the live-read-and-merge rule (SKILL.md → Log-write
  safety) covers this.

## Handoff-doc mode (no filesystem)

Some environments have no persistent storage (ephemeral sandboxes, chat-only
surfaces). There, the log can't live on disk. Fall back to **handoff-doc
mode**:

- Accumulate observations in a single structured handoff document kept in
  the conversation (same `### Observation N:` format, same Status lines).
- At session end, surface the full handoff block and ask the user to paste
  it into their persistent log, or hand it to the next session as context.
- Numbering restarts from what the user's canonical log reports; if unknown,
  use provisional IDs (`### Observation P1:`) and flag that they need
  renumbering on merge.
- All Log-write safety concerns about concurrent erase don't apply (no
  shared file), but the merge-on-paste step does — tell the user to append,
  never overwrite, their canonical log.

## User-facing docs

Point users who want the full picture to:

- This skill's `SKILL.md` (the operating rules).
- `references/weekly-review.md` (how reviews run and get approved).
- `references/skill-authoring.md` (taxonomy, confidentiality, authoring).
- The canonical source repository named in the skill's attribution for the
  complete, up-to-date bundle.
