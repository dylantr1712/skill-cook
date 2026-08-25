#!/usr/bin/env python3
"""Render model_spec.yml as a document a person can read and check.

Two parts. Part 1 walks the model by business subject area, in language that
assumes no Qlik and no SQL, so the service can confirm what the numbers mean.
Part 2 is the per-entity reference for whoever builds the models.

Derived, never authored: everything here is already in model_spec.yml,
findings.md and service_profile.yml. If a sentence reads badly, fix it in the
spec and regenerate - do not edit data_model.md. Two editable copies of the same
fact is exactly the drift the bundle exists to prevent.

Column expressions are deliberately left out: 700-odd verbatim Qlik expressions
would bury the document, and they are the spec's job. Part 2 points at it.

Requires: pyyaml  (pip install pyyaml)

Usage:
    python model_doc.py <extraction_dir>
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("model_doc.py needs pyyaml:  pip install pyyaml")

# parse_findings is the validator's, not a second implementation: findings.md is
# a machine-read format and one parser must own it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_spec import Report, parse_findings  # noqa: E402

UNGROUPED = "Ungrouped"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load(d: Path, name: str, required: bool = True) -> dict:
    p = d / name
    if not p.exists():
        if required:
            sys.exit(f"missing {p}")
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def flow(value, dash: str = "—") -> str:
    """Collapse a YAML block scalar to one line of prose for a table cell."""
    if value is None or value is False:
        return dash
    text = " ".join(str(value).split())
    return text or dash


def cell(value) -> str:
    """Table-cell safe: pipes would break the row."""
    return flow(value).replace("|", "\\|")


def sentence(value) -> str:
    """findings.md writes each field value as a continuation of its own label -
    "Impact: the column is ..." - which reads correctly there and as a fragment
    once rendered as standalone prose. Capitalise the opening word, but never
    touch one that starts with `code` or an _identifier_."""
    text = flow(value)
    return text[0].upper() + text[1:] if text[:1].islower() else text


def anchor(text: str) -> str:
    """GitHub-flavoured heading anchor."""
    slug = re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")
    return re.sub(r"-+", "-", slug)


def title_of(fid: str, findings: dict) -> str:
    """The one-line title from the finding's ### heading."""
    return flow((findings.get(fid) or {}).get("title"), dash="") or fid


def finding_refs(ent: dict) -> list[str]:
    """Every finding id this entity or any of its columns names."""
    ids: list[str] = []
    for value in [ent.get("finding")] + [c.get("finding")
                                         for c in ent.get("columns") or []]:
        for fid in re.findall(r"\b[A-Z][A-Z0-9]*-[DHRX]-\d{3}\b", str(value or "")):
            if fid not in ids:
                ids.append(fid)
    return ids


# ---------------------------------------------------------------------------
# part 1 - by subject
# ---------------------------------------------------------------------------

