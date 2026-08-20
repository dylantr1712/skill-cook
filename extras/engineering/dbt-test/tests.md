# Good and Bad dbt Tests

> **YAML key:** these examples use `data_tests:` (dbt 1.8+). On dbt 1.7 and
> earlier the key is `tests:` — same behaviour, older name.

## Good tests

**Grain test** — the first test every model gets, declared in YAML:

```yaml
models:
  - name: fct_orders
    description: One row per order.
    columns:
      - name: order_id
        description: Primary key. One row per order.
        data_tests:
          - unique
          - not_null
```

**Referential integrity** — the foreign key resolves to a real dimension:

```yaml
      - name: customer_id
        data_tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
```

**Multi-column grain** (via `dbt_utils`):

```yaml
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns: [customer_id, order_date]
```

**Business invariant** — a singular test under `tests/` that returns failing rows:

```sql
-- tests/assert_order_total_non_negative.sql
-- Passes when it returns zero rows.
select order_id, order_total
from {{ ref('fct_orders') }}
where order_total < 0
```

Characteristics of a good test:

- Asserts the model's contract (grain, keys, invariants), not its SQL
- Survives a refactor of the joins/CTEs behind the model
- Names an expectation a human can read ("order_total is never negative")
- Expected values come from an independent source of truth

## Bad tests

**Tautological** — recomputes the expected value the way the model does:

```sql
-- BAD: reruns the model's own logic and compares it to itself.
-- Passes by construction; can never catch a bug.
with recomputed as (
    select order_id, sum(line_total) as order_total
    from {{ ref('stg_orders__line_items') }}
    group by 1
)
select f.order_id
from {{ ref('fct_orders') }} f
join recomputed r using (order_id)
where f.order_total <> r.order_total
```

If the mart's aggregation is wrong, this test is wrong the same way, so it stays green. Reconcile against an **independent** source instead (the source system's own order-total, a known-good sample), or assert a property that doesn't restate the calculation.

**Testing internals** — asserting on a private intermediate column:

```yaml
# BAD: int_orders__enriched is plumbing; no consumer depends on _raw_discount_flag.
# The test breaks on a harmless refactor of the intermediate model.
models:
  - name: int_orders__enriched
    columns:
      - name: _raw_discount_flag
        data_tests: [not_null]
```

Test the mart's contract, not the intermediate step that happens to produce it.

**Everything-shallow** — `not_null` on every column, no grain or invariant test. It looks like coverage but misses the fan-out and the business rules that actually break in production.
