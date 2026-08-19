---
name: dbt-project-audit
description: Scan a dbt project for structure, testing, and cost issues, present them as a visual HTML report, then grill through whichever fix you pick.
disable-model-invocation: true
---

# dbt Project Audit

Surface friction in a dbt project and propose **concrete fixes**: models to split, tests to add, layers to straighten, materializations to change. The aim is a project that is trustworthy (tested), navigable (layered), documented, and cheap to run.

This command is _informed_ by the project's domain model and built on a shared modeling vocabulary:

- Call the Skill tool with "dbt-model-design" for the vocabulary (**grain**, **layer**, **staging/intermediate/marts**, **materialization**, **contract**, **exposure**) and its principles (one model/one grain, layer discipline, the contract is the test surface). Use these terms exactly.
- The domain language in `CONTEXT.md` names the entities and metrics; ADRs in `docs/adr/` record decisions this audit should not re-litigate.

## Process

### 1. Explore

**Scope before you scan: YAGNI.** A refactor pays off by making future changes easier, so weight the models that changed recently or feed the most exposures. Decide *where* to look first:

- If the user named a direction (a mart, a source, a pain point), take it.
- Otherwise, use dbt's own artifacts when present — `target/manifest.json` (model configs, refs, tests, descriptions) and `target/catalog.json` (columns, table sizes) — and walk recent history (`git log --oneline -- models/`) for hot spots. If nothing stands out, widen the net.

Read the domain glossary (`CONTEXT.md`) and any ADRs in the area first. Then spawn a sub-agent to walk `models/`, the `schema.yml`/`_models.yml` files, and `dbt_project.yml`. Note friction against these signals:

- **Untested grain**: a model whose unique key has no `unique` + `not_null` test.
- **Undocumented contract**: a mart with no model/column descriptions, or no declared exposure despite BI depending on it.
- **Broken layering**: a mart reading a raw `source()` directly (skipping staging), or a staging model doing joins/business logic instead of a 1:1 clean.
- **God model**: one file doing staging + several joins + business rules + aggregation. Apply the split test: would separating it concentrate each concern in one place?
- **Grain drift / fan-out**: a join to a many-side that changes grain and risks double-counting.
- **Duplicated logic**: the same CASE/join/window in two marts that belongs in an `int_` model or a macro.
- **Cost/perf smells**: a large full-refresh `table` that should be `incremental`; a heavy `view` queried constantly that should be materialized; missing `source` freshness checks.
- **Orphans**: models with no downstream `ref` and no exposure.

### 2. Present candidates as an HTML report

Write a self-contained HTML file to the OS temp directory so nothing lands in the repo. Resolve the temp dir from `$TMPDIR`, falling back to `/tmp` (or `%TEMP%` on Windows), and write to `<tmpdir>/dbt-audit-<timestamp>.html`. Open it (`xdg-open`/`open`/`start`) and tell the user the absolute path.

The report uses **Tailwind via CDN** for layout and **Mermaid via CDN** for DAG diagrams. Each candidate gets a **before/after DAG visualisation** (the model graph now vs. after the fix). Be visual.

For each candidate, render a card with:

- **Models**: which models / sources are involved
- **Problem**: the friction — untested grain, fan-out, broken layer, cost, etc.
- **Fix**: plain-English description of what would change
- **Benefit**: in terms of trust (tests), clarity (layering/docs), or cost/runtime
- **Before / After DAG**: side-by-side Mermaid, showing the restructured graph
- **Strength**: a badge — `Strong`, `Worth exploring`, or `Speculative`

End with a **Top recommendation**: which fix to tackle first and why (weight trust and cost highest).

**Use CONTEXT.md vocabulary for the domain and the dbt-model-design vocabulary for structure.** If `CONTEXT.md` defines "Encounter," say "the `fct_encounters` grain," not "the encounters table."

**ADR conflicts**: if a candidate contradicts an ADR, surface it only when the friction is real, and mark it clearly (_"contradicts ADR-0007, but worth reopening because…"_).

Do NOT propose the final SQL yet. After the file is written, ask: "Which of these would you like to explore?"

See [HTML-REPORT.md](HTML-REPORT.md) for the full HTML scaffold, diagram patterns, and styling guidance.

### 3. Grilling loop

Once the user picks a candidate, call the Skill tool with "grilling" to walk the decision tree: the target grain, which layer each piece of logic belongs in, what the new tests assert, what the materialization should be, which exposures are affected.

Side effects happen inline as decisions crystallise; call the Skill tool with "domain-modeling" to keep the model current:

- **Naming a new model or metric after a concept not in `CONTEXT.md`?** Add the term.
- **Sharpening a fuzzy metric definition mid-conversation?** Update `CONTEXT.md` there.
- **User rejects a candidate with a load-bearing reason?** Offer an ADR: _"Want me to record this so future audits don't re-suggest it?"_ Only when the reason would actually be needed later.
- **Want to compare alternative model shapes?** Call the Skill tool with "dbt-model-design" for the grain/layer/materialization vocabulary and design it two ways before committing.
