---
name: dbt-model-design
description: Vocabulary and principles for dbt model design — grain, layering (staging/intermediate/marts), materialization, DRY. Use when designing or refactoring a model, deciding where logic belongs, choosing a materialization, or when another skill needs the dbt vocabulary.
---

# dbt Model Design

Design dbt models as **deep transformations behind a clean, tested contract**: a lot of business logic hidden behind a single well-defined grain and a documented set of columns. The aim is leverage for downstream consumers, locality for maintainers, and testability at every layer. Use this language and these principles wherever models are being designed or restructured.

## Glossary

Use these terms exactly; consistent language is the point.

**Model**: one `.sql` file = one `SELECT` = one relation. Scale-agnostic (a staging view or a wide mart).

**Grain**: the one thing a row represents, identified by a unique key (`order_id`, or `customer_id + date`). Every model has exactly **one** grain. If you can't name it in a sentence, the model is doing too much.

**Layer**: where a model sits in the DAG.
- **staging** (`stg_`): 1:1 with a source table. Rename, cast, light cleaning only — no joins, no business logic. Usually a view or ephemeral.
- **intermediate** (`int_`): reusable building blocks — the joins and business logic that more than one mart needs. Not exposed to BI.
- **marts** (`fct_`/`dim_`): business-facing, documented, tested. Usually a table or incremental.

**Source**: a raw upstream table, declared in YAML and referenced with `source()`. Freshness is checked here.

**ref / source**: the only ways a model reads another relation. Never hardcode a database.schema.table — `ref()`/`source()` build the DAG and let dbt manage dependencies.

**Materialization**: how dbt persists the model — `view`, `table`, `incremental`, `ephemeral`. A design decision, not a default.

**Contract**: the grain + column names/types + tests a downstream consumer depends on. The SQL behind it can change freely; the contract shouldn't.

**Exposure**: a declared downstream consumer (a Qlik/BI dashboard, a report) that depends on a mart. Makes the blast radius of a change visible.

## Deep vs shallow models

A **deep** model hides real transformation behind a simple grain:

```
sources → stg_* (1:1 clean) → int_* (reusable logic) → fct_/dim_* (business contract) → exposures
                                                          ▲ small, documented, tested surface
                                                          │ lots of joins/aggregation hidden inside
```

**Shallow / anti-pattern models** (avoid):
- **Pass-through**: a model that only renames and forwards another model (that's what staging is for; don't add a second one).
- **God model**: 400 lines doing staging + five joins + business rules + aggregation in one file. Split it along the layers.
- **Grain-drift**: a join to a many-side silently changes the grain and double-counts. Know your grain before every join.

## Principles

- **One model, one grain, one responsibility.** State the grain in a comment/description and enforce it (`unique` + `not_null` on the key). See `dbt-test`.
- **Read upstream only through `ref()`/`source()`.** Never rebuild logic that a staging or intermediate model already owns; reference it.
- **DRY: repeated logic becomes a macro or an intermediate model.** If the same CASE/join appears in two marts, lift it into `int_` or a macro.
- **Choose materialization deliberately:**
  | Materialization | Use when |
  |---|---|
  | `view` | cheap transforms, always-fresh, low query volume |
  | `table` | heavy transforms queried often by BI |
  | `incremental` | large append-mostly facts where full refresh is too slow/costly |
  | `ephemeral` | staging glue that shouldn't exist as its own object |
- **The contract is the test surface.** Downstream consumers cross the grain + columns, not your SQL. If a consumer reaches "past" the mart into an `int_` model, the seam is in the wrong place — expose what they need in the mart.
- **Layer discipline is the seam.** A mart reads `int_`/`stg_`, never a raw source directly; staging is the single place a source is touched. This keeps source changes local to one staging model.

## Naming

- `stg_<source>__<entity>` — e.g. `stg_athena__orders`
- `int_<entity>__<verb>` — e.g. `int_orders__joined_to_customers`
- `fct_<process>` / `dim_<entity>` — e.g. `fct_orders`, `dim_customers`

Consistent prefixes make the DAG readable and let selectors (`dbt build -s staging`) work by convention.
