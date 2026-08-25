# `model_spec.yml` — the contract

One file per generator, at `<repo>/extraction/<generator>/model_spec.yml`. Identical shape for every service, so `qlik-scaffold-dbt` and the parity
tooling can consume it without configuration. `scripts/validate_spec.py` enforces everything marked
**required**; it is the completion criterion for an extraction, not a formality.

`spec_version: 1`

---

## Top-level keys

```yaml
spec_version: 1                 # required, integer
service: PBB                    # required, the service code
generator: PBB_DataModel        # required, the generator app this bundle covers;
                                # must equal the folder name under extraction/
extracted_at: 2026-08-24        # required, ISO date
source_commit: c0097de          # required, git SHA of the repo as read
scope:                          # required - see below
  layers: [silver]
  deferred_note: "Gold outstanding; tracked in README.md."
apps:                           # required, one entry per Qlik app
  - name: MAC_DataModel         # the app's name, as the Qlik tenant knows it
    layer: silver
    app_id: c5677ec2-8bb4-4f23-8206-92ca8466df41
    directory: MAC_DataModel_QLIK   # the repo folder holding its .qvs files
    role: "Athena and SharePoint to QVD generator"
subjects:       [...]           # business subject areas; groups the entities
sources:        [...]           # required
entities:       [...]           # required
relationships:  [...]           # required (may be empty only if genuinely none)
dimensions:     [...]
metrics:        {...}           # required
parameters:     [...]           # required
calendar:       {...}           # required
dead_code:      [...]           # artefacts deliberately not migrated
out_of_scope:   [...]           # live artefacts owned by another bundle
lineage_notes:  [...]
```

> **Three fields name an app, and they are not interchangeable.** `generator` is the bundle folder
> name; `apps[].name` is the app as the Qlik tenant knows it; `entities[].app` is the **repo
> directory** holding the script. They coincide in some services and not in others — MAC's folders
> carry a `_QLIK` suffix, so the same app is `MAC_DataModel` in the first two and
> `MAC_DataModel_QLIK` in the third. Declare `apps[].directory` and the validator will hold them
> together.

> **YAML 1.1 trap.** PyYAML parses bare `on`, `off`, `yes`, `no`, `y` and `n` as
> **booleans**, so a key written `on:` becomes the key `True` and vanishes from the
> parsed mapping, silently. That is why the relationship key is `join_keys`, not `on`.
> The same applies to *values*: `fan_out_risk: no` parses as `False`, not the string
> `"no"` — write prose (`"none - base fact"`), and the validator will reject a
> non-string. Quote any value that could read as a boolean.

---

## `scope`

**Incompleteness must be declared, not inferred.** A silver-only extraction is a legitimate staged
delivery, but the spec has to say so — otherwise a bundle covering none of the gold layer passes the
gate on warnings alone, which is the exact false PASS the gate exists to prevent.

```yaml
scope:
  layers: [silver]              # required: which layers this spec claims to cover
  deferred_note: "Gold layer (3 consumer apps) outstanding - see README.md."
```

The validator then enforces, per declaration:

| Declared | Enforced |
|---|---|
| `layers` includes `silver` | at least one `silver` entity |
| `layers` includes `gold` | at least one `gold` entity, **and** non-empty `relationships` **and** non-empty `dimensions` |
| `gold` absent, but an app is `layer: gold` | `deferred_note` is **required**, saying what is outstanding and where it is tracked |

While gold is deferred, association keys with no relationship are reported as a `NOTE`, not a
warning — they are expected, because the keys live in the consumer apps. Once gold is in scope the
same condition becomes a warning again.

---

## `subjects`

Business subject areas. **The only part of this spec that is not recoverable from the scripts** — it
is a reading of what each table is *for*, which the code cannot tell you. `model_doc.py` groups
`data_model.md` by these, so a wrong grouping surfaces in a document a person reads rather than
staying invisible.

