---
name: dbt-test
description: Data testing strategy for dbt — grain tests, generic and singular tests, unit tests, and source freshness. Use when the user wants to test a model, build trust in a transformation test-first, add data quality checks, or decide what to assert.
---

# dbt Testing

Testing in dbt is the **red → green loop for data**: write a test that encodes an expectation, watch it fail on the gap, then make the model (or the upstream data) satisfy it. This skill is the reference that makes those tests worth keeping: what a good test is, where tests go, the test types, the anti-patterns, and the rules of the loop.

When exploring the project, read `CONTEXT.md` (if it exists) so test names and column vocabulary match the domain language, and respect ADRs in the area you're touching. For the grain/layer/contract vocabulary, call the Skill tool with "dbt-model-design".

## What a good test is

A good test asserts an expectation through the model's **contract** — its grain, its columns, its referential integrity, its business rules — not through the SQL internals. The SQL can be rewritten entirely; the test shouldn't care. "`fct_orders` is unique by `order_id`" tells you exactly what the model guarantees, and it survives any refactor of the joins behind it.

See [tests.md](tests.md) for good/bad examples and [unit-tests.md](unit-tests.md) for unit-testing transformation logic.

## The grain is where testing starts

Every model has one **grain** (the unique key). **The first test any model gets is `unique` + `not_null` on that key.** A model with no grain test is untrusted no matter how many other checks it has — a silent fan-out doubles rows and nothing catches it.

**Agree the critical expectations up front.** You can't test every column. Before writing tests, name the ones that matter — the grain, the foreign keys, the business invariants, the complex logic — and put the effort there instead of on every field.

## Test types

- **Generic tests** (built-in): `unique`, `not_null`, `accepted_values`, `relationships`. Declared in YAML on a column. The grain test and referential integrity live here.
- **Package tests** (`dbt_utils`, `dbt_expectations`): `unique_combination_of_columns` (multi-column grain), `expression_is_true`, `accepted_range`, `not_null_proportion`, etc. Reach for these before writing a singular test.
- **Singular tests**: a `.sql` file under `tests/` that `SELECT`s the **failing rows**; the test passes when it returns zero. For business rules that don't fit a generic test ("revenue is never negative", "discharge_date >= admit_date").
- **Unit tests** (dbt 1.8+): mock inputs and an expected output, to test complex transformation logic or a macro in isolation from real data. See [unit-tests.md](unit-tests.md).
- **Source freshness**: `dbt source freshness` on raw sources — catches stale upstream data before a model silently serves yesterday's numbers.

## Anti-patterns

- **Tautological**: the test recomputes the expected value the way the model does — a singular test that reruns the model's own SQL and compares it to itself. It passes by construction and can never disagree with the code. Expected values must come from an **independent** source: a known-good literal, a reconciliation against the source system, a hand-worked example.
- **No grain test**: the single most common gap. Every model, every grain, `unique` + `not_null` — first.
- **Testing internals**: asserting on an `int_` model's private column that no consumer depends on. Test the mart's contract, not the plumbing.
- **Everything-shallow**: a `not_null` on all forty columns and no business-rule test. Coverage of the trivial, blind to the grain and the invariants that actually break.

## Rules of the loop

- **Grain test first**, before any transformation logic is trusted.
- **One expectation at a time.** Add a test, run it, watch it fail on the real gap (bad data, or a wrong transformation), then fix — don't write forty tests against imagined behaviour.
- **Run with `dbt build`** (runs models and their tests in DAG order) or `dbt test -s <model>` for a single model. In CI, `dbt build` is the gate.
- **A failing test is a finding, not a nuisance.** Decide whether the fix belongs in the model (wrong logic) or upstream (bad source data) — never delete the test to go green.