def part1(out: list[str], spec: dict, profile: dict, findings: dict,
          groups: dict, subject_meta: dict, tbl) -> None:
    out.append("# Part 1 — What the data means\n")
    out.append(
        "This part is for the people who own the numbers rather than the code. Each section is one\n"
        "subject area: what it answers, which tables carry it, what is known to be wrong today, and\n"
        "what we need the service to confirm. No Qlik or SQL knowledge is assumed.\n")
    out.append(
        "**How to check a section.** Read the plain-terms line for each table and ask whether it\n"
        "matches how the team actually uses that data. A wrong grain — one row per *call* where the\n"
        "business means one row per *client* — is the single most expensive thing to find late, and\n"
        "the easiest thing to spot here.\n")

    todo = spec.get("metrics", {}).get("todo") or []

    for n, subject in enumerate(groups, 1):
        meta = subject_meta.get(subject, {})
        ents = groups[subject]
        out.append(f"\n## {n}. {subject}\n")
        if meta.get("describes"):
            out.append(f"{flow(meta['describes'])}\n")
        if meta.get("published_to"):
            out.append(f"*Reported in:* {', '.join(meta['published_to'])}\n")

        rows = [(f"`{e['name']}`", e["layer"], cell(e.get("grain")))
                for e in ents]
        out.append(tbl(f"{subject} — the tables, and what one row of each means",
                       ["Table", "Layer", "One row is..."], rows))

        # Numbers wrong today: defects reachable from this subject's entities.
        # Only defects, and for the checklist only unverified defects: a hazard
        # or a dead-code suspicion is an engineering question, and asking the
        # service to confirm one wastes the one review they will give us.
        defects, unverified = [], []
        for e in ents:
            for fid in finding_refs(e):
                f = findings.get(fid) or {}
                if f.get("fields", {}).get("Class") != "Defect":
                    continue
                if fid not in [d[0] for d in defects]:
                    defects.append((fid, f))
                if (f["fields"].get("Confidence", "").startswith("unverified")
                        and fid not in [u[0] for u in unverified]):
                    unverified.append((fid, f))

        if defects:
            out.append("\n**Numbers that are wrong today.** These are reproduced exactly as they are "
                       "during the migration, so the two platforms agree; fixing them is separate, "
                       "later work.\n")
            for fid, f in defects:
                impact = f["fields"].get("Impact") or f["fields"].get("Current behaviour")
                out.append(f"- **{fid} — {title_of(fid, findings)}.** {sentence(impact)}")
            out.append("")

        names = {e["name"] for e in ents}
        gap = [m for m in todo
               if names & {str(x) for x in (m.get("likely_inputs") or [])}
               or any(str(x).split(".")[0] in names
                      for x in (m.get("likely_inputs") or []))]
        if gap:
            out.append("\n**Not reproducible yet.** These measures are defined inside the Qlik app "
                       "rather than in any script, so their exact rules are not yet recovered:\n")
            for m in gap:
                out.append(f"- {m['name']} — *{m['app']}*")
            out.append("")

        if unverified:
            out.append("\n**To confirm.** These look wrong from the code alone, but proving it needs "
                       "a look at the data — or someone who knows how the numbers are used:\n")
            for fid, f in unverified:
                out.append(f"- [ ] **{fid}** — {title_of(fid, findings)}")
            out.append("")

    # Closing: the things that block the whole build.
    mig = profile.get("migration") or {}
    blocking = mig.get("blocking_questions") or []
    out.append(f"\n## {len(groups) + 1}. Before anything is built\n")
    if blocking:
        out.append("These questions change what the *correct* answer is, so they come before "
                   "modelling rather than during testing:\n")
        for q in blocking:
            out.append(f"- [ ] {flow(q)}")
        out.append("")
    n_todo = len(todo)
    if n_todo:
        out.append(f"There are also **{n_todo} measures** whose definitions live inside the Qlik "
                   f"apps and are not in version control. Until they are exported, the funder-facing "
                   f"app cannot be signed off as matching. See `metrics_todo.md`.\n")
    out.append("Fuller narrative on how the pipeline runs, which formats matter and what must not be "
               "migrated: `business_context.md`. Every finding in full: `findings.md`.\n")


# ---------------------------------------------------------------------------
# part 2 - by entity
# ---------------------------------------------------------------------------