```yaml
subjects:
  - name: Telephony and queues
    describes: >-
      How many calls arrived, how quickly they were answered, and how many callers gave up waiting.
    published_to: [MAC_Internal, MAC_External]     # optional
```

Each entity then carries `subject: Telephony and queues`.

Optional as a whole — but **once `subjects` is declared, every entity needs one that resolves**, or
the document silently drops tables into a bucket nobody reads. `describes` is prose for a
non-technical reader, and it opens that section of `data_model.md`: write it for the service, not for
the engineer. A declared subject with no entities warns.

Aim for subjects a business reader would recognise — how the service talks about its own work, not
how the apps are laid out. One subject per app is a sign the grouping has not been thought about.

---

## `sources`

Every physical input. One entry per object, not per use.

```yaml
- id: pbb.vw_crm_monthly              # required, unique; <prefix>.<object>
  system: athena                      # required: athena | qvd | inline | file
  database: raa_svcetl_pbb_prod_master_glue_db
  object: vw_crm_monthly              # required
  kind: view                          # table | view | qvd | seed
  maintained_by: system               # required: system | human
  opaque: true                        # view/definition not available for inspection
  external_service: CIMS              # set when the input belongs to another service
  notes: "Unified CRM view; includes AlayaCare data since RQP-7572."
```

`maintained_by: human` marks SharePoint-sourced (`spo_`) tables. These need an ingestion answer in the
target platform, not just a model — flag them in `business_context.md` too.

---

## `entities`

One entry per QVD **and** per app table. This is the bulk of the spec.

```yaml
- name: call_data                     # required, unique
  layer: silver                       # required: silver | gold
  app: PBB_DataModel                  # required — the repo DIRECTORY holding
                                      # `script`, which may differ from the
                                      # app's name. See the note above.
  script: 02b_Call_Data.qvs           # required
  lines: "4-350"                      # required
  artefact: "lib://QVDs Staging/PBB/data/prod/call_data.qvd"
  qlik_table: Call_Data_tbl           # the in-script table name
  grain: >                            # required — see below
    One row per (callreference, assessmentid) pair produced by a FULL OUTER JOIN
    of Procura CRM to Genesys telephony on callreferencecopiedfromgenesys.
  fan_out_risk: >                     # required — see below
    None at this level; this is the base fact. Note the FULL OUTER JOIN yields
    rows with no Procura side and rows with no Genesys side.
  row_expectation: "~1.1M rows as at Aug 2026"
  upstream: [pbb.vw_crm_monthly, pbb.vw_crm_weekly, pbb.genesys_call_monthly]
  filters:                            # row-scope applied on load
    - "weekly sources restricted to rows newer than max(monthly)"
  columns: [...]                      # required, non-empty
```

**`grain` is required and must be a sentence, not a field list.** "One row per X" forces the question
to actually be answered. A grain of "unknown" fails validation.

**`fan_out_risk` is required.** State whether joining this entity to its parent multiplies rows, and on
which key. `"none"` is a valid answer; an empty one is not. This is the field that prevents inflated
metrics after migration.

### When the schema genuinely cannot be recovered

An entity that does `LOAD *` from a QVD **no script in the repo produces** has an unknowable schema.
Record the hole; never invent a placeholder column to satisfy the non-empty rule — a fabricated
column is indistinguishable from a real one to everything downstream.

```yaml
- name: ext_quality_call_orphan
  # ... layer, app, script, lines, grain, fan_out_risk as usual
  schema_recoverable: false
  schema_recoverable_reason: >-
    LOAD * from MAC_Quality_Call.qvd, which no script in this repo produces. Resolve by reading the
    QVD header: QvdTableName() and CreateUtcTime will show what wrote it and when.
  finding: MAC-H-012                  # required — the hole must be a registered finding
  columns: []
```

