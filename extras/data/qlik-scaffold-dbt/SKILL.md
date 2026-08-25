---
name: qlik-scaffold-dbt
description: "Generate dbt sources, models and tests from an extraction bundle's model_spec.yml, preserving lift-and-shift parity."
disable-model-invocation: true
---

# Scaffold dbt from an extraction bundle

Consumes a validated extraction bundle and produces the dbt layer for a **stage-1 lift-and-shift**:
same numbers, including the ones that are currently wrong.

**Status: intentionally thin.** This skill will harden once a validated `<repo>/extraction/<GENERATOR>/model_spec.yml` exists and
the target Snowflake/dbt project conventions are settled. Filling it in before then would bake
guesswork into a template. What follows is the contract and the traps — enough to work from, and the
place to record decisions as they are made.

**Prerequisite:** `validate_spec.py` exits 0 on the bundle. Do not scaffold from a failing spec; the
holes it reports are exactly the ones that become wrong models.

## Reference

- `../qlik-extract-logic/SPEC-SCHEMA.md` — the input contract
- `../qlik-extract-logic/QVS-LANGUAGE.md` — the construct → SQL translation table, and the
  **semantic traps** section, which is the substance of this job
- `../qlik-extract-logic/PARITY-TESTING.md` — the tests to generate

---

## Before starting, settle these with the user

The answers shape everything and are not derivable from the spec:

1. **Project layout** — model directory structure, naming (`stg_` / `int_` / `fct_` / `dim_`),
   whether silver and gold are separate schemas.
2. **Ingestion** — how Athena sources land in Snowflake. This is a prerequisite, not part of this
   skill. Note that `maintained_by: human` sources are SharePoint spreadsheets and need an ingestion
   answer of their own.
3. **Materialisation** — which entities are tables, views or incremental.
4. **Where parity assertions live** — dbt tests, a reconciliation model, or an external harness.

---

## Mapping

| Spec | dbt |
|---|---|
| `sources[]` | `sources.yml` entries; `external_service` sources are a cross-project `ref` or a source in that service's schema |
| `entities[layer: silver]` | staging/intermediate models, one per QVD, materialised per the entity's `filters` |
| `entities[layer: gold]` | mart models, one per app table |
| `columns[].expression` | the SELECT expression, translated per `QVS-LANGUAGE.md` |
| `columns[].source` | the `ref()` / `source()` it selects from |
| `relationships[]` | explicit `JOIN`s — with `fan_out: true` handled, never joined naively |
| `dimensions[]` | derived columns, or conformed dimension models where shared |
| `metrics.recovered[]` | metric definitions or gold-layer measures |
| `metrics.todo[]` | **not implementable** — stop and run `qlik-export-metrics` |
| `parameters[]` | `vars:` in `dbt_project.yml` |
| `calendar` | a date-spine model |
| `dead_code[]` | not migrated |

---

## The traps, in priority order

**1. Fan-out.** Any relationship with `fan_out: true` must not be a plain join. Qlik's associative
engine does not inflate counts; a SQL join does. Use a semi-join, pre-aggregate, or
`COUNT(DISTINCT …)`, and generate the parity test that proves the base count did not move.

**2. Defect-class findings are replicated, not fixed.** Read `findings.md` before writing SQL. A
Defect entry means reproduce the wrong behaviour and reference the finding id in a comment, so the
next reader knows it is deliberate.

**3. Migration hazards are the actual work.** Each `H` finding needs an explicit handling decision
recorded in the model. Text-typed dates need real casts. `Dual()` columns need label **and** sort-key
columns. En-dash literals must survive copy-paste.

**4. `Exists()` and `Peek()` were order-dependent.** The spec names the intended upstream; pin it
explicitly rather than relying on dbt's DAG order to reproduce Qlik's accidental one.

**5. Fail loudly.** The source ran `ErrorMode=0`, so failures were silent. Do not reproduce that.
Parity applies to numbers, not to error handling.

---

## Generate

Models per the mapping, plus tests: `unique`/`not_null` on declared grain keys, `relationships` tests
per relationship, `accepted_values` from `dimensions[].values`, and the tier-1 and tier-2 parity
assertions from `parity_tests.md`.

*Done when:* `dbt build` succeeds, every spec entity has a model, every `todo` metric is listed as an
unimplemented gap, and the tier-1/tier-2 tests pass. Tier-3 measure parity needs Qlik figures at the
recorded freeze point.

## Record what you decide

Every convention settled here belongs in this file, so the next service inherits it instead of
re-deciding. That is the difference between a scaffold skill and a one-off.
