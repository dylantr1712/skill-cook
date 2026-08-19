# Issue tracker: Jira

Issues and specs for this repo live in a Jira project. Use the
[`jira`](https://github.com/ankitpokhrel/jira-cli) CLI (`jira-cli`) for all
operations. Jira identifies issues by **key** (`PROJ-123`), not by a bare
number — always use the full key.

Run `jira init` once per machine to set the site, project, and auth
(`JIRA_API_TOKEN` in the environment). Record the project key here:

**Project key:** `PROJ` _(edit to your project's key.)_

## Conventions

- **Create an issue**: `jira issue create -t Task -s "..." -b "..."`. Use a
  heredoc or `-b -` (editor) for multi-line bodies. `-t` sets the type
  (`Task`, `Bug`, `Story`).
- **Read an issue**: `jira issue view PROJ-123 --comments 20`. Add `--plain`
  for machine-readable text.
- **List issues**: `jira issue list --jql "project = PROJ AND status = Open"
  --plain --no-headers`. Filter by label with `-l <label>`, by status with
  `-s <status>`.
- **Comment on an issue**: `jira issue comment add PROJ-123 "..."`
- **Apply / remove labels**: `jira issue edit PROJ-123 --label "..."` /
  `--label -<name>` to remove. Labels can be repeated.
- **Transition / close**: `jira issue move PROJ-123 "Done"` (the transition
  name must match the project's workflow — `Done`, `Closed`, etc.).
- **Assign**: `jira issue assign PROJ-123 $(jira me)`.

The site and project are read from `jira init` config; there is no
`git remote` inference for Jira.

## Pull requests as a triage surface

**PRs as a request surface: n/a.** Jira holds issues and specs; code review
happens on the code host (GitHub PRs), not in Jira. `/triage` operates on
Jira issues only. If you also want to triage external PRs, configure the
GitHub tracker's PR flag in addition to this file.

## When a skill says "publish to the issue tracker"

Create a Jira issue in the project above.

## When a skill says "fetch the relevant ticket"

Run `jira issue view <KEY> --comments 20`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as
tickets.

- **Map**: a single issue labelled `wayfinder-map`, holding the Notes /
  Decisions-so-far / Fog body: `jira issue create -t Task -s "..." --label
  wayfinder-map`. (On a project with Epics enabled, an Epic may hold the map
  instead; a labelled issue works on every project.)
- **Child ticket**: an issue linked to the map. Prefer a native parent/Epic
  link where the project supports it; otherwise put `Part of PROJ-<map>` at
  the top of the description. Labels: `wayfinder-<type>`
  (`research`/`prototype`/`grilling`/`task`). Once claimed, assign to the
  driving dev.
- **Blocking**: Jira's **native issue links**, the canonical, UI-visible
  representation. Add an edge with
  `jira issue link <child> <blocker> "is blocked by"` (link type names must
  match the site's configured link types — commonly `Blocks` / `is blocked
  by`). Where issue links are disabled, fall back to a
  `Blocked by: PROJ-<n>, PROJ-<n>` line at the top of the description. A
  ticket is unblocked when every blocker is in a Done status.
- **Frontier query**: `jira issue list --jql "project = PROJ AND labels =
  wayfinder-map ..."` scoped to the map's children; drop any with an open
  blocker (a native `is blocked by` link to an unresolved issue, or an open
  key in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `jira issue assign <KEY> $(jira me)`, the session's first
  write.
- **Resolve**: `jira issue comment add <KEY> "<answer>"`, then
  `jira issue move <KEY> "Done"`, then append a context pointer to the map's
  Decisions-so-far.