The validator then exempts the entity from the non-empty-columns rule and warns on **every** run, so
the hole is reported until someone closes it. `grain` and `fan_out_risk` are still required: state
that they are unknown *and why it matters*. Requiring a linked finding is deliberate — declaring an
empty entity must never be cheaper than doing the work.

### `columns`

```yaml
- name: assessment_id                 # required
  source: pbb.vw_crm_monthly.assessmentid   # required — see resolution rules
  expression: "assessmentid as assessment_id"  # required, verbatim
  type: text
  notes: "Text; not zero-padded."
```

**`source` must be non-null.** Permitted values:

| Value | Meaning | Extra requirement |
|---|---|---|
| `<source_id>.<column>` | straight from a declared source | prefix must match a `sources` id |
| `<entity>.<column>` | from a declared upstream entity | column **must exist** on that entity |
| `derived` | computed from other columns | `derived_from:` list required |
| `literal` | constant (`'x' as y`) | — |
| `generated` | row-generation artefact (`RowNo()`, `AUTOGENERATE`) | — |

```yaml
- name: link_procura_key
  source: derived
  derived_from: [call_data.assessment_id, call_data.callreferencecopiedfromgenesys]
  expression: "IF(IsNull(assessmentid) OR IsNull(callreferencecopiedfromgenesys), null(), assessmentid & '-' & callreferencecopiedfromgenesys)"
  notes: "Composite association key. Null when either part is null."
```

Requiring `derived_from` is what keeps the lineage graph connected — `derived` alone would be a dead
end. Every ref is resolved by the validator; a dangling one fails the extraction.

**Name the columns the expression actually reads.** A ref that resolves can still be false lineage:
the neighbouring column in the same table resolves exactly as cleanly as the right one, and no
validator can tell them apart. In MAC a chain of three plausible, resolvable hops
(`DoneDate → LinkDate → AgeCareUserID`) was pure fiction, and it was caught only by reading
`lineage.md` afterwards. Prefer the true upstream column — usually the source column the SQL
selected — over a sibling that happens to sit in the same entity, and **read `lineage.md` before
declaring the extraction done**: deep chains are where this hides.

**`Dual()` columns** must declare their sort key:

```yaml
- name: assessment_date_monthyear
  source: derived
  derived_from: [call_data.assessment_date]
  expression: "Dual(Date(MonthStart(Date#(assessment_date,'DD/MM/YYYY hh:mm:ss')),'MMM-YY'), MonthStart(...))"
  dual:
    label: "MMM-YY formatted month"
    sort_key: "MonthStart of assessment_date"
  notes: "Emit as two columns in dbt: label + sort key."
```

---

## `relationships`

The associative model made explicit. One entry per association or join.

```yaml
- from: Call_Data_Monthly_tbl         # required
  to: Call_Category_tbl               # required
  join_keys: [link_procura_key]       # required, list — never write this as `on:`
  cardinality: one_to_many            # required: one_to_one | one_to_many | many_to_many
  mechanism: qlik_association         # required: qlik_association | explicit_join | mapping
  app: PBB_Internal                   # required
  fan_out: true                       # required
  join_sql: "LEFT JOIN … ON …"         # what dbt should write
  notes: "Unqualified in both tables, so they associate by field name."
```

`mechanism: qlik_association` means **there is no join anywhere in the source** — the link is a shared
field name governed by `Qualify`/`Unqualify`. Record where that declaration lives.

Where two tables share **two or more** unqualified fields, Qlik builds a synthetic key. Record it as a
`many_to_many` relationship *and* raise a finding.

---

## `dimensions`

Derived attributes used for slicing. Expression captured **verbatim** — no reformatting, no
normalising of dashes or case.

