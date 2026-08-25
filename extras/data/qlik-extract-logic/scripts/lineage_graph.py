#!/usr/bin/env python3
"""Derive lineage from model_spec.yml — entity-level and column-level.

Lineage is never authored separately: it is the per-column `source` and
`derived_from` refs, chained. This script renders them, so there is one place to
maintain the fact and no second section to drift.

Requires: pyyaml  (pip install pyyaml)

Usage:
    python lineage_graph.py <extraction_dir>              # write lineage.md
    python lineage_graph.py <extraction_dir> --column Call_Data_Monthly_tbl.postcode
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
    sys.exit("lineage_graph.py needs pyyaml:  pip install pyyaml")

KEYWORDS = {"derived", "literal", "generated"}
MAX_DEPTH = 24


def node_id(name: str) -> str:
    return "n_" + re.sub(r"\W", "_", name)


def load(d: Path) -> dict:
    p = d / "model_spec.yml"
    if not p.exists():
        sys.exit(f"missing {p}")
    spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(spec, dict):
        sys.exit("model_spec.yml did not parse to a mapping")
    return spec


def index(spec: dict):
    entities = {e["name"]: e for e in spec.get("entities") or []
                if isinstance(e, dict) and e.get("name")}
    sources = {s["id"]: s for s in spec.get("sources") or []
               if isinstance(s, dict) and s.get("id")}
    return entities, sources


# ---------------------------------------------------------------------------
# Column-level chains
# ---------------------------------------------------------------------------

def column_of(entities: dict, entity: str, column: str) -> dict | None:
    ent = entities.get(entity)
    if not ent:
        return None
    for c in ent.get("columns") or []:
        if c.get("name") == column:
            return c
    return None


def trace(entities: dict, sources: dict, entity: str, column: str,
          depth: int = 0, seen: frozenset = frozenset()) -> dict:
    """Walk one column back to its origins. Returns a nested chain node."""
    ref = f"{entity}.{column}"
    node = {"ref": ref, "entity": entity, "column": column,
            "expression": None, "kind": "unknown", "parents": []}

    if depth > MAX_DEPTH or ref in seen:
        node["kind"] = "cycle" if ref in seen else "depth_limit"
        return node

    col = column_of(entities, entity, column)
    if col is None:
        node["kind"] = "source" if entity in sources else "unresolved"
        return node

    node["expression"] = col.get("expression")
    src = col.get("source")
    seen = seen | {ref}

    if src in KEYWORDS:
        node["kind"] = src
        parents = col.get("derived_from") or []
    elif isinstance(src, str) and "." in src:
        node["kind"] = "renamed"
        parents = [src]
    else:
        node["kind"] = "unresolved"
        parents = []

    for p in parents:
        pe, _, pc = str(p).rpartition(".")
        if pe in sources:
            node["parents"].append(
                {"ref": p, "entity": pe, "column": pc, "kind": "source",
                 "expression": None, "parents": []})
        else:
            node["parents"].append(trace(entities, sources, pe, pc, depth + 1, seen))
    return node


def depth_of(node: dict) -> int:
    if not node["parents"]:
        return 1
    return 1 + max(depth_of(p) for p in node["parents"])


def render_chain(node: dict, indent: int = 0, out: list | None = None) -> list[str]:
    out = [] if out is None else out
    pad = "  " * indent
    expr = node.get("expression")
    tag = f' _{node["kind"]}_' if node["kind"] in {
        "source", "literal", "generated", "cycle", "unresolved", "depth_limit"} else ""
    line = f'{pad}- `{node["ref"]}`{tag}'
    if expr:
        one = " ".join(str(expr).split())
        if len(one) > 140:
            one = one[:137] + "..."
        line += f'  \n{pad}  `{one}`'
    out.append(line)
    for p in node["parents"]:
        render_chain(p, indent + 1, out)
    return out


# ---------------------------------------------------------------------------
# Entity-level graph
# ---------------------------------------------------------------------------

def entity_edges(spec: dict, entities: dict, sources: dict) -> list[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for name, ent in entities.items():
        for up in ent.get("upstream") or []:
            edges.add((str(up), name))
        # Column refs are the authoritative edges; upstream is a convenience.
        for col in ent.get("columns") or []:
            refs = []
            src = col.get("source")
            if isinstance(src, str) and src not in KEYWORDS and "." in src:
                refs.append(src)
            refs += [str(r) for r in (col.get("derived_from") or [])]
            for r in refs:
                pe = r.rpartition(".")[0]
                if pe and pe != name and (pe in entities or pe in sources):
                    edges.add((pe, name))
    return sorted(edges)


def fan_out_entities(spec: dict) -> set[str]:
    """Entities whose join to a parent multiplies rows.

    Taken from the relationships' fan_out booleans rather than by reading the
    fan_out_risk prose, which is free text like "none - base fact".
    """
    return {str(r.get("to")) for r in spec.get("relationships") or []
            if r.get("fan_out") is True and r.get("to")}


def mermaid(spec: dict, entities: dict, sources: dict) -> str:
    edges = entity_edges(spec, entities, sources)
    fanned = fan_out_entities(spec)
    lines = ["flowchart LR"]

    used_sources = {s for s, _ in edges if s in sources}
    for group, label in (("human", "Human-maintained (SharePoint)"),
                         ("system", "System sources")):
        members = [s for s in sorted(used_sources)
                   if (sources[s].get("maintained_by") or "system") == group]
        if not members:
            continue
        lines.append(f'  subgraph sg_{group}["{label}"]')
        for s in members:
            ext = sources[s].get("external_service")
            tag = f'{s}<br/><i>{ext}</i>' if ext else s
            lines.append(f'    {node_id(s)}([{tag}])')
        lines.append("  end")

    for layer in ("silver", "gold"):
        members = [n for n in sorted(entities)
                   if entities[n].get("layer") == layer]
        if not members:
            continue
        lines.append(f'  subgraph sg_{layer}["{layer}"]')
        for n in members:
            star = "*" if n in fanned else ""
            lines.append(f'    {node_id(n)}["{n}{star}"]')
        lines.append("  end")

    for a, b in edges:
        lines.append(f"  {node_id(a)} --> {node_id(b)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

def build_doc(spec: dict, entities: dict, sources: dict) -> tuple[str, dict]:
    service = spec.get("service", "?")
    out = [f"# {service} — lineage", "",
           "Generated by `lineage_graph.py` from `model_spec.yml`. Do not edit by "
           "hand: change the per-column `source` / `derived_from` refs in the spec "
           "and regenerate.", "",
           "## Entity-level", "",
           "`*` marks an entity with a non-trivial fan-out risk — joining it to its "
           "parent multiplies rows.", "",
           "```mermaid", mermaid(spec, entities, sources), "```", ""]

    chains = {}
    for name in sorted(entities):
        for col in entities[name].get("columns") or []:
            cname = col.get("name")
            if not cname:
                continue
            ch = trace(entities, sources, name, cname)
            chains[f"{name}.{cname}"] = {"depth": depth_of(ch), "chain": ch}

    deep = sorted(((k, v) for k, v in chains.items() if v["depth"] >= 3),
                  key=lambda kv: -kv[1]["depth"])

    out += ["## Column chains of depth 3 or more", "",
            "The shallow ones are straight renames. These are the ones where a "
            "parity failure could originate at any of several hops.", ""]
    if not deep:
        out.append("_None — every column is at most one hop from a source._")
    for ref, info in deep:
        out += [f'### `{ref}`  (depth {info["depth"]})', ""]
        out += render_chain(info["chain"])
        out.append("")

    problems = {k: v for k, v in chains.items()
                if _has_kind(v["chain"], {"unresolved", "cycle", "depth_limit"})}
    if problems:
        out += ["## Broken chains", "",
                "These do not resolve to a declared source or entity. "
                "`validate_spec.py` fails on them.", ""]
        for ref in sorted(problems):
            out.append(f"- `{ref}`")
        out.append("")

    notes = spec.get("lineage_notes") or []
    out += ["## What column refs cannot express", ""]
    if not notes:
        out.append("_No notes recorded — verify this is genuinely the case._")
    for n in notes:
        out.append(f'- **{n.get("kind", "?")}**'
                   + (f' ({n["entity"]})' if n.get("entity") else "")
                   + f': {n.get("detail", "")}')
    out.append("")

    graph = {
        "service": service,
        "edges": [{"from": a, "to": b}
                  for a, b in entity_edges(spec, entities, sources)],
        "column_chains": {k: {"depth": v["depth"], "chain": v["chain"]}
                          for k, v in chains.items()},
    }
    return "\n".join(out), graph


def _has_kind(node: dict, kinds: set[str]) -> bool:
    if node["kind"] in kinds:
        return True
    return any(_has_kind(p, kinds) for p in node["parents"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("extraction_dir", type=Path)
    ap.add_argument("--column", help="trace one column: <entity>.<column>")
    args = ap.parse_args()

    d = args.extraction_dir.resolve()
    spec = load(d)
    entities, sources = index(spec)

    if args.column:
        ent, _, col = args.column.rpartition(".")
        if ent not in entities:
            sys.exit(f"unknown entity {ent!r}")
        chain = trace(entities, sources, ent, col)
        print(f"{args.column}  (depth {depth_of(chain)})")
        print("\n".join(render_chain(chain)))
        return 0

    doc, graph = build_doc(spec, entities, sources)
    (d / "lineage.md").write_text(doc + "\n", encoding="utf-8")
    (d / "lineage.json").write_text(json.dumps(graph, indent=2) + "\n",
                                    encoding="utf-8")
    print(f'wrote {d / "lineage.md"}')
    print(f'wrote {d / "lineage.json"}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
