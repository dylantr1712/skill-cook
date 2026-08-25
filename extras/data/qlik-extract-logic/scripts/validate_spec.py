#!/usr/bin/env python3
"""Coverage gate for a Qlik extraction bundle.

Checks model_spec.yml against SPEC-SCHEMA.md's required fields, resolves every
lineage reference, and cross-checks the spec against inventory.json so nothing
found in the source can be silently omitted. Non-zero exit means the extraction
is not complete.

Requires: pyyaml  (pip install pyyaml)

Usage:
    python validate_spec.py <extraction_dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("validate_spec.py needs pyyaml:  pip install pyyaml")

SPEC_VERSION = 1
KEYWORD_SOURCES = {"derived", "literal", "generated"}
CLASSES = {
    "Defect": "D",
    "Migration hazard": "H",
    "Refactor opportunity": "R",
    "Dead code": "X",
}
PLACEHOLDERS = {"", "unknown", "tbd", "todo", "n/a", "?", "-"}

RE_FINDING_HEAD = re.compile(
    r"^###\s+(?P<id>[A-Z][A-Z0-9]*-(?P<cls>[DHRX])-(?P<num>\d{3}))\b(?P<rest>.*)$")
RE_FIELD = re.compile(r"^\s*[-*]\s*\*\*(?P<key>[^:*]+):\*\*\s*(?P<val>.*)$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def blank(value) -> bool:
    return value is None or (isinstance(value, str)
                             and value.strip().lower() in PLACEHOLDERS)


def not_prose(value) -> bool:
    """True when a field that must be a sentence is missing or not a string.

    Guards the YAML 1.1 boolean trap: `fan_out_risk: no` parses to False, which
    is not blank and would otherwise pass. These fields must be written as text.
    """
    return blank(value) or not isinstance(value, str)


# ---------------------------------------------------------------------------
# findings.md
# ---------------------------------------------------------------------------

def parse_findings(path: Path, rep: Report) -> dict[str, dict]:
    if not path.exists():
        rep.err("findings.md", "missing")
        return {}

    findings: dict[str, dict] = {}
    current: dict | None = None
    key: str | None = None
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        head = RE_FINDING_HEAD.match(line)
        if head:
            fid = head.group("id")
            if fid in findings:
                rep.err(f"findings.md:{lineno}", f"duplicate finding id {fid}")
            # `title` is the text after the id on the ### line - the finding's
            # one-line summary, which model_doc.py renders.
            current = {"id": fid, "class_letter": head.group("cls"),
                       "line": lineno, "fields": {},
                       "title": re.sub(r"^\s*[-–—]\s*", "",
                                       head.group("rest")).strip()}
            findings[fid] = current
            key = None
            continue
        if line.startswith("###"):
            # A section heading that is not a well-formed finding id.
            rep.err(f"findings.md:{lineno}",
                    f"heading is not a valid finding id: {line.strip()[:60]!r}")
            current = None
            key = None
            continue
        if current is not None:
            f = RE_FIELD.match(line)
            if f:
                key = f.group("key").strip()
                current["fields"][key] = f.group("val").strip()
            elif not line.strip():
                # A blank line ends the field. Everything after it - code
                # fences, tables, further paragraphs - is detail, not the
                # summary value, so it is deliberately not accumulated.
                key = None
            elif key:
                current["fields"][key] += " " + line.strip()

    for fid, f in findings.items():
        where = f'findings.md:{f["line"]}'
        cls = f["fields"].get("Class")
        if not cls:
            rep.err(where, f"{fid} has no **Class:** line")
        elif cls not in CLASSES:
            rep.err(where, f"{fid} class {cls!r} not one of {sorted(CLASSES)}")
        elif CLASSES[cls] != f["class_letter"]:
            rep.err(where,
                    f'{fid} id letter "{f["class_letter"]}" contradicts class {cls!r} '
                    f'(expected {CLASSES[cls]})')
        for required in ("Evidence", "Current behaviour", "Stage 1"):
            if blank(f["fields"].get(required)):
                rep.err(where, f"{fid} missing **{required}:**")
    return findings


# ---------------------------------------------------------------------------
# spec structure
# ---------------------------------------------------------------------------

def check_top_level(spec: dict, rep: Report) -> None:
    for key in ("spec_version", "service", "generator", "extracted_at",
                "source_commit", "scope", "apps", "sources", "entities",
                "relationships", "metrics", "parameters", "calendar"):
        if key not in spec:
            rep.err("model_spec.yml", f"missing required top-level key {key!r}")
    if spec.get("spec_version") != SPEC_VERSION:
        rep.err("model_spec.yml",
                f"spec_version must be {SPEC_VERSION}, got {spec.get('spec_version')!r}")


def check_sources(spec: dict, rep: Report) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for i, src in enumerate(spec.get("sources") or []):
        where = f"sources[{i}]"
        sid = src.get("id")
        if blank(sid):
            rep.err(where, "missing id")
            continue
        if sid in by_id:
            rep.err(where, f"duplicate source id {sid!r}")
        by_id[sid] = src
        for key in ("system", "object", "maintained_by"):
            if blank(src.get(key)):
                rep.err(f"{where} ({sid})", f"missing {key!r}")
        if src.get("maintained_by") not in (None, "system", "human"):
            rep.err(f"{where} ({sid})",
                    "maintained_by must be 'system' or 'human'")
    return by_id


def check_entities(spec: dict, rep: Report) -> dict[str, dict]:
    by_name: dict[str, dict] = {}
    for i, ent in enumerate(spec.get("entities") or []):
        where = f"entities[{i}]"
        name = ent.get("name")
        if blank(name):
            rep.err(where, "missing name")
            continue
        if name in by_name:
            rep.err(where, f"duplicate entity name {name!r}")
        by_name[name] = ent
        where = f"{where} ({name})"

        for key in ("layer", "app", "script"):
            if blank(ent.get(key)):
                rep.err(where, f"{key!r} is required and must not be a placeholder")
        for key in ("grain", "fan_out_risk"):
            if not_prose(ent.get(key)):
                rep.err(where, f"{key!r} must be a sentence describing the actual "
                               f"case (got {ent.get(key)!r})")
        if ent.get("layer") not in (None, "silver", "gold"):
            rep.err(where, "layer must be 'silver' or 'gold'")

        # An entity loading a QVD that nothing in the repo produces has a
        # genuinely unknowable schema. Declaring that is legitimate; inventing a
        # placeholder column to satisfy the count below is not. The reason and
        # the finding are mandatory so an empty entity cannot be added quietly.
        if ent.get("schema_recoverable") is False:
            for key in ("schema_recoverable_reason", "finding"):
                if blank(ent.get(key)):
                    rep.err(where, f"schema_recoverable: false requires {key!r}")
            if ent.get("columns"):
                rep.err(where, "schema_recoverable: false but columns are "
                               "declared - drop the flag or drop the columns")
            rep.warn(where, f"schema not recoverable, so this entity is a hole in "
                            f"the model: {ent.get('schema_recoverable_reason')} "
                            f"[{ent.get('finding')}]")
            continue

        cols = ent.get("columns")
        if not cols:
            rep.err(where, "must declare at least one column")
            continue
        seen: set[str] = set()
        for j, col in enumerate(cols):
            cwhere = f"{where}.columns[{j}]"
            cname = col.get("name")
            if blank(cname):
                rep.err(cwhere, "missing name")
                continue
            if cname in seen:
                rep.err(cwhere, f"duplicate column {cname!r}")
            seen.add(cname)
            cwhere = f"{where}.{cname}"
            if blank(col.get("source")):
                rep.err(cwhere, "source is required (upstream ref, derived, "
                                "literal or generated)")
            if blank(col.get("expression")):
                rep.err(cwhere, "expression is required (verbatim from the script)")
            if col.get("source") == "derived" and not col.get("derived_from"):
                rep.err(cwhere, "source 'derived' requires a non-empty derived_from")
            if "Dual(" in str(col.get("expression", "")) and not col.get("dual"):
                rep.warn(cwhere, "Dual() expression without a dual.sort_key "
                                 "- sort order will be lost in dbt")
    return by_name


def resolve_refs(entities: dict[str, dict], sources: dict[str, dict],
                 rep: Report) -> None:
    """Every lineage ref must land somewhere. A dangling hop breaks the graph."""

    def check(ref: str, where: str) -> None:
        if not isinstance(ref, str) or "." not in ref:
            rep.err(where, f"ref {ref!r} is not <id>.<column> nor a keyword")
            return
        prefix, _, column = ref.rpartition(".")
        if prefix in entities:
            cols = {c.get("name") for c in entities[prefix].get("columns") or []}
            if column not in cols:
                rep.err(where,
                        f"ref {ref!r} names entity {prefix!r} which has no "
                        f"column {column!r}")
            return
        # Source refs: the column cannot be verified (we have no source schema),
        # but the source itself must be declared.
        if prefix in sources or any(prefix == sid for sid in sources):
            return
        rep.err(where, f"ref {ref!r} resolves to neither an entity nor a "
                       f"declared source ({prefix!r} unknown)")

    for name, ent in entities.items():
        for col in ent.get("columns") or []:
            cwhere = f"entities.{name}.{col.get('name')}"
            src = col.get("source")
            if src in KEYWORD_SOURCES:
                pass
            elif isinstance(src, str) and src:
                check(src, f"{cwhere}.source")
            for k, dref in enumerate(col.get("derived_from") or []):
                check(dref, f"{cwhere}.derived_from[{k}]")
        for up in ent.get("upstream") or []:
            if up not in sources and up not in entities:
                rep.err(f"entities.{name}.upstream",
                        f"{up!r} is neither a declared source nor an entity")


def check_subjects(spec: dict, entities: dict[str, dict], rep: Report) -> None:
    """Business subject areas, if the spec groups its entities into them.

    Optional, because it is the one part of the spec that is not recoverable
    from the scripts - it is a reading of what each table is FOR. But once
    declared it must be complete, or data_model.md silently drops entities into
    an "ungrouped" bucket nobody reads.
    """
    subjects = spec.get("subjects")
    if not subjects:
        return
    names: set[str] = set()
    for i, s in enumerate(subjects):
        where = f"subjects[{i}]"
        name = s.get("name")
        if blank(name):
            rep.err(where, "missing name")
            continue
        if name in names:
            rep.err(where, f"duplicate subject {name!r}")
        names.add(name)
        if not_prose(s.get("describes")):
            rep.err(f"{where} ({name})",
                    "'describes' must be a sentence a non-technical reader can "
                    "follow - it is the opening of that section in data_model.md")

    used: set[str] = set()
    for name, ent in entities.items():
        sub = ent.get("subject")
        if blank(sub):
            rep.err(f"entities.{name}",
                    "'subject' is required once 'subjects' is declared")
        elif sub not in names:
            rep.err(f"entities.{name}",
                    f"subject {sub!r} is not a declared subject")
        else:
            used.add(sub)
    for unused in sorted(names - used):
        rep.warn("subjects", f"subject {unused!r} has no entities - a rename "
                             f"that half-landed, or a group that never arrived")


def check_relationships(spec: dict, entities: dict[str, dict], rep: Report) -> None:
    valid_card = {"one_to_one", "one_to_many", "many_to_many"}
    valid_mech = {"qlik_association", "explicit_join", "mapping"}
    for i, rel in enumerate(spec.get("relationships") or []):
        where = f"relationships[{i}]"
        # NB: the key is `join_keys`, never `on`. In YAML 1.1 (which PyYAML
        # implements) a bare `on` is the boolean True, so an `on:` key silently
        # disappears from the parsed mapping.
        if "on" in rel or True in rel:
            rep.err(where, "use 'join_keys', not 'on' - bare 'on' is a YAML 1.1 "
                           "boolean and parses as the key True")
        for key in ("from", "to", "cardinality", "mechanism", "app"):
            if blank(rel.get(key)):
                rep.err(where, f"missing {key!r}")
        if "fan_out" not in rel:
            rep.err(where, "missing 'fan_out' (true/false)")
        if rel.get("cardinality") not in valid_card | {None}:
            rep.err(where, f"cardinality must be one of {sorted(valid_card)}")
        if rel.get("mechanism") not in valid_mech | {None}:
            rep.err(where, f"mechanism must be one of {sorted(valid_mech)}")
        keys = rel.get("join_keys")
        if blank(keys):
            rep.err(where, "missing 'join_keys'")
        elif isinstance(keys, str):
            rep.err(where, "'join_keys' must be a list of key columns, not a string")
        for side in ("from", "to"):
            tbl = rel.get(side)
            if tbl and tbl not in entities:
                rep.warn(where, f"{side} table {tbl!r} is not a declared entity")


def check_metrics(spec: dict, rep: Report) -> None:
    metrics = spec.get("metrics") or {}
    if not isinstance(metrics, dict):
        rep.err("metrics", "must be a mapping with 'recovered' and 'todo'")
        return
    for key in ("recovered", "todo"):
        if key not in metrics:
            rep.err("metrics", f"missing {key!r} list (use [] if genuinely none)")
    for i, m in enumerate(metrics.get("recovered") or []):
        where = f"metrics.recovered[{i}]"
        for key in ("name", "expression", "grain", "business_rule"):
            if blank(m.get(key)):
                rep.err(where, f"missing {key!r}")
    for i, m in enumerate(metrics.get("todo") or []):
        where = f"metrics.todo[{i}]"
        for key in ("name", "app", "evidence"):
            if blank(m.get(key)):
                rep.err(where, f"missing {key!r}")


def check_parameters(spec: dict, rep: Report) -> None:
    for i, p in enumerate(spec.get("parameters") or []):
        where = f"parameters[{i}]"
        for key in ("name", "defined_in"):
            if blank(p.get(key)):
                rep.err(where, f"missing {key!r}")


def check_calendar(spec: dict, rep: Report) -> None:
    cal = spec.get("calendar") or {}
    for key in ("fy_start_month", "first_week_day", "broken_weeks"):
        if cal.get(key) is None:
            rep.err("calendar", f"missing {key!r}")


def check_scope(spec: dict, entities: dict[str, dict], rep: Report) -> set[str]:
    """Incompleteness must be declared, not inferred.

    A silver-only extraction is a legitimate staged delivery, but it has to say
    so. Without this, a bundle covering none of the gold layer passed the gate
    with only warnings - exactly the false PASS the gate exists to prevent.
    """
    scope = spec.get("scope") or {}
    layers = scope.get("layers")
    if not isinstance(layers, list) or not layers:
        rep.err("scope", "must declare 'layers', e.g. [silver] or [silver, gold]")
        return set()
    layers = {str(x) for x in layers}
    unknown = layers - {"silver", "gold"}
    if unknown:
        rep.err("scope", f"unknown layer(s) {sorted(unknown)}")

    declared_gold_apps = [a.get("name") for a in spec.get("apps") or []
                          if a.get("layer") == "gold"]
    have = {e.get("layer") for e in entities.values()}

    for layer in sorted(layers):
        if layer not in have:
            rep.err("scope", f"layer {layer!r} is in scope but no entity declares it")

    if "gold" in layers:
        if not (spec.get("relationships") or []):
            rep.err("scope", "gold is in scope but 'relationships' is empty - the "
                             "associative model is the gold layer's join model")
        if not (spec.get("dimensions") or []):
            rep.err("scope", "gold is in scope but 'dimensions' is empty")
    elif declared_gold_apps:
        if not scope.get("deferred_note"):
            rep.err("scope", f"gold is out of scope while apps {declared_gold_apps} "
                             f"are declared gold - add scope.deferred_note saying "
                             f"what is outstanding and where it is tracked")
        else:
            print(f"NOTE  scope: gold deferred for {declared_gold_apps} "
                  f"- {scope['deferred_note']}")
    return layers


def check_fidelity(spec: dict, repo: Path, rep: Report) -> tuple[int, int]:
    """Prove the spec quotes the scripts, rather than trusting that it does.

    Two checks the rest of the gate cannot make:
      - the entity's script exists and its line range is inside the file
      - every column expression appears verbatim in that script

    Whitespace is normalised (the spec may wrap a long expression), but nothing
    else is: a normalised en-dash, a changed case or a dropped operator all fail
    here, which is the point.
    """
    cache: dict[tuple, str] = {}

    def body(app, script):
        key = (app, script)
        if key not in cache:
            p = repo / str(app) / str(script)
            cache[key] = (re.sub(r"\s+", " ", p.read_text(encoding="utf-8",
                                                          errors="replace"))
                          if p.exists() else "")
        return cache[key]

    # `entities[].app` is the repo-relative *directory* holding the script, which
    # is not always the app's name - directories may carry a suffix. Checking the
    # directory once, by name, beats one "script does not exist" error per entity.
    declared_dirs = {str(a.get("directory") or a.get("name"))
                     for a in spec.get("apps") or []}
    bad_dirs: set[str] = set()
    for app in dict.fromkeys(str(e.get("app")) for e in spec.get("entities") or []):
        if not (repo / app).is_dir():
            bad_dirs.add(app)
            rep.err("entities", f"app {app!r} is not a directory under {repo} - "
                                f"`app` must be the repo-relative folder holding "
                                f"`script`, which may differ from the app's name")
        elif app not in declared_dirs:
            rep.warn("entities", f"app {app!r} matches no apps[].directory or "
                                 f"apps[].name - declare the directory so the two "
                                 f"names cannot drift")

    checked = missing = 0
    for ent in spec.get("entities") or []:
        name, app, script = ent.get("name"), ent.get("app"), ent.get("script")
        if str(app) in bad_dirs:
            continue
        p = repo / str(app) / str(script)
        if not p.exists():
            rep.err(f"entities.{name}", f"script {app}/{script} does not exist")
            continue
        total = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        m = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*$", str(ent.get("lines", "")))
        if not m:
            rep.err(f"entities.{name}",
                    f'lines {ent.get("lines")!r} is not "N-M"')
        else:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo < 1 or lo > hi:
                rep.err(f"entities.{name}", f"lines {lo}-{hi} malformed")
            elif hi > total:
                rep.err(f"entities.{name}",
                        f"lines {lo}-{hi} exceeds {script} length {total}")

        hay = body(app, script)
        for col in ent.get("columns") or []:
            expr = col.get("expression")
            if not expr or col.get("source") in ("literal", "generated"):
                continue
            needle = re.sub(r"\s+", " ", str(expr)).strip()
            # Annotations describing a Qlik association are prose, not code.
            if needle.lower().startswith(("association", "see ", "pattern",
                                          "n/a", "--", "derived in ")):
                continue
            checked += 1
            if needle not in hay:
                missing += 1
                rep.err(f"entities.{name}.{col.get('name')}",
                        f"expression not found verbatim in {script}: "
                        f"{needle[:100]}")
    return checked, missing


def check_finding_links(spec: dict, findings: dict[str, dict], rep: Report) -> None:
    """Any finding id named in the spec must exist in findings.md."""
    text = yaml.safe_dump(spec, allow_unicode=True)
    for fid in set(re.findall(r"\b[A-Z][A-Z0-9]*-[DHRX]-\d{3}\b", text)):
        if fid not in findings:
            rep.err("model_spec.yml",
                    f"references finding {fid} which is not in findings.md")


# ---------------------------------------------------------------------------
# inventory cross-check
# ---------------------------------------------------------------------------

def check_coverage(spec: dict, inv: dict, entities: dict[str, dict],
                   sources: dict[str, dict], layers: set[str],
                   rep: Report) -> None:
    dead = spec.get("dead_code") or []
    dead_paths = {str(d.get("artefact", "")).strip() for d in dead}

    # The inventory is repo-wide; a bundle covers one generator. A repo holding
    # several generators therefore presents STORE targets that are neither this
    # bundle's work nor dead - they are live outputs owned by another bundle.
    # Without somewhere to say that, the only way past this gate is to call them
    # dead code, which later reads as "not migrated".
    oos = spec.get("out_of_scope") or []
    oos_paths = {str(o.get("artefact", "")).strip() for o in oos}
    for i, o in enumerate(oos):
        for key in ("artefact", "app", "owner_bundle", "reason"):
            if blank(o.get(key)):
                rep.err(f"out_of_scope[{i}]", f"missing {key!r}")
        if str(o.get("artefact", "")).strip() in dead_paths:
            rep.err(f"out_of_scope[{i}]",
                    f'{o.get("artefact")!r} is also in dead_code - an artefact is '
                    f"either dead or owned elsewhere, not both")
    if oos:
        owners = sorted({str(o.get("owner_bundle")) for o in oos
                         if not blank(o.get("owner_bundle"))})
        print(f"NOTE  out_of_scope: {len(oos)} live artefact(s) owned by other "
              f"bundle(s): {', '.join(owners) or 'UNNAMED - see errors'}")

    # Every STORE target must be an entity or explicitly dead.
    artefacts = {}
    for name, ent in entities.items():
        art = str(ent.get("artefact") or "")
        if art:
            artefacts[art.rsplit("/", 1)[-1]] = name

    for st in inv.get("stores") or []:
        where = f'{st["file"]}:{st["line"]}'
        if not st.get("resolved"):
            if st["path"] not in dead_paths and st["path"] not in oos_paths:
                rep.err(where,
                        f'STORE to unresolved path {st["path"]} is not declared '
                        f'in dead_code or out_of_scope')
            continue
        qvd = st["qvd"]
        stem = qvd[:-4] if qvd.lower().endswith(".qvd") else qvd
        if (qvd in artefacts or stem in entities or qvd in dead_paths
                or qvd in oos_paths):
            continue
        rep.err(where, f"STORE target {qvd!r} has no matching entity "
                       f"(expected entity named {stem!r}, or artefact ending "
                       f"{qvd!r}, or a dead_code / out_of_scope entry)")

    # Every SQL source found in the scripts must be declared.
    declared = {(str(s.get("database", "")).lower(), str(s.get("object", "")).lower())
                for s in sources.values()}
    for src in inv.get("sql_sources") or []:
        key = (src["database"], src["object"])
        if key not in declared:
            rep.err(f'{src["referenced_in"][0]}',
                    f'SQL source {src["database"]}.{src["object"]} is not '
                    f'declared in spec sources')

    # Every external QVD dependency must be a declared source.
    for ext in inv.get("summary", {}).get("external_qvd_dependencies") or []:
        if not any(str(s.get("external_service", "")).upper() == ext["service"].upper()
                   for s in sources.values()):
            rep.err("model_spec.yml",
                    f'external QVD dependency on {ext["service"]} '
                    f'({ext["qvd"]}) is not declared as a source with '
                    f'external_service: {ext["service"]}')

    # Association keys are the join model; each should appear in a relationship.
    rel_keys = set()
    for rel in spec.get("relationships") or []:
        keys = rel.get("join_keys")
        if isinstance(keys, list):
            rel_keys.update(str(k) for k in keys)
    missing_keys = [k for k in inv.get("summary", {}).get("association_keys") or []
                    if k not in rel_keys]
    if missing_keys:
        if "gold" in layers:
            for key in missing_keys:
                rep.warn("relationships",
                         f"association key {key!r} is unqualified in the scripts "
                         f"but appears in no relationship")
        else:
            # Expected while gold is deferred: the keys live in the consumer apps.
            print(f"NOTE  relationships: {len(missing_keys)} association key(s) "
                  f"deferred with the gold layer: {', '.join(missing_keys)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("extraction_dir", type=Path)
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as errors")
    ap.add_argument("--repo", type=Path, default=None,
                    help="repo root holding the app folders "
                         "(default: parent of extraction_dir)")
    ap.add_argument("--fidelity-only", action="store_true",
                    help="run only the verbatim expression check - the authoring "
                         "loop, not the completion gate")
    ap.add_argument("--entity", action="append", default=None, metavar="NAME",
                    help="restrict to this entity (repeatable). Implies "
                         "--fidelity-only, since the coverage checks are only "
                         "meaningful over the whole spec")
    args = ap.parse_args()

    d = args.extraction_dir.resolve()
    spec_path = d / "model_spec.yml"
    inv_path = d / "inventory.json"

    if not spec_path.exists():
        sys.exit(f"missing {spec_path}")

    rep = Report()
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    if not isinstance(spec, dict):
        sys.exit("model_spec.yml did not parse to a mapping")

    # Bundles live at <repo>/extraction/<generator>/, so the repo root is two
    # levels up when the convention is in use, one level up otherwise.
    if args.repo:
        repo = args.repo.resolve()
    elif d.parent.name.lower() == "extraction":
        repo = d.parent.parent.resolve()
    else:
        repo = d.parent.resolve()

    if args.entity or args.fidelity_only:
        if args.entity:
            want = set(args.entity)
            unknown = want - {e.get("name") for e in spec.get("entities") or []}
            if unknown:
                sys.exit(f"no such entity: {', '.join(sorted(unknown))}")
            spec["entities"] = [e for e in spec["entities"]
                               if e.get("name") in want]
        n_expr, n_bad = check_fidelity(spec, repo, rep)
        for e in rep.errors:
            print(f"ERROR {e}")
        n_ent = len(spec.get("entities") or [])
        print(f"\n{n_ent} entit{'y' if n_ent == 1 else 'ies'}, {n_expr} "
              f"expression(s) checked verbatim, {n_bad} mismatched")
        if rep.errors:
            print("FAIL - not the full gate; run without --fidelity-only/--entity "
                  "to complete the extraction")
            return 1
        print("OK - fidelity only. The full gate has not run.")
        return 0

    findings = parse_findings(d / "findings.md", rep)
    check_top_level(spec, rep)
    sources = check_sources(spec, rep)
    entities = check_entities(spec, rep)
    resolve_refs(entities, sources, rep)
    check_subjects(spec, entities, rep)
    check_relationships(spec, entities, rep)
    check_metrics(spec, rep)
    check_parameters(spec, rep)
    check_calendar(spec, rep)
    layers = check_scope(spec, entities, rep)

    gen = spec.get("generator")
    if gen and d.parent.name.lower() == "extraction" and d.name != gen:
        rep.err("generator",
                f"spec says generator {gen!r} but the folder is named "
                f"{d.name!r} - the extraction folder must be named after the "
                f"generator app")
    n_expr, n_bad = check_fidelity(spec, repo, rep)
    check_finding_links(spec, findings, rep)

    if inv_path.exists():
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
        check_coverage(spec, inv, entities, sources, layers, rep)
    else:
        rep.err("inventory.json", "missing - run qvs_inventory.py first")

    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")

    n_ent = len(entities)
    n_col = sum(len(e.get("columns") or []) for e in entities.values())
    print(f"\n{n_ent} entities, {n_col} columns, {len(sources)} sources, "
          f"{len(findings)} findings")
    print(f"{n_expr} expression(s) checked verbatim against the scripts, "
          f"{n_bad} mismatched")
    print(f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")

    if rep.errors or (args.strict and rep.warnings):
        print("FAIL - extraction is not complete")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
