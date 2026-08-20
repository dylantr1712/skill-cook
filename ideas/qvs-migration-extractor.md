# Skill idea: QVS to migration-context extractor

**Status:** not started. Design reviewed, not built.
**Captured:** 2026-08-20
**Blocked on:** real QVS samples. Several layout decisions cannot be made responsibly without them.

---

## The goal

A Claude Code skill that runs against our GitHub-tracked QVS transformation scripts (the pre-prod copy of the Qlik data model, version-controlled for code review before push to Qlik) and extracts everything an agent or a human would need to rebuild the same logic in dbt/Snowflake.

Output goes into a knowledge folder that later migration work loads from, instead of re-reading raw QVS every time.

**Success criteria.** The output should be usable, without re-reading raw QVS, for:

- making Phase 2 star-schema grain decisions
- building the QVS-vs-dbt parity testing
- scaffolding dbt models and tests
- feeding Confluence documentation

If a future session working on one subject area's dbt build can load just that area's extracted context and have what it needs, the skill is working.

## Context

- **Current stack:** QVS load scripts to QVDs to Qlik data model to Qlik dashboards.
- **Target:** Snowflake + dbt, in two phases.
  - Phase 1: literal 1:1 translation of existing logic.
  - Phase 2: cube-to-star/snowflake refactor, with explicit grain decisions per fact table.
- The QVS repo is the source of truth for what currently exists. It is what gets reviewed before load logic reaches production Qlik.
- Intended to run per subject area / app as we work through the migration, not as a one-off big-bang dump.

---

## Part 1: the original spec

Preserved as written, because it is the thinking that started this.

### Domain gotchas a generic "summarize this code" pass would miss

1. **Implicit associative joins.** Qlik's engine auto-links tables on identically-named fields. There is often no explicit `JOIN ON`. A field like `Date` or `ID` appearing in two unrelated tables creates an unintended link (synthetic key risk, fan-out). Output needs to surface these collisions explicitly, not just the explicit `JOIN` / `KEEP` / `CONCATENATE` statements.

2. **Variable substitution hides real logic.** `$(vStartDate)`-style references mean the actual WHERE clause or table name often is not visible in the LOAD statement, and the variable may be defined in a different included script. Extraction needs to resolve these chains and clearly flag anything it cannot resolve, rather than silently producing a partial picture.

3. **Metrics probably are not fully in the QVS.** QVS is the load layer. A lot of measure logic lives in chart-level set-analysis expressions inside the `.qvw`, which is not tracked in GitHub. Anything extracted from QVS alone must be honest about this gap rather than presenting an incomplete metric list as complete.

4. **Comments are a primary source, not noise.** Often the only surviving record of *why* logic exists (ticket refs, "changed per finance request 2019", author notes). Preserve close to verbatim next to what they annotate, do not paraphrase away.

### What the output needs to capture

- **Schema:** tables, source (Athena table / QVD), columns, source expressions, filters
- **Entities and relationships:** explicit and implicit (associative) joins, which fields drive them, flagged by collision risk
- **Grain:** per fact/table, with the evidence for the claim, not just an assertion
- **Metrics:** formula where it exists in QVS, explicitly flagged where it does not (chart-layer only)
- **Dimensions:** attributes, hierarchies, any slowly-changing behaviour
- **Business rules and context:** from conditional logic and comments, with file/line references
- **Variables:** definitions, resolved values where possible, flagged where not
- **Lineage:** source to transform steps to output, ordered
- **Existing tests and assumptions:** any reconciliation or validation logic already in the scripts, plus candidate data-quality checks a reader would infer (uniqueness, not-null, accepted values). These become dbt test candidates.
- **Open questions:** anything genuinely ambiguous that needs a human decision before Phase 2 grain/schema decisions get made

### Non-negotiable principles

