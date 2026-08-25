# Healthdirect Australia Qlik estate — conventions and recurring gotchas

**This file is living and append-only.** Every extraction must add anything it met that is not already
here, before declaring itself complete. That requirement is what makes each successive service cheaper
than the last.

`Catalogued from:` PBB (Aug 2026), MAC (Aug 2026).

---

## Estate shape

### The two-layer pattern

Each service is typically **one generator app plus one or more consumer apps**:

| Layer | Reads | Writes | Migration target |
|---|---|---|---|
| Generator (`*_DataModel`) | Athena | QVDs | silver |
| Consumers (per audience) | QVDs | in-memory model | gold + semantic |

The generator does the heavy SQL; the consumers rename, derive, bucket and label per audience. Expect
the consumer apps to be **near-duplicates of each other with meaningful divergences** — those
divergences are usually governance rules, not accidents, and must survive migration.

Verify this shape holds for each new service rather than assuming it.

**A repo may hold more than one generator.** MAC_QLIK contains `MAC_DataModel` (24 QVDs, four
consumer apps) *and* `MAC_ForecastDataGenerator` (4 QVDs, one consumer), sharing the service code and
the repo but not the pipeline. `qvs_inventory.py` refuses to guess when it detects several, which is
the signal to stop and confirm with the operator. Extract them as separate bundles.

**An app may be a binary copy of another.** MAC_Vendor's entire load script is a binary load of the
External app, so it has no model logic to extract — but it *is* a real consumer, and its row-level
scoping lives in the QVF's section access, which is not in git. Record it as an estate edge and route
the scoping question to the service.

### Where extractions live

One folder per generator, named after the generator app:

```
<repo>/extraction/<GENERATOR>/        e.g. PBB_QLIK/extraction/PBB_DataModel/
```

A repo may hold more than one generator, so the folder is never just `extraction/`. The name is
recorded as `generator:` in `model_spec.yml`, and the gate fails if the two disagree. **Confirm the
generator name with the operator** rather than inferring it from the repo directory - the estate has
many generators and this name is what downstream tooling globs for.

### Athena naming

```
raa_svcetl_<service>_prod_master_glue_db      service's own curated tables
raa_svcetl_spo_prod_master_glue_db            SharePoint-sourced reference data
raa_svcetl_ga_prod_master_glue_db             Google Analytics 3 / Universal Analytics
raa_svcetl_gav4_prod_master_glue_db           Google Analytics 4
```

**GA lives in two databases, not one.** `ga` is GA3 and `gav4` is GA4, and a single loader reads
both across a cutover date. Reading by eye it is easy to see only the first; run the inventory and
trust its database list. The same object name (`vw_ga_pagesourcemedium`) exists in both, so source
ids must be qualified by generation.

**`spo_` prefixed tables are human-maintained**, landing from SharePoint spreadsheets. They are not
system-of-record data: they have no referential guarantees, get edited by hand, and need an *ingestion*
answer in the target architecture, not just a model. Always call these out separately.

**The `spo_` prefix is not sufficient to identify them.** There are two SharePoint layers — the
estate-wide `raa_svcetl_spo_prod_master_glue_db` and a per-service one, e.g.
`raa_svcetl_mac_spo_prod_master_glue_db` — and the per-service database mixes hand-edited sheets with
system extracts delivered *via* SharePoint. In MAC, `mac_hda_queue_mapping` and
`mac_operations_directors_dashboard_kpi` are hand-maintained without the prefix, while the
`mac_cognos_*` and `mac_siebel_*` tables in the same database are system extracts. Classify by what
maintains the table, not by its name; 22 of MAC's 53 sources are human-maintained.

**Audience scoping may live in a spreadsheet.** MAC's `qlik_internal` / `qlik_external` flags — the
rule deciding what the funder sees — are columns in a hand-edited queue-mapping sheet, matched with
case-sensitive equality against `'YES'`. So does its effective-dated queue-to-service-line mapping.
Governance depending on an unversioned file is worth raising on its own terms.

