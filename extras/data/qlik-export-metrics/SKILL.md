---
name: qlik-export-metrics
description: "Pull master items and chart expressions out of Qlik QVF apps and fold them into an existing model_spec.yml, closing the metrics.todo gap."
disable-model-invocation: true
---

# Export Qlik app metrics

`qlik-extract-logic` can only recover what is in the `.qvs` scripts. Measure **expressions** live
inside the QVF app as master items and chart expressions, which are not in git. That gap is recorded
as `metrics.todo` entries in `model_spec.yml`. This skill closes it.

Needs Qlik app access, so it usually runs separately — often later, often by someone else.

**Prerequisite:** an extraction bundle with `model_spec.yml` and `metrics_todo.md`. If there is none,
run `qlik-extract-logic` first.

## Reference

Shared reference lives with the extraction skill; read by relative path, no invocation needed:

- `../qlik-extract-logic/SPEC-SCHEMA.md` — the `metrics` contract you are writing into
- `../qlik-extract-logic/QVS-LANGUAGE.md` — expression semantics, and the set-analysis notes
- `../qlik-extract-logic/HDA-CONVENTIONS.md` — estate conventions; append anything new

---

## Process

### 1. Establish access and read the gap

Read `metrics_todo.md` and the `metrics.todo` list in `model_spec.yml` — that is the target list.
Get the app ids from `service_profile.yml`.

Confirm with the user which tool they have working, rather than assuming:

| Tool | Notes |
|---|---|
| `qlik-cli` | official; `qlik app object ls --app <id>` then `qlik app object get` |
| `corectl` | `corectl app objects`, `corectl app object properties`; needs an engine URL |
| Qlik Engine JSON-RPC | websocket; last resort, but scriptable against Qlik Sense on-prem |
| Manual export | the app's master items pane, or an exported sheet; fine for a short list |

On-prem (`analytics.corp.healthdirect.org.au`) and Qlik Cloud (`healthdirect.ap.qlikcloud.com`) need
different auth. The app may exist on both with **different content** — establish which is
authoritative before exporting.

### 2. Export

Pull, for each app:

- **master measures** — name, label, definition, number format, tags
- **master dimensions** — name, field(s), whether drill-down
- **chart expressions** — any measure defined inline on a sheet rather than as a master item
- **variables** defined in the app rather than the load script

Inline chart expressions matter as much as master items: an important measure is often defined once
on one sheet and never promoted.

*Done when:* every `metrics.todo` name is either matched to a definition or confirmed absent.

### 3. Fold into the spec

For each recovered measure, move the entry from `metrics.todo` to `metrics.recovered` with:

- `expression` **verbatim**, including set analysis
- `grain` — what one row of the result means
- `business_rule` — the rule in plain English
- `thresholds` — any number embedded in the expression

**Decompose the set analysis.** `{<call_rank={1}>}` is a dedup rule; `{<genesys_data_type={0}>}` is a
source filter; `{$<...>}` inherits selection state. Each becomes a `WHERE` or a window in dbt, and
each is business logic that must be recorded, not just copied. Selection-state inheritance has no dbt
equivalent and must be resolved into an explicit filter — record it as a **migration hazard** finding.

Add a finding for anything you meet along the way: a measure contradicting its label, two master
items computing the same thing differently, a measure depending on a field the spec does not have.

*Done when:* `metrics.todo` contains only genuinely-absent measures, each with a note saying so.

### 4. Validate

```
python ../qlik-extract-logic/scripts/validate_spec.py <repo>/extraction/<GENERATOR>
```

Must exit 0. Then set `migration.metrics_exported: true` in `service_profile.yml`.

Update `parity_tests.md`: measures previously "untestable pending export" now need real tier-3 tests.

---

## Rules

**Verbatim, including set analysis.** Do not simplify, do not reorder, do not drop a modifier that
looks redundant.

**A measure you cannot find stays a gap.** Never reconstruct an expression from its label. Record it
absent and say where you looked.

**Labels lie.** Compare each definition against its label and raise a finding on any mismatch. The
label is what the business believes the number means.
