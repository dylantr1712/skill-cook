# <SERVICE> — findings

Recorded during extraction. Classification rules and tie-breaks: `FINDINGS-TAXONOMY.md`.

**This register is a backlog, not a work order.** Stage 1 is a lift-and-shift: defects are
*replicated* so parity holds, and refactors are *not done*. Only migration hazards are stage-1 work.

Ids are stable and never renumbered: `<SERVICE>-<D|H|R|X>-<NNN>`.

| Class | Prefix | Stage 1 action |
|---|---|---|
| Defect | `D` | replicate exactly, raise a stage-2 ticket |
| Migration hazard | `H` | **must** be handled during migration |
| Refactor opportunity | `R` | record only, do not touch |
| Dead code | `X` | exclude, record why |

Required on every entry: **Class**, **Evidence**, **Current behaviour**, **Stage 1**.
`Confidence: unverified` is mandatory on anything not provable from the source alone.

> **These four label texts are parsed verbatim.** `validate_spec.py` matches
> `- **<Key>:** <value>` and compares the key as an exact string, so rewording a label — even to
> something clearer, like `**Current behaviour, and why it is correct in Qlik:**` — reads as a
> *missing* field and fails the gate. Keep the label fixed and put every qualifier in the value. An
> empty value fails too.

---

## Defects

### <SERVICE>-D-001 — <one-line title>

- **Class:** Defect
- **Confidence:** verified
- **Evidence:** `<APP>/<script>.qvs:<line>`
- **Spec ref:** `entities.<entity>.<column>`
- **Current behaviour:** <what the code does today>
- **Impact:** <which numbers are wrong, and how widely>
- **Correct behaviour:** <what it should do>
- **Stage 1:** Replicate current behaviour so parity holds.
- **Stage 2 ticket:** <raise against / ticket id>

---

## Migration hazards

### <SERVICE>-H-001 — <one-line title>

- **Class:** Migration hazard
- **Evidence:** `<APP>/<script>.qvs:<line>`
- **Spec ref:** `entities.<entity>.<column>`
- **Current behaviour:** <what the code does today, and why it is correct in Qlik>
- **Risk on Snowflake:** <how a literal translation diverges>
- **Stage 1:** <the explicit decision — the required handling>

---

## Refactor opportunities

### <SERVICE>-R-001 — <one-line title>

- **Class:** Refactor opportunity
- **Evidence:** `<APP>/<script>.qvs:<line>`
- **Current behaviour:** <correct, but structurally poor>
- **Proposed change:** <what stage 2 should do>
- **Stage 1:** None. Migrate as-is.

---

## Dead code

### <SERVICE>-X-001 — <one-line title>

- **Class:** Dead code
- **Evidence:** `<APP>/<script>.qvs:<line>`
- **Current behaviour:** <what it is>
- **Stage 1:** Not migrated. <why it is safe to exclude>