**`vw_` prefixed tables are views**, often unions that hide their own logic. Check whether the view
definition is available; if it is not, record it as an opaque boundary in the lineage.

### QVD library paths

```
lib://QVDs Staging/<SERVICE>/data/prod      live
lib://QVDs Staging/<SERVICE>/data/dev       dev (vDevMode = 1)
lib://QVDs Final/<SERVICE>/data/…           testing
```

Selected by `fn_InitConfig(rootPath)` with `'Staging'` for live and `'Final'` for test, plus a
`vDevMode` flag choosing the `prod`/`dev` leaf. Record which combination production actually runs.

**The folder name is not always the service code.** MAC uses a numbered display name —
`lib://QVDs Staging/4. My Aged Care Data Model/data/prod` — and nests QVDs in per-subject subfolders
(`kms/`, `mtc/`). Read the path out of `fn_InitConfig` rather than assuming the PBB shape.

**There may be a second library outside the QVD estate.** MAC's consumer configs set
`vQVDReferenceFolderPath = 'lib://Reference Files'`, holding a postcode-to-statistical-area
concordance that **no script in the repo produces**. An input with no producer has no refresh story,
no schema contract and no owner — treat it as a blocking question, not a detail.

### Cross-service QVD dependencies

Consumer apps read QVDs published by **other services'** pipelines — PBB Internal reads
`lib://QVDs Staging/CIMS/data/prod/CIMS_AllService.qvd`. These edges determine migration sequencing:
a consumer's gold layer cannot land before its upstream service's silver exists. Record them in
`service_profile.yml` under `consumes_external_qvds`.

### Monthly / weekly source pairs

Sources commonly come in pairs — `…_monthly` and `…_weekly` — with the weekly table carrying only rows
newer than the monthly table's high-water mark:

```sql
FROM …_weekly AS w, monthly_max_date
WHERE date_parse(w.date, '%d/%m/%Y') > monthly_max_date.max_date
```

This is the estate's incremental pattern. In dbt it becomes an incremental model with an explicit
watermark. Note that different consumer apps may point at *different* members of the pair — that
changes their data currency and is a deliberate design choice worth recording.

---

## Locale and calendar

Set in `01_Main.qvs` of every app, and it matters. **Do not assume ISO — read it.** PBB uses ISO;
MAC uses US-style month-first with a 12-hour clock:

```qvs
SET DateFormat='M/D/YYYY';                            // MAC
SET TimestampFormat='M/D/YYYY h:mm:ss[.fff] TT';      // MAC
```

That single difference propagates everywhere, because Qlik uses these variables for every *implicit*
text-to-date conversion — and generators routinely hand Qlik text that does not match them. It is the
root of several MAC findings: `Hour()` on a raw timestamp string, `Date(Floor(x))` on an ISO date
string, timestamp subtraction for duration measures, and an incremental filter that works only
because both sides happen to be `YYYYMMDD`. **Establish the format variables before reasoning about
any date expression**, and where a text value cannot match them, record the question rather than
assuming either outcome.

The PBB (ISO) variant, for comparison:

```qvs
SET DateFormat='YYYY-MM-DD';
SET TimestampFormat='YYYY-MM-DD HH:mm:ss[.fff]';
SET FirstWeekDay=6;        // Sunday-starting weeks
SET BrokenWeeks=1;         // weeks do not span year boundaries
SET FirstMonthOfYear=1;
SET CollationLocale='en-US';
```

- **Australian financial year, July–June.** `'FY' & Year(MakeDate(if(Month<=6, Year, Year+1), 6, 30))`
  is the estate idiom. FY26 = 1 Jul 2025 – 30 Jun 2026.
- **`FirstWeekDay=6` means weeks start Sunday**, not Monday. Snowflake's `WEEK` defaults differ; set
  `WEEK_START` explicitly or compute weeks arithmetically.
