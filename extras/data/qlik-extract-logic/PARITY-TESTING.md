# Parity test specification

Stage 1 is a lift-and-shift, so the acceptance question is narrow: **does Snowflake produce the same
numbers as Qlik?** `parity_tests.md` is the document that makes that answerable rather than arguable.

Write it during extraction, while the grain and fan-out of every entity is fresh. It is a
specification, not a test run — the tests execute later, once dbt models exist.

---

## Principles

**Compare at the grain the business reads, not just at row-count level.** Matching row counts with a
mis-joined dimension still gives wrong dashboards. Every test names a grain and a set of slices.

**Zero tolerance on counts, stated tolerance on rates.** Row counts, distinct keys and integer
measures must match exactly. Rates and averages carry an explicit tolerance with a reason (floating
point, or a known rounding difference), never a vague "approximately".

**Slice along the dimensions that actually appear in the reports.** For this estate: month, financial
year, state, region type (Metro/Rural), category, and audience/app. A total that matches while one
state is wrong and another compensates is a false pass — so always test sliced, not only in aggregate.

**Test the known-wrong things too.** Defect-class findings are replicated in stage 1, so a parity test
must assert the *current* (wrong) value. Reference the finding id in the test so nobody later "fixes"
it and reports a regression.

**Every test names its source of truth.** A Qlik figure, and how to obtain it: an app, a sheet, a
straight-table export, or a QVD row count. A test whose expected value cannot be reproduced is not a
test.

---

## Test tiers

### Tier 1 — structural
Cheapest, run first, catch the gross errors.

| Test | Assertion |
|---|---|
| Entity row count | per silver entity, Snowflake count = QVD count, exactly |
| Grain uniqueness | the declared `grain` key set is unique (or documented as not) |
| Distinct key count | per association key, distinct values match |
| Column presence | every spec column exists, correctly typed |
| Null rate | per column, null/blank proportion matches within 0.1pp |

Grain uniqueness is worth running even where the spec says the grain is not unique — it documents the
actual duplication rate, which is often the thing nobody knew.

### Tier 2 — dimensional
Proves joins did not inflate and buckets did not shift.

| Test | Assertion |
|---|---|
| Fan-out control | count of the base fact **after** joining each dimension = count before |
| Dimension value sets | distinct values of each derived dimension match exactly, including `'Not recorded'` |
| Bucket distribution | row count per bucket value matches, per month |
| Sort order | `Dual()`-derived label/sort pairs order identically |
| Referential | every key value in the fact exists in the dimension, at the same match rate |

The fan-out control test is the important one: it is the direct check on the Qlik-association-vs-SQL-join
trap, and the reason `fan_out_risk` is a required spec field.

### Tier 3 — measure
The numbers people actually look at.

| Test | Assertion |
|---|---|
| Measure total | per measure, grand total matches (exact for counts, tolerance for rates) |
| Measure by month | per measure per month, across the full retained history |
| Measure by slice | per measure per state, region type, category |
| Threshold boundaries | rows at exactly the SLA boundary classify identically |
| Period-over-period | FY/quarter/month aggregations match, including FYTD flags |

Boundary tests matter because the estate encodes thresholds as raw comparisons (`<= 120` seconds,
`> 30` seconds). An off-by-one in the operator moves only the rows sitting exactly on the boundary,
which a total can hide.

Measures still in `metrics.todo` cannot be tested. List them here as **untestable pending
`qlik-export-metrics`**, so the gap is visible in the parity report rather than silently absent.

### Tier 4 — temporal
Cheap to forget, expensive to get wrong.

| Test | Assertion |
|---|---|
| Calendar spine | date range and row count match |
| FY assignment | every date maps to the same FY (check 30 Jun / 1 Jul explicitly) |
| Week numbering | week number and `WeekCommencing` match, given Sunday-start and broken weeks |
| Incremental watermark | the high-water mark selects the same row set |
| Timezone | timestamps agree, if any conversion is genuinely applied |

Always test 30 June and 1 July explicitly. FY boundary handling is the most common silent break.

---

## Entry format

```markdown
### PT-032 — Calls answered within SL, by month

- **Tier:** 3 (measure)
- **Entity / measure:** `call_data.answered_within_sl`
- **Grain:** month
- **Slices:** none (see PT-033 for by-state)
- **Source of truth:** PBB Internal app, "Service Level" sheet, exported straight table
- **Expected:** exact match, all months from 2024-01
- **Tolerance:** 0
- **Notes:** boundary case — `timetoanswer` exactly 120 counts as within SL (see PT-034)
- **Findings:** none
```

Ids are stable: `PT-NNN`. Where a test asserts known-wrong behaviour, name the finding:
`**Findings:** asserts current behaviour of PBB-D-002`.

---

## Reconciliation harness

The document also states *how* the comparison runs, so it is repeatable rather than a one-off
spreadsheet:

- **Qlik side:** how each expected figure is obtained (app, sheet, export, or QVD read). Prefer QVD
  row counts and straight-table exports over reading numbers off charts.
- **Snowflake side:** the query or dbt test that produces the comparable figure.
- **Comparison:** where results land, and what the pass/fail report looks like.
- **Freeze point:** parity must be measured against a **fixed** Qlik reload, since both sides move.
  Name the reload timestamp; without it, differences cannot be attributed.

The freeze point is the part most often skipped and the one that wastes the most time.

---

## What is not a parity test

- Performance comparison — real, but not parity
- Anything asserting the *correct* answer where stage 1 replicates a defect
- Tests on measures whose Qlik expression is unknown; those are gaps, and must be listed as gaps
