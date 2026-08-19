# Weekly Review Procedure

Loaded when a review triggers (scheduled/autonomous run, or the 7-day
fallback with OPEN observations) or when the user explicitly asks for a
review. Never run unprompted in an interactive session — offer it in one
line and proceed with the user's task unless they opt in.

## Trigger conditions

- **Scheduled / autonomous:** a cron or session-start automation fired the
  review. Run it without asking.
- **7-day fallback:** `last-review-date.txt` reads `never` or a date older
  than 7 days AND there is at least one OPEN observation. Offer once, run
  only if the user opts in.

If neither holds, don't review.

## Procedure

1. **Snapshot & back up.** Copy `log.md` to a pre-review backup before any
   mutation (see SKILL.md → Log-write safety). Archival and status edits
   below are the highest-risk writes the log takes.

2. **Read the whole live log.** Load every OPEN observation. Group them by
   target: existing-skill improvements grouped per skill, simplifications
   per skill, and new-skill candidates listed separately.

3. **Triage each OPEN observation** into one outcome:
   - **ACTION** — a concrete skill change is warranted now.
   - **DECLINE** — not worth pursuing; record why.
   - **DEFER** — keep OPEN, needs more evidence or user input.
   Cluster related observations so one skill edit can resolve several.

4. **Confirm with the user (approval policy).** Present the grouped triage:
   one line per item (title, target skill, proposed action, suggested
   type). The user approves which items to action. Do not apply substantial
   changes or create new skills without explicit approval. Small, additive,
   low-risk fixes may be noted as "will apply directly" but still shown.

5. **Apply approved changes.** Load `references/skill-authoring.md` before
   editing or creating any skill and follow its editing/staging rules.
   - Additive fixes (a new rule, a clarification, a factual correction) →
     edit the live skill file directly.
   - Substantial changes (restructuring, new capability, changed
     methodology) and all new skills → stage per skill-authoring.
   - A principle that generalises across skills → propose it for
     `cross-cutting-principles.md`.

6. **Resolve statuses (with dates).** For every actioned/declined entry,
   set the Status line to `ACTIONED (YYYY-MM-DD) — [what was done]` or
   `DECLINED (YYYY-MM-DD) — [reason]`. Use strictly line-anchored edits;
   never a DOTALL pattern across the multi-entry file. Verify the
   `### Observation` header count is unchanged after status-only edits.

7. **Archive.** Move entries resolved *before today* to
   `skill-observations/archive/log-[YYYY-MM-DD].md`, preserving the log
   header. Entries resolved today stay in the active log until tomorrow.
   Re-read the live log immediately before the write-back and merge any
   entries appended since the snapshot; verify the post-write header count
   equals the live pre-write count minus exactly the archived count.

8. **Record the review date.** Write today's date into
   `skill-observations/last-review-date.txt` (this is the only step that
   writes a real date there — a date means a review actually ran).

9. **Verify survival.** Grep the log for every entry this review touched or
   this session wrote; confirm each still exists exactly once. Re-append
   any silently lost to a concurrent write-back, and log a meta-observation.

## Delivery / staging of updated skills

- **Live-file environments (Claude Code, local `.claude/skills`):** applied
  edits land directly in the skill file. Show the user a diff summary.
- **Staged delivery (managed/shared environments):** write the updated
  skill to a staging path and hand the file to the user rather than
  overwriting the installed skill in place. The user promotes it.
- Either way: one skill file mutated at a time, backed up, verified.

## Approval policy summary

| Change class | Needs explicit approval? |
|---|---|
| Small additive fix (rule, clarification, factual fix) | No — but show it |
| Restructuring / changed methodology | Yes |
| New capability added to a skill | Yes |
| New skill creation | Yes |
| Cross-cutting principle promotion | Yes |
| Declining/deferring an observation | Confirm in the triage summary |