- **`BrokenWeeks=1`** truncates weeks at the year boundary rather than carrying them across.
- Timezone is nominally `Australia/Sydney` (`vTimeZone`), but it is frequently set and never used —
  check whether any expression actually reads it before assuming conversion happens. **In MAC it
  genuinely is used** (in the QVD metadata scanner, and via `vKMSTimeZone` in the Internal app's
  `ConvertToLocalTime` calls), so `timezone_actually_applied: true` is a real answer, not a default.
  Note the generator's Athena queries also do their own `AT TIME ZONE` conversions *independently* of
  the variable, which is where MAC's two timezone defects arise.
- Calendar scripts (`94a_calendar.qvs`) are copy-pasted between apps **with small divergences**. Diff
  them; do not assume one calendar.

Recurring calendar fields: `FY`, `FinancialYear`, `FinancialYearQuarter`, `FinancialMonthOrdinal`,
`InFYTD`, `InYTD`, `InQTD`, `InMTD`, `MonthsAgo`, `WeekCommencing` (in several formats),
`IncompleteMonth`, `SeasonName`.

---

## Config idioms

`fn_InitConfig(rootPath)` in `01a_Config.qvs` sets `vLibRootPath`, `vCurrentTimestamp`, `vTimeZone`,
`vDateFormat`, `vTimeFormat`, `vDevMode`, `vQVDFolderPath`, and `ErrorMode`. Near-identical across
apps and services; diff rather than re-read.

`load_datetime` is stamped onto nearly every stored table as `'$(vCurrentTimestamp)' as load_datetime`
— an audit column, and the key used by rollback utilities.

Utility `SUB`s that appear in generator apps (`fn_CopyQvds`, `fn_CopyFile`, `fn_ResetQvdFileData`,
`fn_RollbackQvdFileData`) are **dev/ops tooling, not model logic**. Classify as dead code for
migration, but note that `fn_ResetQvdFileData` and `fn_RollbackQvdFileData` reveal the intended
operational recovery story, which the target platform still needs an answer for.

---

## Recurring gotchas

Each of these has been observed in the estate. Check for every one on every service.

### `ErrorMode=0` in production
Config sets `ErrorMode=0` on the production path, so **every load failure is silent**. Any defect
below that depends on a failing statement will therefore be invisible in the app. Always a
**migration hazard**: the dbt equivalent must fail loudly.

### `Peek` from a table name that does not exist
Pattern: a `SUB` loads a table under one name and `Peek`s from another (often the SQL's inner alias
rather than the Qlik table name). Returns null, the variable keeps its default, and `ErrorMode=0`
hides it. Seen in PBB's `fn_GetMinCallDate`: loads `Min_Call_Date_tbl`, peeks `'combined_dates'`.
**Check every `Peek` table name against the table actually loaded.**

Then map the blast radius per app rather than assuming it is uniform: in PBB the same broken variable
truncates call data in two consumer apps but not the third, which bounds only its GA load. Sibling
apps that look copy-pasted often are not. `grep` every use of the variable before writing the impact.

### Watermark variables with misleading names
`fn_GetMinCallDate` computes `MIN` of two `MAX`es — it is a *high-water mark for aligning secondary
data to call data*, not a minimum call date. Read what the SQL does, not what the name says.

### Indigenous status flag mapping
Recurring hand-written `IF`/`WildMatch` ladders collapsing a free-text indigenous status field into a
binary flag. The PBB implementation maps **Torres Strait Islander and "Not stated" both to `'0'`**,
which misclassifies TSI respondents. Never reuse an existing flag without checking its branches
against the real value distribution. Aboriginal and/or Torres Strait Islander status should be
recorded and reported in a way that represents First Nations people accurately and respectfully — a
defect here has consequences beyond the number.

### En-dash in category strings
CRM category values contain `–` (en-dash, U+2013) in some branches and `-` (hyphen) in others, inside
the same `CASE`. Transcribe verbatim.

### Case-sensitivity in `Match()`
An upstream label change that alters only capitalisation silently zeroes a `Match()` branch. Already
caused a live count defect in PBB's `nursetriage` field.

### Text-typed dates and numerics
Source columns arrive as text: dates as `'DD/MM/YYYY hh:mm:ss'` or `'DD/MM/YYYY'`, postcodes and IDs
as strings. `Num(postcode)` is applied inconsistently, so `'0800'` and `'800'` may or may not match
depending on the code path. Record the exact treatment per column.

