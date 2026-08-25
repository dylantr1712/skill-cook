---
name: qlik-extract-logic
description: "Extract a Qlik service's .qvs logic into a spec, lineage, findings register and parity plan, ready for a Snowflake + dbt lift-and-shift."
disable-model-invocation: true
---

# Extract Qlik `.qvs` logic

Reads one Healthdirect Qlik service repo and produces the extraction bundle that a Snowflake + dbt
lift-and-shift is built from. The bundle, not a summary, is the deliverable.

Stage 1 is **like for like**. Numbers must match, *including where they are currently wrong*. That
single constraint drives every rule below.

**Completion is not a judgement call:** `validate_spec.py` must exit 0. Until it does, the extraction
is incomplete regardless of how finished it feels.

## Reference

Load as needed, not upfront:

| File | When |
|---|---|
| `QVS-LANGUAGE.md` | any construct whose semantics or SQL equivalent is not obvious |
| `HDA-CONVENTIONS.md` | estate naming, paths, calendar, recurring gotchas — **read the gotchas before starting** |
| `SPEC-SCHEMA.md` | authoring `model_spec.yml` |
| `FINDINGS-TAXONOMY.md` | classifying anything wrong or improvable |
| `PARITY-TESTING.md` | writing `parity_tests.md` |

Templates in `assets/`. Requires `pyyaml` (`pip install pyyaml`).

---

## Process

### 1. Orient

Confirm with the user, before writing anything:

- **repo path**
- **service code** (e.g. `PBB`)
- **the name of the data generator this bundle covers** (e.g. `PBB_DataModel`) — this names the
  output folder and is recorded as `generator:` in the spec
- whether all apps are in scope

**Ask for the generator name; do not infer it silently.** Step 2 detects candidates — the apps that
`STORE` QVDs — so you can propose one, but the operator confirms. The estate has many generators, a
repo may hold more than one, and the folder name is a lasting convention that downstream tooling
depends on: getting it wrong is expensive to undo later.

Record the git SHA (`git -C <repo> rev-parse --short HEAD`) — the spec is only meaningful against a
known commit.

Read `HDA-CONVENTIONS.md` now, particularly the gotchas. Every one is a thing to actively look for.

### 2. Inventory

```
python scripts/qvs_inventory.py <repo> --summary --generator <GENERATOR>
```

Writes `<repo>/extraction/<GENERATOR>/inventory.json`. **All bundle files live in that folder** —
one folder per generator, named after it, so a repo with several generators does not collide.

Omit `--generator` only when you want the detected name: the script uses it if exactly one app
`STORE`s QVDs, and refuses when there are several. Either way, confirm it against step 1 before
continuing.

This is the map and the coverage baseline: everything it found must end up accounted for.

**A repo may hold more than one generator.** The inventory stays repo-wide, so it will list `STORE`
targets and SQL sources belonging to generators this bundle does not cover. Those go in the spec's
`out_of_scope` list — **never in `dead_code`**. They are live artefacts with an owner; calling them
dead reads later as "not migrated". Each one names its `owner_bundle`, which is also the reminder
that a second bundle is owed. `--generator` names the folder only; it does not narrow the inventory.

Read the summary properly. Note the generator and consumer apps, the databases, the published QVDs,
any external QVD dependency, the association keys, and the unresolved paths. **Do not proceed on an assumption the
inventory contradicts** — it parses the scripts and is more reliable than a skim.

*Done when:* the summary is read and the app/QVD/source counts are known.

### 3. Seed the profile

Copy `assets/service_profile.template.yml` to `extraction/<GENERATOR>/service_profile.yml` and fill what the
inventory knows. Ask the user for what it cannot: app ids, reload schedules, owners, audiences.

`publishes_qvds` and `consumes_external_qvds` are the estate dependency edges, and each external
edge is a hard migration sequencing constraint. Get them right even when they look incidental.

*Done when:* every app and every inventory-listed QVD appears, and open questions are asked, not guessed.

### 4. Generator app → silver

Read the generator app in **section order** (the order `inventory.json` lists — lexical by filename,
which is the dependency declaration). For each stored table, write an entity:

- `grain` as a sentence. Not a field list, not "unknown".
- `fan_out_risk` explicitly. `"none - base fact"` is fine; blank is not.
- Every column with `source` and verbatim `expression`.
- `filters` for any row-scope applied on load.

Capture `sources` and `parameters` as you meet them.

Where a `LOAD` sits above a `SQL` block, both stages are one transform: the SQL alias is the column's
`source`, the Qlik expression is its `expression`. The `LOAD` field list is the real output schema —
anything the SQL selects but the `LOAD` omits is discarded and must not appear.

**Authoring at scale.** A large generator's spec runs to hundreds of columns, and the verbatim check
is the expensive one to satisfy. Write one part file per entity and verify each as you go with
`validate_spec.py --entity <name>`, which runs the fidelity check alone. Then concatenate the parts
into `model_spec.yml` and **delete them** — two copies of the contract is one too many.

*Done when:* every `STORE` in `inventory.json` has an entity, a `dead_code` entry or an
`out_of_scope` entry.

### 5. Consumer apps → gold

Same treatment per consumer app, plus:

- **Diff the sibling apps** before writing anything. Consumer apps are near-duplicates; the
  divergences are the interesting part and are usually deliberate governance rules (a field withheld
  from an external audience is a rule, not an oversight). Record what each app exposes and withholds.
