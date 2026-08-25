# Findings taxonomy

Extraction is the cheapest moment to notice everything wrong with, or improvable about, a Qlik data
model: the code is already being read with full context that will never be reloaded so cheaply again.
So notice all of it — then classify it so nothing leaks into stage-1 scope.

**The register is a backlog, not a work order.** Recording an improvement is not permission to make
it. Stage 1 is a lift-and-shift; the numbers must match, including where they are currently wrong.

---

## The four classes

Every finding carries **exactly one** class. If two seem to apply, the table below breaks the tie.

### Defect — `D`
Produces wrong numbers **today**, in Qlik, before any migration.

*Stage-1 action:* **replicate exactly** so parity tests pass, record the correct behaviour, raise a
ticket for stage 2. Do not fix during migration — a "fixed" number breaks parity and nobody can tell
your fix from a migration bug.

*Examples:* a `Peek` naming a table that was never loaded; a status-flag ladder collapsing two
distinct categories into one; a `Match()` branch dead because upstream capitalisation changed.

### Migration hazard — `H`
Correct in Qlik. **Silently different on Snowflake** if translated literally.

*Stage-1 action:* **must be handled during migration**, with the decision recorded. This is the only
class that is stage-1 work.

This is the class most often missed, because it is neither a bug nor a tidy-up. It has no symptom
until after the cutover, when a number quietly moves and no one knows why.

*Examples:* text-typed dates compared as strings; Qlik's non-inflating association vs a SQL join that
multiplies; `Dual()` sort order lost; en-dash literals; `Match()` case-sensitivity where Snowflake's
collation differs; `ErrorMode=0` masking failures that dbt would surface; auto-concatenation.

### Refactor opportunity — `R`
Produces **correct** numbers. Structure is duplicated, unclear, or hostile to change.

*Stage-1 action:* **none.** Record and move on. Stage 2 work.

*Examples:* three near-identical consumer scripts; a 1,700-line `UNION` chain; an EAV shape better
modelled as columns; a misleading variable name; copy-pasted calendars that have drifted.

### Dead code — `X`
Not migrated at all.

*Stage-1 action:* exclude, and **record why** so the next person does not think it was overlooked.

*Examples:* dev/ops utilities (`fn_CopyQvds`, rollback helpers); commented-out blocks; empty
convention stubs; `TRACE` statements; `DROP TABLE`.

---

## Tie-breaks

| Situation | Class | Why |
|---|---|---|
| Wrong today **and** ugly | `D` | wrongness dominates |
| Wrong today **and** would also break on Snowflake | `D` | already wrong; the migration is not the cause |
| Correct today, breaks on Snowflake, also ugly | `H` | the hazard is the actionable part |
| Ugly, and you are not migrating it | `X` | dead code needs no refactor |
| Suspicious but unverified | `D`, marked `confidence: unverified` | never silently drop it |

Cannot decide between `D` and `H`? Ask: **would this be wrong if we never migrated?** Yes → `D`.
No → `H`.

---

## Entry format

`findings.md` is a Markdown document with one section per finding. Stable ids, never renumbered:
`<SERVICE>-<CLASS>-<NNN>` — `PBB-D-001`, `PBB-H-004`, `PBB-R-002`, `PBB-X-001`.

```markdown
### PBB-D-001 — `vMinCallDate` never updates from its default

- **Class:** Defect
- **Confidence:** unverified — needs checking against the live app
- **Evidence:** `PBB_Internal/01b_Init.qvs:44`
- **Spec ref:** `parameters.vMinCallDate`
- **Current behaviour:** `fn_GetMinCallDate` loads `Min_Call_Date_tbl` but peeks
  `'combined_dates'`, the SQL's inner alias. The peek returns null and, under `ErrorMode=0`, fails
  silently, so `vMinCallDate` retains its `'2023-12-31'` literal.
- **Impact:** the variable gates `WHERE call_date <= …` in all three consumer apps, so the blast
  radius is every number in every app.
- **Correct behaviour:** peek `Min_Call_Date_tbl`.
- **Stage 1:** replicate observed behaviour once confirmed. **Resolve the confidence flag first** —
  it changes what parity even means.
- **Stage 2 ticket:** raise against PBB Internal.
```

Required fields: **Class**, **Evidence** (`file:line`), **Current behaviour**, **Stage 1**. Everything
else as applicable. `Confidence: unverified` is mandatory on anything not proven from the source alone.

The validator checks that every finding has exactly one class from `{Defect, Migration hazard,
Refactor opportunity, Dead code}`, a well-formed id, and an `Evidence` line — and that every finding
id referenced from `model_spec.yml` exists here.

---

## Cross-referencing

Findings and spec point at each other:
- spec entries carry `finding: PBB-D-001` where implicated
- findings carry a **Spec ref** naming the entity, column, parameter or relationship

This is what makes the register usable during parity debugging: a failing test leads to a column,
which leads to any known finding about it.

---

## Rolling up for stage 2

Ids are stable and class-prefixed so `R`-class findings can be gathered across services once several
are extracted, giving a single post-migration refactor backlog. The rollup script is not built yet —
consistent ids now are what make it trivial later.

---

## What not to record

- Style preferences with no consequence (indentation, comment wording)
- Anything already stated as normal in `HDA-CONVENTIONS.md` — record the *deviation*, not the convention
- Speculation about intent with no evidence in the code

A register that lists everything is read by nobody.