### Composite keys built by string concatenation
`postcode & '-' & state`, `assessmentid & '-' & callreference`, `main_category & '-' & sub_l1_category`.
These become the association keys. They inherit every formatting inconsistency of their parts, and a
null part usually yields a null or malformed key. Check the null handling on each.

### Empty semantic-layer files
`95a_Dimensions.qvs` and `96a_Measures.qvs` exist by convention but are frequently **stubs containing
only comments**. The measures live in the app's master items and chart expressions inside the QVF,
which is not in git. Expect to find measure *names* only — often as labels in a data-builder inline
table (`97_*_Data_Builder.qvs`) — and route the expressions to `qlik-export-metrics`.

### EAV-shaped analytics tables
GA data lands in a tall `attribute` / `dim` / `metric` / `top_rank` shape built from a very large
`UNION` chain (PBB: ~27 attributes over 1,758 lines). `metric` means a different thing per `attribute`
value. Document as **pattern plus attribute inventory**, never transcribed line by line, and note that
column lineage alone understates the transform.

### Row-ranking windows ordered by a text date
`ROW_NUMBER() OVER (PARTITION BY … ORDER BY <text date> ASC)` where the ordering column is an
unparsed `'DD/MM/YYYY HH:mm:ss'` string. The sort is lexical, so day-of-month dominates: `'02/01/2025'`
sorts before `'11/12/2024'`. The *count* of rank-1 rows stays right, so it never shows up as a total
being wrong — but the row selected is not the earliest, and every attribute read from it may come
from the wrong record. Seen in PBB's `call_rank`, which is the model's de-duplication rule.

### `ApplyMap` handed the wrong argument
A state-name map keyed on abbreviations, called with a `postcode-state` composite key, so nothing ever
matches and every row silently takes the default. Seen in PBB's `postcode_state_full`, immediately
below a correct call on the same map. Check what each `ApplyMap` is actually passed, not what the
column name implies.

### Asymmetric casting across the two halves of a composite key
One side builds `Num(postcode) & '-' & state`, the other builds `postcode & '-' & state`. The
association then only works where the reference value has no leading zero. In Australia this
selectively breaks **Northern Territory** postcodes (`0800`-`0899`). Always compare how both sides of
a composite key are built, and measure the match rate per state.

### Multiple date formats within one service
PBB carries four: `'DD/MM/YYYY HH:mm:ss'` (CRM), `'DD/MM/YYYY'` (telephony), `'YYYYMMDD'` (monthly
returns) and `'DD/MM/YYYY'` again for the forecast table, whose neighbours all use `'YYYYMMDD'`.
Never assume one format per service; record it per column.

### Blank-versus-null in telephony fields
Genesys columns arrive as empty strings, not nulls, and the SLA logic tests `= ''` specifically in
one place and `IS NOT NULL AND <> ''` in another. Any ingestion that normalises `''` to NULL silently
moves the service-level numbers. Preserve the distinction through landing, and assert it there.

### Connection strings named after individuals
`LIB CONNECT TO 'AWS Athena Prod (okta_firstname.lastname@healthdirect.org.au) …'`. The production
connection is tied to named people's Okta identities. Record it: it is a continuity risk worth
raising regardless of the migration.

### App ids that disagree between README files
The same app appears with different GUIDs in the repo root README and its own app README, and
on-prem versus Qlik Cloud ids differ for some apps while matching for others. Never take an app id
from one file alone - collect all of them and ask which is live before exporting anything.

### GA3 → GA4 cutover
GA data spans two incompatible source generations with a cutover date variable, plus a
delete-then-append refresh (`fn_DeleteDataFromGAFile`). Both generations' attribute lists must be
captured, along with which one covers which date range.