- **Relationships.** Read every `Qualify`/`Unqualify`; the unqualified fields are the complete join
  key list. Write one relationship per association with its `cardinality` and `fan_out`.
- **Dimensions.** Derived buckets, flags and labels, expressions verbatim. Where the same concept
  appears in several apps with small differences, use one entry with `variants` and raise a refactor
  finding.

*Done when:* every association key in `inventory.json` appears in a relationship, and every field in
any `*_Data_Builder.qvs` inline table resolves to an entity column, a dimension, a metric, or a
`metrics.todo` entry.

### 6. Metrics

Split honestly:

- `recovered` — the rule is genuinely in the script. Thresholds, flags, row-ranking dedup.
- `todo` — a measure whose name appears (usually as a label) but whose expression lives in the QVF.
  Record `name`, `app`, `evidence`.

**Never infer an expression into `recovered`.** A plausible guess is worse than a recorded gap: the
gap gets resolved, the guess gets trusted. Semantic-layer stubs are usually empty by convention —
see the gotcha in `HDA-CONVENTIONS.md`.

### 7. Calendar

Fill `calendar` from the app's `01_Main.qvs` locale block and its calendar script. **Diff the
calendar scripts across apps** — they are copy-pasted and drift. Set
`timezone_actually_applied` only if an expression genuinely reads the timezone variable.

### 8. Findings, written as you go

Not a separate pass. When you notice something, classify and record it immediately in
`extraction/<GENERATOR>/findings.md` (from `assets/findings.template.md`) — the context is loaded now and will
not be this cheap again.

One class per finding, per `FINDINGS-TAXONOMY.md`. The tie-break: **would this be wrong if we never
migrated?** Yes → Defect. No → Migration hazard.

Mark anything not provable from the source alone `Confidence: unverified` and say what would settle
it. Do not silently drop a suspicion.

### 9. Validate

```
python scripts/validate_spec.py <repo>/extraction/<GENERATOR>
python scripts/lineage_graph.py  <repo>/extraction/<GENERATOR>
python scripts/model_doc.py      <repo>/extraction/<GENERATOR>
```

Fix errors until it exits 0. Treat warnings as questions to answer, not noise to tolerate — an
unqualified field in no relationship usually means a missed join.

Then read `lineage.md`. Any chain in the "Broken chains" section is a hole in the graph. Deep chains
are where parity failures will hide, so check the ones that matter read correctly.

**Then read `data_model.md`.** It is the first view in which the model is legible as a whole, so it
is where a wrong grain, a mis-grouped table or a sentence that reads like nonsense to a business
reader becomes obvious. Every problem it shows is fixed **in the spec**, never in the document.

*Done when:* `validate_spec.py` prints PASS.

### 10. Narrative documents

- `business_context.md` — what the service reports on, who each app serves, the audience-scoping
  rules, the orchestration and incremental contract, the type/format contracts Snowflake will not
  forgive, and the don't-migrate list. Readable by someone who does not know Qlik.
- `parity_tests.md` — per `PARITY-TESTING.md`. Include a freeze point.
- `metrics_todo.md` — the measure gap, the app ids, and how to close it with `qlik-export-metrics`.
- `README.md` — how the bundle fits together and how to regenerate the derived files.
- `data_model.md` — **generated, not written.** Part 1 walks the model by business subject area for
  the service to confirm; Part 2 is the per-table reference. Its quality comes entirely from the
  spec: declare `subjects` with a `describes` sentence each, tag every entity, and make sure each
  `grain` reads as a sentence a non-technical reader can check. This is the artefact the service
  signs off, so it is worth spending the subject descriptions on.

### 11. Feed the catalogue

**Required, not optional.** Append to `HDA-CONVENTIONS.md`:

- any construct, naming pattern, path convention or gotcha met that was not already catalogued
- the service register row, updated

This is why service #4 costs less than service #1. Skipping it degrades the skill for everyone.

*Done when:* `HDA-CONVENTIONS.md` covers everything this extraction had to work out, and
`QVS-LANGUAGE.md` covers every construct the repo used.

---

## Rules that decide quality

**Verbatim means verbatim.** Never reformat an expression, normalise an en-dash to a hyphen, or fix
casing. A single wrong dash silently empties a category; `Match()` is case-sensitive. Character
fidelity is the deliverable.

**Pattern, not transcription, for generated bulk.** A 1,700-line `UNION` chain gets documented as a
pattern plus an attribute inventory, with the variations named. The coverage gate still proves nothing
was skipped. Transcribing it wastes context that the subtle logic needs.

**Grain before columns.** If you cannot state an entity's grain in a sentence, you do not yet
understand it, and its columns will be wrong. Work it out first.

**Fan-out is the number-one parity risk.** Qlik associations do not inflate counts; SQL joins do.
Every entity finer-grained than its parent needs that written down.

**Record, don't fix.** Found a bug? Replicate it and register it. Found duplication? Register it and
migrate it as-is. Stage 1 changes nothing.

**Ask rather than assume.** Reload schedules, app ids, audiences and whether a suspected defect is
live are things the user knows and the code does not.

---

## Out of scope

Master item and chart expressions inside the QVF (→ `qlik-export-metrics`), dbt model authoring
(→ `qlik-scaffold-dbt`), and running the parity tests, which needs both platforms live.
