# Qlik `.qvs` language reference, for migration to Snowflake + dbt

What each construct *means*, and what it becomes in SQL. Read the sections you need; the
[semantic traps](#semantic-traps) section is the one that decides whether a lift-and-shift matches.

Append to this file whenever you meet a construct that is not here.

---

## Script structure

**Section order is lexical by filename.** `01_Main.qvs`, `01a_Config.qvs`, `02a_…`, `99_Exit.qvs`
run in that order. There is no manifest and no explicit import — the numbering *is* the dependency
declaration. A file's position tells you what is already in memory when it runs.

Conventional numbering in the HDA estate: `01*` config/init, `02*`–`05*` loads, `9x*` calendar and
semantic helpers, `99_Exit`.

**`SUB name(args) … END SUB` / `CALL name(args)`** — procedures. Qlik has no return value; a `SUB`
communicates by creating tables or setting variables. Note `EXIT SUB` returns early.

**`LET` vs `SET`** — `LET v = expr` evaluates the expression; `SET v = text` assigns the literal text
unevaluated. Mixing them up is a common source of a variable holding `Now()` as a string instead of a
timestamp.

**Qlik has two literal forms, and both contain `//`.** Single quotes (`'lib://…'`) and **square
brackets** (`FROM [lib://QVDs Staging/PBB/data/prod/call_data.qvd]`). Brackets also delimit
identifiers containing spaces (`AS [Month-Year]`, `[Include (Y/N)]`). Any tooling that strips
comments must treat both as literals — miss the bracket form and every QVD path in the repo is read
as a comment.

**`$(var)` is textual macro expansion, performed before the statement is parsed.** This is not
variable substitution in the SQL sense. Consequences that matter:
- `'$(v)'` produces a quoted literal; `$(v)` splices raw text, so a variable can carry an operator, a
  whole `WHERE` clause, or a table name.
- **An undefined or empty variable expands to nothing**, silently producing a malformed or
  semantically different statement. Combined with `ErrorMode=0` this yields wrong results with no
  error. Treat every `$(…)` as a place to check the variable is genuinely set.

**`ErrorMode`** — `0` ignore errors and continue, `1` halt (default), `2` halt without rollback.
Production HDA apps commonly run `ErrorMode=0`, which means load failures are invisible. Always
record this; see `HDA-CONVENTIONS.md`.

---

## Loading data

### Preceding LOAD over `SQL`

The dominant pattern in the HDA estate:

```qvs
Call_Data_tbl:
NoConcatenate LOAD
    assessmentid as assessment_id
    , IF(IsNull(a) OR IsNull(b), null(), a & '-' & b) as link_procura_key
    , '$(vCurrentTimestamp)' as load_datetime;
SQL
    SELECT … FROM "db"."table";
```

**Two transform stages in one statement.** The `SQL` block runs on Athena; the `LOAD` above it runs in
Qlik over that result set. The `LOAD` field list is the **actual output schema** — anything the SQL
selects but the `LOAD` omits is discarded. Both stages must be captured separately in the spec, and
the `expression` recorded per column is the *Qlik* expression, with the SQL alias as its `source`.

Field references in the `LOAD` are **case-insensitive** against the SQL's output column names. Athena
and Snowflake are not equally forgiving; see the traps.

### Table concatenation

Qlik **auto-concatenates** two `LOAD`s whose field lists are identical, silently, into one table.

- `NoConcatenate` forces a separate table.
- `CONCATENATE (Table) LOAD …` appends explicitly → `UNION ALL`.

Auto-concatenation is fragile under change: add one field to one of two matching loads and they stop
merging, producing two tables and different results. Where you see matching loads without an explicit
keyword, record it as a **migration hazard**.

### QVD round-trip

`STORE Table INTO [path/name.qvd] (qvd)` persists; `LOAD * FROM [path/name.qvd] (qvd)` reads. QVDs are
the layer boundary in the HDA estate: the generator app stores them, the consumer apps read them.
Every `STORE` is a silver-layer table; every QVD `LOAD` is a dependency edge.

### Resident load

`LOAD … RESIDENT Table` reads an already-loaded in-memory table → a CTE or intermediate model. Order
matters: the source table must still exist (not yet `DROP TABLE`d).

### Other load sources

- `AUTOGENERATE n` — generate n rows, used with `RowNo()` to build calendars → `GENERATOR` /
  `SEQ4()` in Snowflake, or a dbt date-spine macro.
- `LOAD * INLINE [ … ]` — literal table → a dbt seed.
- `MAPPING LOAD` — a two-column lookup consumable **only** by `ApplyMap`. Does not enter the data
  model and creates no association.
- `FieldValue('field', n)` / `FieldValueCount` — read the *n*th distinct value of an already-loaded
  field. Used in calendar scripts to find min/max dates.
- `DirList` / `FileList` / `FileSize` — filesystem access, dev tooling only. Almost always **dead
  code** for migration purposes.

---

## The associative model

**This is the single largest conceptual gap between Qlik and dbt.** Qlik has no foreign keys and, in
these apps, almost no explicit joins. Two tables associate when they **share a field name**.

`Qualify *` renames every subsequently loaded field to `TableName.field`, which *prevents*
association. `Unqualify a, b, c` exempts those fields, so they keep their bare names and **become the
join keys**. The pattern:

```qvs
Qualify *;
Unqualify link_procura_key, link_date, postcode_state;
Call_Data_Monthly_tbl:
LOAD …
```

means "this table joins to everything else on `link_procura_key`, `link_date` and `postcode_state`".
**Read every `Unqualify` in a repo and you have the complete join key list.**

**Synthetic keys** — when two tables share *two or more* field names, Qlik silently builds a `$Syn`
bridge table. Usually a modelling accident. Record it; it is nearly always a **refactor opportunity**,
and occasionally a defect.

**Circular references** — three or more tables associating in a loop. Qlik marks one table loose and
results become ambiguous. Always a finding.

### Explicit joins

Qlik does have `LEFT JOIN (Table) LOAD …`, `INNER JOIN`, `OUTER JOIN`, and `KEEP`. Where present these
map to SQL directly. `JOIN` with no prefix means outer.

`Exists(field)` filters to values already loaded elsewhere → a semi-join. **It is order-dependent**:
it tests whatever has been loaded so far, so the same statement placed earlier means something
different. When translating, name the specific upstream table explicitly:

```qvs
WHERE Exists(link_procura_key)          -- Qlik: whatever loaded link_procura_key already
```
```sql
WHERE link_procura_key IN (SELECT link_procura_key FROM {{ ref('call_data') }})
```

`Peek('field', row, 'Table')` reads a single cell — row `0` first, `-1` last. **Scoped to the named
table**, which must exist. Naming a table that was never loaded returns null rather than erroring, and
under `ErrorMode=0` that failure is silent. A frequent defect site.

---

## Construct → SQL translation

| Qlik | Meaning | Snowflake / dbt |
|---|---|---|
| `NoConcatenate LOAD` | separate table | its own model / CTE |
| `CONCATENATE (T) LOAD` | append | `UNION ALL` |
| auto-concatenation | implicit append | `UNION ALL` — but flag it |
| `LOAD … RESIDENT T` | re-read in-memory table | CTE or intermediate model |
| `STORE … (qvd)` | persist | a materialised model (silver) |
| `LOAD … FROM […] (qvd)` | read persisted | `ref()` |
| `Qualify` / `Unqualify` | association control | explicit `JOIN … ON` |
| `Exists(f)` | value already loaded | `IN (SELECT …)` / semi-join |
| `Peek('f', n, 'T')` | single cell | scalar subquery or a var |
| `ApplyMap('m', x, dflt)` | lookup with default | `LEFT JOIN` + `COALESCE`, or `DECODE`/`CASE` |
| `MAPPING LOAD` | lookup table | dbt seed |
| `LOAD * INLINE` | literal rows | dbt seed |
| `WHILE IterNo() <= …` + `SubField` | row explosion | `LATERAL FLATTEN(SPLIT(col, ';'))` |
| `SubField(s, d, n)` | nth token (`-1` = last) | `SPLIT_PART(s, d, n)` |
| `SubStringCount(s, d)` | delimiter count | `LENGTH(s) - LENGTH(REPLACE(s, d, ''))` |
| `Dual(text, num)` | display + sort value | **two columns**: label + sort key |
| `Match(x, 'a', 'b')` | position, **case-sensitive** | `CASE`/`IN` — mind the case |
| `WildMatch(x, '*a*')` | glob, case-**in**sensitive | `ILIKE` |
| `Pick(Match(…), …)` | switch idiom | `CASE` |
| `Date#(s, 'fmt')` | text → date | `TO_DATE(s, fmt)` |
| `Date(d, 'fmt')` | date → text | `TO_CHAR(d, fmt)` |
| `Num(x)` | text → number | `TRY_TO_NUMBER(x)` |
| `MonthStart(d)` | period start | `DATE_TRUNC('month', d)` |
| `Interval(x, 'fmt')` | duration format | `TO_CHAR` on a duration |
| `KeepChar(s, '123')` | keep listed chars | `REGEXP_REPLACE(s, '[^123]', '')` |
| `Len(Trim(x)) > 0` | non-blank test | `COALESCE(TRIM(x), '') <> ''` |
| `AUTOGENERATE n` | n rows | `GENERATOR(ROWCOUNT => n)` / date spine |
| `RowNo()` / `RecNo()` | output / input row number | `ROW_NUMBER()` |
| `TAG FIELD … WITH` | field metadata | dbt `meta:` / column tags |
| `DROP TABLE` | free memory | nothing (no equivalent needed) |
| `TRACE` | log line | nothing |
| `SUB` / `CALL` | procedure | macro, or just inlined SQL |
| `AUTONUMBER f1, f2;` | replace values with integers | nothing — **values become unreproducible**, so never join or compare on them across platforms |
| `Previous(f)` | previous *input* row's value | `LAG(f) OVER (ORDER BY …)` |
| `Peek('f')` (no row/table) | previous *output* row of the table being built | `SUM(…) OVER (… ROWS UNBOUNDED PRECEDING)` — a running total |
| `Interval(a - b, 'fmt') * 86400` | duration in seconds | `DATEDIFF('second', b, a)` |
| `ConvertToLocalTime(ts, 'tz')` | UTC → zone | `CONVERT_TIMEZONE('UTC', 'tz', ts)` |
| `Timestamp#(s, 'fmt')` | text → timestamp | `TO_TIMESTAMP(s, fmt)` |
| `NUM#(s)` | text → number, locale-aware | `TRY_TO_NUMBER(s)` |
| `Alt(a, b, …)` | first non-null/valid | `COALESCE(a, b, …)` |
| `Repeat(s, n)` | repeat string | `REPEAT(s, n)` |
| `Index(s, sub)` | position of substring | `POSITION(sub, s)` |
| `Mid(s, n)` | substring from n | `SUBSTR(s, n)` |
| `FieldValue('f', IterNo())` + `while` | iterate a field's distinct values | `SELECT DISTINCT f` — see the date-spine note below |
| `TableNumber('T')` | is table loaded? | nothing — a control-flow guard, not logic |
| `DROP FIELD f FROM T` | remove one column | omit it from the model |
| `Hour(x)` / `Month(x)` on **text** | implicit parse then extract | `DATE_PART` on an **explicit** cast — see trap 10 |
| `DayNumberOfQuarter(d)` | day ordinal within quarter | `DATEDIFF('day', DATE_TRUNC('quarter', d), d) + 1` |
| `weekyear(d)` | ISO-ish week-numbering year | `YEAROFWEEK(d)` — mind `WEEK_START` |
| `WeekStart(d)` | start of week, honours `FirstWeekDay` | `DATE_TRUNC('week', d)` — **set `WEEK_START` first** |
| `Week(d, fwd, bw)` | week number with explicit conventions | `WEEK(d)` — the 2nd/3rd args override the SET variables, so read them |

---

## Semantic traps

These break lift-and-shift parity. Each one seen in the HDA estate.

**1. Association fan-out does not inflate counts in Qlik; a SQL join does.**
When a fact table associates 1:many with a detail table, Qlik's `Count(fact.id)` still counts rows in
the *fact* table restricted by the current selection — it does not multiply. The equivalent SQL join
multiplies. This is the number-one cause of inflated metrics post-migration. Translate to
`COUNT(DISTINCT …)`, a semi-join, or pre-aggregation — and record `fan_out_risk` on every entity whose
grain is finer than the fact it attaches to.

**2. `Match()` is case-sensitive, `WildMatch()` is not.**
A label change upstream that only alters capitalisation silently zeroes a `Match()` branch. This has
already caused a live defect in the estate. Check every `Match` against real source values, and prefer
recording the case-handling explicitly in the spec.

**3. Qlik dates are numbers wearing a format.**
A Qlik date is a float; `Date#()` parses text into one, `Date()` formats one back. Comparing a
**text** date against a real date compares text, so `'31/12/2023' <= '2023-12-31'` is a string
comparison that happens to run without error. Source systems in this estate deliver dates as *text*
in `'DD/MM/YYYY hh:mm:ss'`. Every such comparison is a **migration hazard** until explicitly cast.

**4. `$(var)` expanding to nothing.**
Undefined variable → empty expansion → malformed or subtly different statement → with `ErrorMode=0`,
no error. Check that every referenced variable is set on every path, including inside `SUB`s where a
`Peek` may have failed.

**5. `Dual()` carries sort order invisibly.**
`Dual('Jan-24', 45292)` displays as text but sorts and compares numerically. Drop the numeric half in
migration and every chart re-sorts alphabetically. Always emit a separate sort-key column.

**6. Blank vs null.**
Qlik distinguishes `''` from null, and the `Len(Trim(x)) > 0` idiom treats both as absent. Preserve
whichever semantic the original used; do not "tidy" one into the other.

**7. Auto-concatenation is schema-dependent.**
Identical field lists merge silently. Any field addition changes the table topology. Record where the
original relies on it.

**8. `Exists()` and `Peek()` depend on load order.**
Both read state accumulated so far. Reordering models in dbt changes their meaning. Pin the intended
upstream explicitly.

**9. Text-typed numerics.**
Postcodes, IDs and flags arrive as text and are compared with `Num()` in some places and not others.
`'0800'` and `'800'` are different strings and the same number. Record the exact treatment per column.

**10. Character-level literals.**
Category strings in this estate contain an **en-dash** (`–`, U+2013) in some branches and a hyphen
(`-`) in others, within the same `CASE`. Transcribe verbatim; never normalise. A single wrong dash
silently empties a category.

**8. `AUTONUMBER` destroys key comparability.**
`AUTONUMBER f;` replaces every value of `f` with an integer assigned in load order. Associations
survive within the reload, but the values are meaningless outside the app and unstable between
reloads. Any parity test that compares key values will fail for a reason unrelated to the migration —
and a test comparing *counts of distinct keys* can pass while the values differ entirely. **Reconcile
on the business columns the key is built from, never on the key.** Seen in both MAC consumer apps,
applied to two composite keys and an email address.

**9. `Qualify` / `Unqualify` are stateful, and order decides what associates.**
They are directives, not declarations: each applies only to `LOAD` statements that *follow* it. So
`Unqualify PersonId` issued after the tables that would use it leaves those tables' `PersonId`
qualified, and the intended association silently does not exist. Seen in MAC External's KMS section,
where the user list is joined to nothing at all. When mapping the associative model, read the
directives **in script order** and attribute each to the loads that follow it — not to the section
as a whole.

**10. Qlik's implicit text→date parse uses the app's format variables, which may not be ISO.**
`Hour('2026-08-04 14:23:11')`, `Date(Floor(x))` and `a - b` on text timestamps all require Qlik to
interpret text against `DateFormat` / `TimestampFormat`. Those are set per app and are **not
necessarily ISO**: MAC sets `M/D/YYYY` and `M/D/YYYY h:mm:ss[.fff] TT`. When the text does not match,
the result is null rather than an error, and `IsNull()` guards do **not** catch it — a non-matching
string is not null, so the expression proceeds and yields null downstream. Under `ErrorMode=0`
nothing is reported. Always check the app's format variables before assuming a text date parses, and
record the question rather than guessing.

**11. A `LEFT JOIN` filtered in the `WHERE` clause is an `INNER JOIN`.**
`LEFT JOIN m ON … WHERE m.flag = 'YES'` discards every unmatched left row, so the join is not
preserving anything. It reads as optional enrichment and acts as a row filter. Seen three times in
MAC, twice deliberately (an audience flag, a CSS-agent restriction) and in both cases scoping the
output by a hand-maintained spreadsheet. Always check whether a right-table predicate sits in `ON` or
in `WHERE` — it changes the row count, not just the columns.

**12. A `LEFT JOIN` used to apply a "latest row" CTE does not filter at all.**
The idiom `LEFT JOIN latest ON key = key AND date = latest.max_date` looks like de-duplication and is
a no-op: the left row survives whether or not it matches. It needs an `INNER JOIN`, or
`WHERE latest.key IS NOT NULL`. Seen in MAC's registration override, where it turns an intended
de-duplication into a row multiplication. Whenever a CTE computes a `MAX` per key, check how its
result is *applied*.

**13. An aggregate over a text timestamp is a lexical aggregate.**
`MIN(activity_end_date_time)` on text, parsed afterwards, returns the lexically smallest string. With
a zero-padded ISO format that coincides with the chronological minimum; with an **unpadded** hour
(`%k`) it does not, so `'…14:05:00'` sorts before `'…9:05:00'`. And across mixed formats in one column
it is arbitrary. Push the parse **inside** the aggregate. The same trap in window form —
`ROW_NUMBER() … ORDER BY <text date>` — is catalogued in `HDA-CONVENTIONS.md`; MAC's AV0003 loader
shows the correct pattern, `ORDER BY TRY_CAST(col AS INT) ASC, col ASC`.

**14. Qlik wildcards left inside a SQL string never match.**
Qlik's `LIKE` uses `*`; SQL's uses `%`. An expression copied from a Qlik `LOAD` into an `SQL` block
keeps its asterisks and becomes a literal-string comparison that is false for every row — silently,
with no syntax error. Seen in MAC's `mac_call_av1`, where two warm-transfer flags carried over from
the Qlik layer are `0` for every row. When the same expression appears in both layers of a
preceding-`LOAD`-over-`SQL` pair, check which dialect each copy is actually evaluated in.

**15. A calendar generated from `FieldValue` spans whatever the model happens to contain.**
The `FieldValue('LinkDate', IterNo())` + `while` idiom reads the min and max of a field's *symbol
table*, so the generated date spine is data-driven, differs per app, and extends as far as any
forward-looking table projects. Two consequences: the spine cannot be modelled as a fixed range, and
any `Today()`-relative flag on it silently covers future dates. It also creates a hard **section
ordering dependency** — the calendar must load after every table contributing key values, which is
why MAC's file is named "98 Calendar Dim (After ComKey)".