### Hour-gated orchestration inside the script
A generator may do materially different work depending on **when** it runs. MAC's orchestration
section gates its five most expensive loaders on the wall-clock hour:
`IF MATCH($(vHour), '5', '6') THEN ... CALL COGNOSLoad ...`, where `vHour = HOUR(vCurrentTimestamp)`.
Everything after the `END IF` runs on every reload. So the app reloads several times a day and the
agreement between the Qlik task schedule and that `MATCH` list exists nowhere but in the two lining
up. Combined with `ErrorMode=0`, a delayed or retried reload skips those loads silently. Always read
the orchestration section for conditional `CALL`s before assuming a section runs, and **ask the
operator for the real reload times** - the schedule is part of the logic.

### Three incremental patterns in one generator
Do not assume a service has one incremental contract. MAC has three, plus eight entities with none:
a **21-day re-extract** (re-pull a fixed window, re-read older rows from the QVD - a missed day
self-heals, which is why its fragility goes unnoticed); a **gap-filling watermark** (the earlier of
`today - N` and the QVD's own `MAX(date)`, so it reaches back if the QVD has fallen behind - worth
preserving, it is the only self-healing backfill); and a true **upsert** (`MAX(modifiedon)` plus a
`NOT EXISTS` anti-join on the key). Record which pattern each entity uses; they translate differently.

### Composite key conventions drift, and the separator is the tell
A service may migrate its composite-key format and leave residue. MAC moved from `-` to `;`
separated `<date><sep><discriminator>` keys, leaving three things behind: four silver QVDs still
computing the old `-` form that **no consumer reads**; one consumer app (NPrinting) never migrated
and internally consistent on `-`; and a header comment still documenting `[Date]-[CallType]` directly
above code using `;`. Two encodings of the same logical key coexist and are not interchangeable.
Check the separator at every build **and** parse site before assuming a key is shared.

### The same key parsed positionally with different segment counts
Where a composite key is decomposed with `SubField(k, ';', n)`, the contributing tables may supply
different numbers of segments with different meanings. MAC's Internal bridge parses four positions
while its eleven source tables supply between two and four - and two of them **deliberately repeat**
a value in positions 2 and 3 so both dimension columns populate. The External app solves the same
problem differently, parsing segment 2 *twice*. Neither is a bug; both must be recorded per table.
Map the segment meaning per contributing table, or the gold model will silently mis-attribute
dimension values.

### One QVD per audience, from two non-equivalent loaders
Two QVDs with the same stem and a `_v2` suffix are not necessarily old and new. MAC's
`MAC_Activity_Resolution` and `MAC_Activity_Resolution_v2` are read by **different apps** and select
different rows (one filters on activity type and CSS agents, the other on channel), compute different
measures, and derive their end date differently. Both are live, so the same named KPI differs between
the Internal and External dashboards. Check *who consumes* each version before concluding one
supersedes the other - and check whether a consumer loads `_v2` into a table named after `v1`, which
MAC does.

### An expensive QVD with no consumer
Check every published QVD for a reader before migrating it. MAC's `MAC_Call.qvd` is the generator's
most expensive output - a four-way compound join of telephony, a Siebel bridge, CRM interactions and
the agent list three times - and its only consumer was commented out in September 2023 because the
app would not load on Qlik Cloud. It has been built daily for nobody since. `grep` the QVD name
across the repo; a commented-out reader is the signal, and the comment usually says why.

### `Timestamp(x, 'DD MMM HH:MM')` renders the month, not the minutes
In Qlik format strings `mm` is minutes and `MM` is **month**. `'HH:MM'` therefore yields
hour-then-month, collapsing every interval within an hour to the same label. Seen live in MAC's
`Interval_format`, exposed in the External app. Check every format string containing `MM` next to a
time component.

### Period-to-date calendar flags that ignore the period
`InQTD` written as `If(DayNumberOfQuarter(DateTemp) <= DayNumberOfQuarter(Today()),1,0)` compares the
day ordinal within a quarter while ignoring **which** quarter, so it flags the opening days of every
quarter in the calendar. Same shape for `InWTD` on weekdays. And `InYTD` / `InMTD` / `InFYTD`
typically test only period membership, with no upper bound at today - which matters because a
`FieldValue`-generated calendar extends as far as any forecast table projects. Five of MAC's six
to-date flags are wrong this way, in all three apps. **Check each flag for both halves of the
predicate: the right period, and `<= Today()`.**