- **Never let output look more certain than it is.** Every grain statement, relationship and business rule must be distinguishable as confirmed-in-code vs inferred vs needs-human-review. Silent wrong assumptions are expensive precisely because Phase 2 gets built on them.
- **Say explicitly what could not be extracted** (unresolved variables, chart-layer metrics, section access, anything outside the QVS's visibility) rather than omitting it quietly.
- **Traceable back to source.** Every extracted fact points to the file and line it came from.

---

## Part 2: design review

Assessment from the design conversation. Recommendations, not decisions.

### Split the deterministic pass from the inferred pass

The spec bundles two jobs with very different reliability:

| | Examples | Property |
| --- | --- | --- |
| **Deterministic** | resolve `$(vVar)` chains, find field-name collisions, order lineage, list tables and columns | mechanically checkable, same answer every run |
| **Inferred** | grain, business rules from comments, open questions | LLM judgment, varies run to run |

Bundled, the facts inherit the reliability of the guesses, and confidence labelling becomes a discipline the model must remember on every line. That degrades.

**Recommendation:** the deterministic pass is a Python script the skill runs, emitting a facts file. The reasoning pass reads that file and produces interpretation. Confidence then becomes *structural*: anything in the facts file is confirmed-in-code by construction, anything in the interpretation layer is inferred by construction. It also makes the parser independently testable, which answers the validation question.

### Per-app scoping is forced, not a choice

Qlik's associative model links on field names across everything loaded into one app. A collision between `Date` in two tables is only detectable with the full table set for that app. Per-file extraction cannot find them, by construction.

**Per app, always.** Bake it in rather than making it configurable. A whole-estate scan is a separate later thing, useful for finding the same field name meaning different things across apps.

### Synthetic key detection is the highest-value output

Listed in the spec under "entities and relationships", but it deserves to be the headline. It is fully deterministic:

- Two tables sharing exactly **one** field name: normal association, an implicit join
- Two tables sharing **two or more** field names: Qlik generates a synthetic key table
- Loops: circular reference, Qlik marks a table loose

Computable from field names alone. It is also what a human reviewer's eye slides over, and what silently breaks a 1:1 translation: you rebuild the join in dbt as a clean equi-join, get a different row count, and spend a day finding out why.

**Build this first.** Small script, verifiable, useful standalone.

### Refinements to the gotchas

**Variable resolution has a hard boundary: `SET` vs `LET`.** `SET x = 1+1` stores the literal string `1+1`. `LET x = 1+1` stores `2`. A parser can resolve `SET` chains and include-file chains statically. It cannot resolve anything computed at runtime (a variable assigned from a query result, a parameterised `$(vFunc(a,b))`). Document that as the boundary of the deterministic pass rather than discovering it per-file.

**The metric gap has an inverse worth capturing.** Aggregation and set analysis live in the chart layer, correct. But QVS often carries pre-calculated flags and helper fields built specifically so chart expressions stay simple. Those *are* metric logic, they are in scope, and they are easy to miss because they look like ordinary columns. Honest framing: QVS gives you the metric **inputs and any pre-aggregation**; the chart layer holds the aggregation and filtering.

**Settle the chart-layer question early.** The spec says `.qvw`, which is QlikView rather than Qlik Sense. Whether chart expressions can be extracted from those at all determines whether the metric gap is permanent or closeable. Answer before designing around it.

**Add a redaction rule.** QVS load scripts carry connection strings, credentials, and PII-revealing column names. This skill writes a knowledge folder that gets committed and later fed to other sessions. In a health data org that is a real exposure. Copy the pattern from `diagnosing-bugs`, which already redacts before showing anything.

### Compose with what already exists

**Open questions should feed `grilling`, not sit in a list.** A document full of open questions is a document nobody resolves. The extractor should hand them to the interview: `/grill-with-docs` works them in rounds with a recommended answer each, and resolutions land in `CONTEXT.md` and ADRs as they settle. Phase 2 grain decisions are exactly the "hard to reverse, surprising without context, real trade-off" test `domain-modeling` uses to decide something deserves an ADR.

**Fix the target vocabulary before writing any output.** Grain, layer, contract, source and exposure need to mean one thing each, and the extractor should emit exactly those words. This repo no longer ships a dbt modelling skill to borrow the definitions from, so they will have to come from the project's own `CONTEXT.md`, agreed via `/grill-with-docs` before extraction starts. Invent new words and someone translates twice.

### Start narrower than ten output categories

Ten categories on day one is sprawl. Ship three:

1. **Association and collision map** (deterministic, nobody has it, highest value)
2. **Resolved variables**, unresolvable ones flagged (deterministic, miserable by hand)
3. **Grain with evidence** (inferred, gates every Phase 2 decision)

Schema, columns and lineage are useful but a competent reader gets them from the script in a few minutes. The three above are impossible or miserable by hand. Prove them on one subject area, then widen.

### Validating the extraction

The split answers this:

- **Parser:** fixture tests. Hand-write a small QVS with a known synthetic key, a `SET`/`LET` pair, and an include chain, then assert the script finds them.
- **Inferred layer:** cannot be unit-tested. Validated once, by a human reviewing a subject area they already know well. A one-time calibration cost worth paying deliberately.
- **Downstream:** the real validation is parity testing. If the extracted grain is wrong, the parity test fails. Which argues for designing the output so parity tests can be generated from it.

---

## Still open

Decisions that need either a human call or real files:

- Folder and file structure, and formats per artifact type (markdown vs YAML vs other).
- Where exactly the deterministic/inferred line sits, once the real scripts show how much is statically resolvable.
- Whether chart-layer expressions are extractable from the `.qvw` files at all.
- Whether to support a whole-estate scan in addition to per-app.
- How consistent the QVS estate actually is: are variables centralised, do apps share QVDs, is there a house style.

## Next action

Run `/grill-me` on this design. There are opinions about the QVS estate that cannot be guessed at and that change the parser.

Alternatively, hand over two or three representative QVS files (redacted is fine) and build the collision detector first: small, verifiable, and useful on its own before anything else exists.