```yaml
- name: re_calleragebucket
  entity: Call_Data_Monthly_tbl
  app: PBB_Report_6Monthly
  script: 03a_Call_Data.qvs
  lines: "101-108"
  expression: |
    IF(LEN(TRIM(callerageyears)) > 0, IF(Num(callerageyears) >= 0 AND … , 'Not recorded')
  values: ['0-18', '19-25', '26-35', '36-45', '46-55', '56-70', '71+', 'Not recorded']
  null_handling: "blank and out-of-range both become 'Not recorded'"
  variants:
    - name: calleragebucket
      difference: "returns NULL instead of 'Not recorded'"
  notes: ""
```

Where the same concept exists in several apps with small differences, record one entry with `variants`
rather than three near-identical entries — and raise a **refactor** finding.

---

## `metrics`

Two lists, deliberately separated. Never guess an expression into `recovered`.

```yaml
metrics:
  recovered:
    - name: answered_within_sl
      entity: call_data
      script: 02b_Call_Data.qvs
      lines: "317-320"
      expression: "CASE WHEN g.callansweredtime IS NOT NULL AND g.callansweredtime <> '' AND g.callabandonedtime = '' AND cast(g.timetoanswer as integer) <= 120 THEN 1 ELSE 0 END"
      grain: per call
      business_rule: "Answered, not abandoned, and answered within 120 seconds."
      thresholds: {service_level_seconds: 120}
  todo:
    - name: "Grade Of Service (%)"          # required
      app: PBB_Internal                     # required
      evidence: "97_PBB_Data_Builder.qvs:178"  # required — where the name appears
      likely_inputs: [answered_within_sl, call_reference_id]
      where_to_find: "app master items / chart expressions"
```

Every `todo` entry is a named gap with a place to look, resolved by `qlik-export-metrics`.

---

## `parameters`

```yaml
- name: vMinCallDate                  # required
  defined_in: "PBB_Internal/01b_Init.qvs:7"   # required
  kind: watermark                     # watermark | path | flag | format | threshold
  default: "2023-12-31"
  computed_by: fn_GetMinCallDate
  used_by: ["PBB_Internal/03a_Call_Data.qvs:162", "PBB_Internal/03e_GA_Data.qvs:19"]
  purpose: "Upper bound on call_date in consumer apps; aligns secondary data to call data."
  dbt_target: var
  finding: PBB-D-001                  # link when the parameter is implicated in a finding
```

---

## `calendar`

```yaml
calendar:
  fy_start_month: 7                   # required
  first_week_day: 6                   # required (6 = Sunday)
  broken_weeks: true                  # required
  date_format: "YYYY-MM-DD"
  timezone: "Australia/Sydney"
  timezone_actually_applied: false    # set true only if an expression reads it
  script: 94a_calendar.qvs
  variants:
    - app: PBB_Report_6Monthly
      extra_fields: [FinancialYearStartYear, FinancialYearEndYear, Month_FY]
  fields: [FY, FinancialYear, FinancialYearQuarter, InFYTD, WeekCommencing, ...]
```

---

## `dead_code`

Artefacts the scripts produce that are deliberately **not** migrated. Required for any `STORE`
target the inventory could not resolve, otherwise the coverage gate cannot tell "excluded on purpose"
from "missed".

```yaml
- artefact: "$(vQvdFilePath)"        # the path exactly as inventory.json reports it
  script: PBB_DataModel/01b_Utility.qvs
  reason: "Dev-only rollback utility; writes to a caller-supplied path."
  finding: PBB-X-002
```

---

## `out_of_scope`

**`dead_code`'s opposite: live, but owned by another bundle.** `inventory.json` is repo-wide while a
bundle covers one generator, so a repo holding several generators presents `STORE` targets that are
neither this bundle's work nor dead. Without this list the only way past the coverage gate is to call
them dead code — which later reads as "not migrated", about QVDs that reload every day.

```yaml
out_of_scope:
  - artefact: Actual.qvd              # required, as inventory.json reports it
    app: MAC_ForecastDataGenerator_QLIK   # required, the directory
    script: "Data Generator App - 02 ETL Actual.qvs"
    owner_bundle: MAC_ForecastDataGenerator   # required, the bundle that owns it
    reason: "Second generator in this repo; needs its own bundle."   # required
```