### `IncompleteMonth` set on complete months
`If(MonthEnd(DateTemp) < MonthEnd(Today()),'Yes')` is true for months that have **ended** - the
complete ones - and null for the current and future months. The field name means the opposite of its
value, so a filter excluding `'Yes'` drops all history and keeps only the partial month. Read the
predicate, not the name.

### Two spellings of financial year in one calendar
MAC's calendar publishes `[FY]` as `'FY26'` and `[FinancialYear]` as `'FY2026'` for the same period,
plus `FinancialYearsAgo` and `FinancialYearQuarter`. Both are correct and a filter written for one
matches nothing in the other. Additionally `[FY]`'s `Dual` **sort key is one year behind its label**
- ordering still works because the offset is uniform, but any expression reading the numeric half
gets a date a year early. Record both fields and reproduce the offset.

### `YearWeek` built from two different days and two week conventions
`weekyear(DateTemp + 1)&'-'&'W'&num(week(DateTemp,6,0),'00')` takes the year from `DateTemp + 1` and
the week number from `DateTemp`, so they disagree at year boundaries; and the explicit `0` for
broken-weeks contradicts the app's `SET BrokenWeeks=1`, so the calendar carries two inconsistent week
definitions. Whenever `Week()` is called with explicit arguments, check them against the SET
variables - the arguments win.

### Positional string surgery on offset-bearing timestamps
KMS timestamps arrive as `'DD/MM/YYYY h:mm:ss AM +HH:MM'` and are reassembled by dropping the last 7
characters, parsing the head, and re-appending the last 6 as an offset. Correct for that exact format
and brittle to any change in it. Worse, the result is `CAST(... AS TIMESTAMP)` - **not** `TIMESTAMP
WITH TIME ZONE` - so the offset is likely discarded despite the column being named `_utc`, and the
value is then converted *again* with `AT TIME ZONE`. A day-boundary shift is the symptom. Check the
cast target whenever a string carries an offset.

### `AT TIME ZONE` applied to columns already in that zone
Where a source has mixed-zone columns, look for a documented contract and check whether the code
follows it. MAC's MTC file header states that `hd_`-prefixed datetimes are Sydney time and all others
UTC; one `hd_` column is correctly exempted from conversion with an inline comment, and **eleven of
its siblings are converted anyway**. Either the comment is wrong or those columns are double-shifted
by the Sydney offset - and every duration mixing a converted with an unconverted column inherits the
error. The internal inconsistency is the signal; `DESCRIBE` the source view to settle it.

### A five-character year format
`format_datetime(x, 'YYYYY-MM-dd HH:mm:ss')` - five `Y`s - emits a five-digit year (`02026-...`). One
character, among eleven otherwise-correct siblings in the same `SELECT`. Worth scanning format strings
character by character when they are repeated in bulk; a diff against the siblings finds it fastest.

### A variable redefined mid-script at script scope
`vCurrentTimestamp` is set by `fn_InitConfig`, then **re-assigned** at the top of MAC's MTC section -
outside any `SUB`, so it applies to every section loaded afterwards. The four later sections stamp
`load_datetime` with milliseconds while the earlier ones do not. It reads as harmless local
initialisation. That matters because `load_datetime` is what the rollback utility orders by, as a
**string**, so mixed formats make the recovery mechanism unreliable. Grep for `LET` re-assignments of
config variables outside `SUB`s.

### Bucket ladders with an unreachable boundary
`WHEN "call no" >= 8 and "call no" <= 9 THEN '8 to 9' ELSE 'more than 10'` has no bucket for exactly
10, and the `ELSE` also absorbs zero, null and blank. Check the top and bottom of every ladder for
gaps, and check what the catch-all actually catches. MAC's `case_interactions` additionally compares a
spreadsheet column against integers with no `try()`, so a varchar column would fail the whole load
silently.