def part2(out: list[str], findings: dict, groups: dict,
          rels: list, tbl) -> None:
    out.append("\n---\n")
    out.append("# Part 2 — Table reference\n")
    out.append(
        "One section per table, grouped as in Part 1, silver (built from the source systems) before\n"
        "gold (built for an app). **Column expressions are not repeated here** — they live verbatim in\n"
        "`model_spec.yml`, and their full derivation chains in `lineage.md`.\n")

    by_from = collections.defaultdict(list)
    by_to = collections.defaultdict(list)
    for r in rels:
        by_from[r.get("from")].append(r)
        by_to[r.get("to")].append(r)

    n = 0
    for subject, ents in groups.items():
        out.append(f"\n## {subject}\n")
        for e in ents:
            n += 1
            name = e["name"]
            out.append(f"\n### {n}. `{name}`\n")

            facts = [
                ("Layer", e.get("layer")),
                ("Built by", f'`{e.get("app")}/{e.get("script")}`'
                             f'{" lines " + str(e["lines"]) if e.get("lines") else ""}'),
                ("Output", f'`{e.get("artefact") or e.get("qlik_table") or "—"}`'),
                ("One row is", e.get("grain")),
                ("Fan-out risk", e.get("fan_out_risk")),
                ("Rows expected", e.get("row_expectation")),
            ]
            filters = [f for f in (e.get("filters") or []) if flow(f) != "None."]
            if filters:
                facts.append(("Row scope", "; ".join(flow(f) for f in filters)))
            out.append(tbl(f"`{name}` — summary",
                           ["", ""],
                           [(f"**{k}**", cell(v)) for k, v in facts if v]))

            joins = []
            for r in by_from.get(name, []):
                joins.append((f'→ `{r.get("to")}`', cell(r.get("cardinality")),
                              ", ".join(f"`{k}`" for k in r.get("join_keys") or []),
                              "**yes**" if r.get("fan_out") else "no",
                              cell(r.get("app"))))
            for r in by_to.get(name, []):
                joins.append((f'← `{r.get("from")}`', cell(r.get("cardinality")),
                              ", ".join(f"`{k}`" for k in r.get("join_keys") or []),
                              "**yes**" if r.get("fan_out") else "no",
                              cell(r.get("app"))))
            if joins:
                out.append(tbl(f"`{name}` — how it associates with other tables",
                               ["Related table", "Cardinality", "Key(s)",
                                "Inflates rows?", "App"], joins))

            fids = finding_refs(e)
            if fids:
                out.append("**Known issues:** " + ", ".join(
                    f"{fid} ({title_of(fid, findings)})" for fid in fids) + "\n")

            if e.get("schema_recoverable") is False:
                out.append(
                    f"> **The columns of this table are not known.** "
                    f"{flow(e.get('schema_recoverable_reason'))} "
                    f"Tracked as {e.get('finding')}.\n")
                continue

            cols = e.get("columns") or []
            rows = [(f'`{c.get("name")}`', cell(c.get("type")),
                     cell(c.get("source")), cell(c.get("notes")))
                    for c in cols]
            out.append(tbl(f"`{name}` — columns ({len(cols)})",
                           ["Column", "Type", "Comes from", "Notes"], rows))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("extraction_dir", type=Path)
    args = ap.parse_args()

    d = args.extraction_dir.resolve()
    spec = load(d, "model_spec.yml")
    profile = load(d, "service_profile.yml", required=False)
    findings = parse_findings(d / "findings.md", Report())
    entities = [e for e in spec.get("entities") or [] if e.get("name")]
    subject_meta = {s["name"]: s for s in spec.get("subjects") or []
                    if s.get("name")}

    fallback = not subject_meta
    order = list(subject_meta) if subject_meta else []
    if fallback:
        order = sorted({str(e.get("app")) for e in entities})

    def key_of(e):
        return str(e.get("app")) if fallback else (e.get("subject") or UNGROUPED)

    groups: dict[str, list] = {}
    for k in order:
        members = [e for e in entities if key_of(e) == k]
        if members:
            groups[k] = sorted(members, key=lambda e: (e.get("layer") != "silver",
                                                       e["name"]))
    stragglers = [e for e in entities if key_of(e) not in groups]
    if stragglers:
        groups[UNGROUPED] = sorted(stragglers, key=lambda e: e["name"])

    # Table captions are numbered across the whole document.
    state = {"n": 0}

    def tbl(caption: str, headers: list[str], rows: list) -> str:
        state["n"] += 1
        head = "| " + " | ".join(headers) + " |"
        rule = "|" + "|".join("---" for _ in headers) + "|"
        body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
        return (f"*Table {state['n']} — {caption}*\n\n{head}\n{rule}\n{body}\n"
                if rows else f"*Table {state['n']} — {caption}: none.*\n")

    classification = (profile.get("security_classification")
                      or "UNSPECIFIED — set `security_classification` in service_profile.yml")
    service = spec.get("service", "?")
    generator = spec.get("generator", "?")

    out: list[str] = []
    out.append(f"# {service} — data model\n")
    out.append(f"**{profile.get('name') or service} · {generator}**\n")
    out.append("| | |\n|---|---|")
    out.append(f"| **Date** | {spec.get('extracted_at')} |")
    out.append(f"| **Version** | commit `{spec.get('source_commit')}` |")
    out.append(f"| **Security classification** | {classification} |")
    out.append(f"| **Status** | Stage 1 extraction — for review |\n")

    out.append("## Document control\n")
    out.append("| | |\n|---|---|")
    out.append("| **Generated by** | `model_doc.py` from `model_spec.yml`, "
               "`findings.md` and `service_profile.yml` |")
    out.append(f"| **Source repository** | `{profile.get('repo') or '—'}` at commit "
               f"`{spec.get('source_commit')}` |")
    out.append(f"| **Covers** | {len(entities)} tables, "
               f"{sum(len(e.get('columns') or []) for e in entities)} columns, "
               f"{len(groups)} subject areas |")
    owner = profile.get("owner")
    if isinstance(owner, dict):
        owner = ", ".join(f"{k}: {v}" for k, v in owner.items())
    out.append(f"| **Owner** | {flow(owner)} |\n")
    out.append("> **Do not edit this file.** It is generated. Every sentence in it comes from\n"
               "> `model_spec.yml`, which is the contract the migration is built from — correct it\n"
               "> there and regenerate, or the two will disagree and the file you edited will lose.\n")
    out.append("> Formatting note: this is Markdown, so Healthdirect Australia typography and brand\n"
               "> colours are not applied here. They apply if this is ever exported to a document or\n"
               "> published as a page.\n")

    out.append("\n## Contents\n")
    out.append("**Part 1 — What the data means**\n")
    for i, subject in enumerate(groups, 1):
        out.append(f"{i}. [{subject}](#{anchor(f'{i}. {subject}')})")
    out.append(f"{len(groups) + 1}. "
               f"[Before anything is built](#{anchor(f'{len(groups) + 1}. Before anything is built')})")
    out.append("\n**Part 2 — Table reference**\n")
    for subject in groups:
        out.append(f"- [{subject}](#{anchor(subject)})")
    out.append("")

    if fallback:
        out.append("> **Note.** This spec declares no `subjects`, so the tables below are grouped by "
                   "the app that builds them rather than by what they are for. Declaring `subjects` "
                   "in `model_spec.yml` gives a reader the business grouping instead.\n")

    part1(out, spec, profile, findings, groups, subject_meta, tbl)
    part2(out, findings, groups, spec.get("relationships") or [], tbl)

    out.append("\n---\n")
    out.append(f"*{service} — data model · commit `{spec.get('source_commit')}` · "
               f"{spec.get('extracted_at')} · {classification} · "
               f"© Healthdirect Australia Ltd*")

    text = "\n".join(out) + "\n"
    (d / "data_model.md").write_text(text, encoding="utf-8")

    # Coverage assertions: a mis-tagged table must not be able to hide.
    placed = sum(len(v) for v in groups.values())
    print(f"wrote {d / 'data_model.md'}")
    print(f"{placed} of {len(entities)} tables placed in {len(groups)} group(s), "
          f"{state['n']} tables captioned")
    if placed != len(entities):
        sys.exit(f"ERROR {len(entities) - placed} table(s) missing from the document")
    if UNGROUPED in groups and not fallback:
        sys.exit(f"ERROR {len(groups[UNGROUPED])} table(s) have no subject: "
                 f"{', '.join(e['name'] for e in groups[UNGROUPED])}")
    n_def = sum(1 for f in findings.values()
                if f.get("fields", {}).get("Class") == "Defect")
    print(f"{len(findings)} findings read, {n_def} defect(s) available to place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