The validator reports these as a `NOTE` naming the owning bundles, so the exclusion stays visible
rather than silent, and rejects an artefact listed in both `dead_code` and here.

The same applies to **sources**: an Athena object read only by another generator is declared in
`sources` with `out_of_scope: true`. Declaring it rather than omitting it is deliberate — a source
shared between two generators is a migration sequencing fact, and `read_by` is where it shows up.

---

## `lineage_notes`

What column refs cannot express. One entry per limitation.

```yaml
- kind: association                   # association | eav | human_source | external | opaque
  entity: Call_Category_tbl
  detail: "No FK exists; the link is the shared unqualified field name. Cardinality asserted by reading Qualify/Unqualify."
```

Use `eav` where one column's meaning varies by another's value, `human_source` where lineage ends in a
spreadsheet, `external` for cross-service edges, `opaque` where a view definition is unavailable.

---

## What the validator enforces

`python scripts/validate_spec.py <extraction_dir> [--repo <repo>] [--strict]` exits non-zero unless
all of the below hold. Two extra flags exist for the *authoring* loop rather than the gate:
`--fidelity-only` runs check 16 alone, and `--entity NAME` (repeatable) restricts it to one entity —
useful when a large spec is being written entity by entity. Neither completes an extraction, and both
say so.

1. All required keys present; `spec_version` is 1.
2. `sources` ids unique; `entities` names unique.
3. Every entity has a non-empty `grain` and `fan_out_risk`, **as strings** (guards the YAML
   boolean trap) and not a placeholder like `unknown`.
4. Every entity has at least one column — unless it declares `schema_recoverable: false`, which
   requires `schema_recoverable_reason`, a `finding`, and no columns, and warns on every run.
5. **Every column has a non-null `source`**, valid per the resolution table.
6. Every `derived` column has a non-empty `derived_from`.
7. Every entity-scoped ref resolves - the entity exists and carries that column.
8. Every relationship has `from`, `to`, `join_keys` (a list), `cardinality`, `mechanism`, `app`,
   `fan_out`. Writing `on:` instead of `join_keys:` is rejected explicitly.
9. Every `metrics.todo` entry has `name`, `app`, `evidence`.
10. Every parameter has `name` and `defined_in`.
11. Cross-check against `inventory.json`: every `STORE` target resolves to an entity, a `dead_code`
    entry or an `out_of_scope` entry; every SQL `FROM` resolves to a source; every external QVD
    dependency is declared with `external_service`. Each `out_of_scope` entry carries `artefact`,
    `app`, `owner_bundle` and `reason`, and appears in no `dead_code` entry.
12. Every finding id referenced from the spec exists in `findings.md`, and every finding there has
    exactly one class, a well-formed id whose class letter agrees, and `Evidence` /
    `Current behaviour` / `Stage 1` lines.
13. **`generator` is declared** and equals the extraction folder name.
14. **`scope` is declared**, and matches reality per the table above.
15. **Every entity's `app` is a real directory** under the repo root (checked once per app, by name,
    rather than once per entity), and **every entity's `script` exists with its `lines` range inside
    that file.** An `app` matching no `apps[].directory` or `apps[].name` warns.
16. **Every column `expression` appears verbatim in its entity's script**, whitespace-normalised but
    otherwise character-exact. This is what makes "verbatim" an enforced property rather than a
    promise: normalising a single en-dash to a hyphen fails the gate.
17. **If `subjects` is declared**, each carries a `name` and a `describes` sentence, and every entity
    carries a `subject` that resolves to one of them. A declared subject with no entities warns.

Checks 15 and 16 need the repo root. It is inferred as the grandparent of `extraction_dir`
(because bundles live at `<repo>/extraction/<generator>/`); pass `--repo` when the bundle
lives elsewhere.