### Row filters hidden in a `LOAD *` consumer
An audience app may narrow its data in ways that look incidental. MAC's External app filters KMS
content views to `typename = 'Document'` where the Internal app loads all types, so the two apps'
knowledge-base counts are not comparable - and nothing labels this as a scoping decision. Diff the
`WHERE` clauses between sibling apps, not just the field lists.

---

## Service register

| Service | Repo | Generator | Consumers | Extracted |
|---|---|---|---|---|
| PBB | `PBB_QLIK` | `PBB_DataModel` (11 QVDs) | `PBB_Internal`, `PBB_External`, `PBB_Report_6Monthly` | silver complete 2026-08-24; gold + metrics outstanding |
| MAC | `MAC_QLIK` | `MAC_DataModel` (24 QVDs) | `MAC_Internal`, `MAC_External`, `MAC_NPrinting_Reporting`, `MAC_Vendor` | silver + gold complete 2026-08-25, gate PASS (51 entities, 737 columns, 699 expressions verified); metrics outstanding - all 13 Directors Dashboard KPIs. **No upstream service dependency**, so it can be sequenced independently |
| MAC (forecast) | `MAC_QLIK` | `MAC_ForecastDataGenerator` (4 QVDs) | `MAC_ForecastApp` | not started. Second generator in the MAC repo; separate bundle |
| CIMS | — | — | — | not started. **Also an upstream of PBB** — publishes `CIMS_AllService.qvd`, so its silver must land before PBB_Internal's gold |
| HIAS | — | — | — | not started |
| GP | — | — | — | not started |

Keep this table current. It is the estate index. **The estate has more generators than the rows
below** - add a row the first time each one is touched rather than treating this list as complete.

**Confirmed on PBB, worth checking on each new service:**
- the generator/consumer split holds, with consumer apps as near-duplicates
- consumer apps may read *different* members of the monthly/weekly source pair, making one app
  deliberately more current than its siblings
- an external-audience app withholds columns present in silver: a governance rule, not an omission
- `95a_Dimensions.qvs` / `96a_Measures.qvs` exist and are empty
- calendar scripts are copy-pasted per app and have already drifted

**Confirmed on MAC (Aug 2026) - where it agreed with PBB:**
- the generator/consumer split, with consumer apps as near-duplicates and the divergences being the
  interesting part
- copy-pasted calendars (three of them, one field of drift, and every calendar defect in triplicate)
- `ErrorMode=0` on the production path
- a production Athena connection named after individuals - two of them, in all four apps
- text-typed dates, blank-versus-null significance, and postcodes losing leading zeros
- measures living in the QVF, not in the scripts

**Where MAC contradicted the PBB baseline - check rather than assume:**
- **the locale is not ISO** (`M/D/YYYY`, 12-hour), which changes every implicit date conversion
- **`timezone_actually_applied` is true**; the variable is genuinely read
- **two generators in one repo**, and one app that is a binary copy of another
- **no empty `95a_/96a_` semantic stubs at all** - the measure split is clean, so there is no
  partially-populated measure layer to mine
- **no cross-service QVD dependency**, so no sequencing constraint
- **the external app is broader than the internal one** in three respects: more history, more columns
  in two sections, and unmasked usernames. The governance direction is not reliable.
- **the `spo_` prefix does not identify hand-maintained tables** - there are two SharePoint layers and
  the per-service one is mixed
- **`ROW_NUMBER() ORDER BY <text date>` is done correctly here** (`ORDER BY TRY_CAST(col AS INT) ASC,
  col ASC`), so the pattern is not universally broken - but the same service commits the aggregate
  form of the error (`MIN` over a text timestamp)
- **`ApplyMap` is called correctly** in both MAC sites, including the `NULL()`-default-plus-`COALESCE`
  idiom, which is the pattern to copy

**Migration sequencing so far:** CIMS → PBB. MAC is independent - it reads no other service's
QVDs - but it has three inputs with **no producer in its own repo** (two quality QVDs and a postcode
concordance), which are blocking questions rather than sequencing constraints. Extend as each
service's `consumes_external_qvds` is recorded.
