# Skill Authoring

Load before creating or editing any skill. Covers taxonomy, licensing and
attribution, the lean-content rule, confidentiality layers, cross-cutting
principle propagation, and live-file editing rules.

## Taxonomy (full)

Two homes for every observation and skill:

- **Open-source** — client-agnostic, methodology-driven, useful to any
  practitioner. No names, domains, credentials, or project specifics.
- **Internal** — contains user/client/project specifics, private stack
  details, or personal preferences. Lives in a private skills location.

Default to **open-source** when an item could go either way, stripping the
specifics into a generalised form. The open-source/internal line is also the
confidentiality boundary: crossing it leaks. When in doubt, generalise and
keep the specific version internal.

## Lean-content rule

A skill earns every line. Before adding content, ask "what can this
replace?" as hard as "what does this add."

- No section that hasn't proven relevant across multiple real sessions.
- No rule derived from a single unvalidated observation — wait for a
  pattern, or mark it provisional.
- No "just in case" complexity that has never triggered.
- Prefer structural enforcement (a checklist, a verification step, an
  unskippable tool call) over louder prose. A rule the agent keeps
  violating should be converted to enforcement or removed — not repeated
  in bold.
- Push detail into on-demand reference files; keep `SKILL.md` to what's
  needed to route and act.

## Confidentiality layers (2–5)

Layer 1 (generalise the Principle) is enforced at logging time in SKILL.md.
The remaining layers apply when authoring:

2. **Issue/Improvement scrubbing.** When promoting an observation into a
   skill, strip client names, product names, internal URLs, and any detail
   that identifies a real project from the text that ships.
3. **Example sanitisation.** Replace real inputs/outputs in examples with
   invented, plausible, non-identifying equivalents. Never paste raw client
   data as an example.
4. **Aggregation check.** Confirm that several generalised details in the
   same skill can't be recombined to re-identify a project or person.
5. **Home check.** If an insight only makes sense with specifics that can't
   be stripped, it belongs in an internal skill, not an open-source one.
   Don't dilute an open-source skill to fit an inherently internal insight.

## Attribution & licensing

- New open-source skills carry an attribution/licence consistent with this
  repository's licence. Use the template below.
- When adapting an existing third-party skill, preserve its original
  attribution and licence, and note the adaptation.
- Never relicense internal specifics as open-source.

Attribution template (top-of-skill comment or a `NOTICE`):

```
Skill: [name]
Origin: [this repo / adapted from <source> (<licence>)]
Licence: [licence]
```

## Cross-cutting principles

Some observations reveal a principle that applies to skills generally, not
just one. Propose these for `cross-cutting-principles.md` (create it if
absent).

Template:

```markdown
# Cross-Cutting Principles

Principles that apply across skills, promoted from observations.

---

## [Principle name]
**Promoted from:** Observation [N]
**Applies to:** [which skills / all]
**Principle:** [the generalisable rule]
**Why:** [what failure or friction it prevents]
```

Propagation: when a principle is added, check whether existing skills
already violate it and log observations for the ones that need updating —
don't silently rewrite every skill at once.

## Live-file editing rules

- **Small, additive, low-risk** (a new rule, a clarification, a factual
  fix): edit the skill file directly.
- **Substantial** (restructuring, new capability, changed methodology) and
  **all new-skill creation**: draft first, show the user, then apply/stage
  per the environment (see `references/environments.md` and
  `references/weekly-review.md` → delivery/staging).
- One skill file at a time. Read the current file before editing — never
  edit from memory of an earlier version.
- After editing, confirm the change is coherent with the skill's own rules
  (a skill that preaches lean content shouldn't grow a redundant section).
- New skill scaffolding: `skills/<name>/SKILL.md` with `name` +
  `description` frontmatter; push depth into `references/` files loaded on
  demand.
