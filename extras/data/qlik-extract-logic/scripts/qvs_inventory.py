#!/usr/bin/env python3
"""Extract the mechanical facts from a Qlik service repo's .qvs scripts.

Stdlib only. Produces inventory.json, which validate_spec.py uses as the coverage
baseline: everything this finds must be accounted for in model_spec.yml.

Usage:
    python qvs_inventory.py <repo_dir> [-o inventory.json] [--service PBB] [--summary]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Comment stripping
#
# Must be a state machine, not a regex: QVD library paths contain "//"
# (lib://QVDs Staging/PBB/...) and appear BOTH single-quoted and inside square
# brackets, which is Qlik's other literal form. Miss either and a naive stripper
# eats every path in the repo. Comments are replaced with spaces so byte
# offsets, and therefore line numbers, stay accurate.
# ---------------------------------------------------------------------------

(NORMAL, SQUOTE, DQUOTE, BRACKET,
 LINE_COMMENT, BLOCK_COMMENT, REM_COMMENT) = range(7)


def strip_comments(text: str) -> str:
    out = list(text)
    state = NORMAL
    i = 0
    n = len(text)
    # True while only whitespace has been seen since the last statement break,
    # which is where a REM statement is allowed to start.
    at_stmt_start = True

    def blank(idx: int) -> None:
        if out[idx] != "\n":
            out[idx] = " "

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if state == NORMAL:
            if ch == "'":
                state = SQUOTE
                at_stmt_start = False
            elif ch == '"':
                state = DQUOTE
                at_stmt_start = False
            elif ch == "[":
                # Qlik's second literal form: file paths and quoted field names.
                # Contents are never code, so pass through untouched.
                state = BRACKET
                at_stmt_start = False
            elif ch == "/" and nxt == "/":
                state = LINE_COMMENT
                blank(i)
                blank(i + 1)
                i += 2
                continue
            elif ch == "/" and nxt == "*":
                state = BLOCK_COMMENT
                blank(i)
                blank(i + 1)
                i += 2
                continue
            elif at_stmt_start and text[i : i + 3].upper() == "REM" and (
                i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")
            ):
                state = REM_COMMENT
                blank(i)
                i += 1
                continue
            elif ch == ";":
                at_stmt_start = True
            elif not ch.isspace():
                at_stmt_start = False

        elif state == SQUOTE:
            if ch == "'":
                # Qlik escapes a quote by doubling it.
                if nxt == "'":
                    i += 2
                    continue
                state = NORMAL

        elif state == DQUOTE:
            if ch == '"':
                state = NORMAL

        elif state == BRACKET:
            if ch == "]":
                state = NORMAL

        elif state == LINE_COMMENT:
            if ch == "\n":
                state = NORMAL
                at_stmt_start = True
            else:
                blank(i)

        elif state == BLOCK_COMMENT:
            if ch == "*" and nxt == "/":
                blank(i)
                blank(i + 1)
                state = NORMAL
                i += 2
                continue
            blank(i)

        elif state == REM_COMMENT:
            if ch == ";":
                state = NORMAL
                at_stmt_start = True
            else:
                blank(i)

        i += 1

    return "".join(out)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

RE_STORE = re.compile(
    r"\bSTORE\s+(?P<table>[\w.]+)\s+INTO\s*\[(?P<path>[^\]]+)\]", re.I)
RE_QVD_LOAD = re.compile(r"\bFROM\s*\[(?P<path>[^\]]*\.qvd)\]", re.I)
RE_SQL_FROM = re.compile(
    r"\b(?:FROM|JOIN)\s+\"?(?P<db>[a-z0-9_]+)\"?\s*\.\s*\"?(?P<obj>[a-z0-9_]+)\"?",
    re.I)
RE_VAR = re.compile(
    r"^\s*(?P<kw>LET|SET)\s+(?P<name>[A-Za-z_]\w*)\s*=(?P<value>[^;]*);", re.I | re.M)
RE_DOLLAR = re.compile(r"\$\(([A-Za-z_]\w*)\)")
RE_UNQUALIFY = re.compile(r"\bUnqualify\s+(?P<fields>[^;]+);", re.I)
RE_QUALIFY = re.compile(r"\bQualify\s+(?P<fields>[^;]+);", re.I)
RE_SUB = re.compile(r"\bSUB\s+(?P<name>\w+)", re.I)
RE_CALL = re.compile(r"\bCALL\s+(?P<name>\w+)", re.I)
RE_TAG = re.compile(r"\bTAG\s+FIELD\s+(?P<field>[\w.]+)\s+WITH\s+(?P<tags>[^;]+);", re.I)
RE_TABLE_LABEL = re.compile(r"^[ \t]*(?P<name>[A-Za-z_][\w.]*)[ \t]*:[ \t]*$", re.M)
RE_INLINE = re.compile(r"\bLOAD\s+\*?\s*INLINE\b", re.I)
RE_MAPPING = re.compile(r"\bMAPPING\s+LOAD\b", re.I)
RE_ERRORMODE = re.compile(r"\bSET\s+ErrorMode\s*=\s*(?P<mode>\d)", re.I)
RE_LIBCONNECT = re.compile(r"\bLIB\s+CONNECT\s+TO\s+'(?P<conn>[^']+)'", re.I)
RE_JOIN_KW = re.compile(r"\b(LEFT|INNER|RIGHT|OUTER)?\s*JOIN\s*\(", re.I)
RE_CONCATENATE = re.compile(r"\bCONCATENATE\s*\(", re.I)
RE_NOCONCAT = re.compile(r"\bNoConcatenate\b", re.I)
RE_WHILE_ITER = re.compile(r"\bWHILE\b[^;]*\bIterNo\s*\(", re.I | re.S)
RE_PEEK = re.compile(r"\bPeek\s*\(\s*'(?P<field>[^']*)'\s*,[^,)]*,\s*'(?P<table>[^']*)'", re.I)
RE_EXISTS = re.compile(r"\bExists\s*\(", re.I)
RE_LIB_QVD_PATH = re.compile(r"lib://QVDs\s+(?P<root>\w+)/(?P<service>[^/]+)/", re.I)


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


# ---------------------------------------------------------------------------
# LOAD field lists
#
# The LOAD field list is a table's real output schema, and each field expression
# is what the spec must record verbatim. Splitting it here rather than by eye is
# the difference between character-accurate expressions and typos: a normalised
# en-dash or dropped quote silently changes results.
# ---------------------------------------------------------------------------

RE_LOAD_START = re.compile(r"\bLOAD\b", re.I)
RE_TERMINATOR = re.compile(
    r"\b(RESIDENT|FROM|INLINE|AUTOGENERATE|SQL)\b", re.I)


def split_top_level(text: str, sep: str = ",") -> list[str]:
    """Split on separators at nesting depth zero, respecting Qlik literals."""
    parts, buf, depth = [], [], 0
    state = NORMAL
    for ch in text:
        if state == NORMAL:
            if ch == "'":
                state = SQUOTE
            elif ch == '"':
                state = DQUOTE
            elif ch == "[":
                state = BRACKET
            elif ch in "(":
                depth += 1
            elif ch in ")":
                depth -= 1
            elif ch == sep and depth == 0:
                parts.append("".join(buf))
                buf = []
                continue
        elif state == SQUOTE and ch == "'":
            state = NORMAL
        elif state == DQUOTE and ch == '"':
            state = NORMAL
        elif state == BRACKET and ch == "]":
            state = NORMAL
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def find_statement_end(code: str, start: int) -> int:
    """Offset of the `;` ending the statement beginning at `start`."""
    state = NORMAL
    i = start
    while i < len(code):
        ch = code[i]
        if state == NORMAL:
            if ch == "'":
                state = SQUOTE
            elif ch == '"':
                state = DQUOTE
            elif ch == "[":
                state = BRACKET
            elif ch == ";":
                return i
        elif state == SQUOTE and ch == "'":
            state = NORMAL
        elif state == DQUOTE and ch == '"':
            state = NORMAL
        elif state == BRACKET and ch == "]":
            state = NORMAL
        i += 1
    return len(code)


def extract_loads(code: str) -> list[dict]:
    """One entry per LOAD, with its field expressions split verbatim."""
    loads = []
    labels = [(m.start(), m.group("name"))
              for m in RE_TABLE_LABEL.finditer(code)]

    for m in RE_LOAD_START.finditer(code):
        stmt_start = m.end()
        stmt_end = find_statement_end(code, stmt_start)
        body = code[stmt_start:stmt_end]

        # The field list runs up to the first source clause, if any.
        term = RE_TERMINATOR.search(body)
        field_text = body[:term.start()] if term else body
        clause = body[term.start():].strip() if term else ""

        # DISTINCT is a property of the LOAD, not part of the first field.
        distinct = bool(re.match(r"\s*DISTINCT\b", field_text, re.I))
        if distinct:
            field_text = re.sub(r"^\s*DISTINCT\b", "", field_text, count=1,
                                flags=re.I)

        fields = split_top_level(field_text)
        if not fields:
            continue

        # Attribute to the nearest preceding table label.
        table = None
        for off, name in labels:
            if off < m.start():
                table = name
            else:
                break

        loads.append({
            "table": table,
            "line": line_of(code, m.start()),
            "distinct": distinct,
            "source_clause": " ".join(clause.split())[:200],
            "field_count": len(fields),
            "fields": fields,
        })
    return loads


def norm_fields(raw: str) -> list[str]:
    return [f.strip() for f in raw.split(",") if f.strip()]


def unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def resolve_dollar(text: str, varmap: dict[str, str], passes: int = 6) -> str:
    """Expand $(var) using literal variable values, best effort.

    Only literal assignments resolve. Variables holding expressions, SUB
    parameters and loop variables stay unexpanded on purpose: an unresolved
    path must be accounted for by the extraction, not silently guessed at.
    """
    cur = text
    for _ in range(passes):
        if "$(" not in cur:
            break
        nxt = RE_DOLLAR.sub(
            lambda m: varmap.get(m.group(1), m.group(0)), cur)
        if nxt == cur:
            break
        cur = nxt
    return cur


def annotate_path(entry: dict, varmap: dict[str, str]) -> None:
    """Fill in qvd basename for dynamic paths, flagging what stays unresolved."""
    entry["dynamic"] = "$(" in entry["path"]
    if not entry["dynamic"]:
        entry["resolved"] = True
        return
    resolved = resolve_dollar(entry["path"], varmap)
    base = resolved.rsplit("/", 1)[-1]
    entry["resolved_path"] = resolved
    if base.lower().endswith(".qvd") and "$(" not in base:
        entry["qvd"] = base
        entry["resolved"] = True
    else:
        entry["resolved"] = False
        entry["unresolved_vars"] = sorted(set(RE_DOLLAR.findall(base)))


def scan_file(path: Path, rel: str, service: str) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    code = strip_comments(raw)

    def collect(pattern, fn):
        return [fn(m, line_of(code, m.start())) for m in pattern.finditer(code)]

    stores = collect(RE_STORE, lambda m, ln: {
        "table": m.group("table"), "path": m.group("path").strip(),
        "qvd": m.group("path").strip().rsplit("/", 1)[-1], "line": ln})

    qvd_loads = []
    for m in RE_QVD_LOAD.finditer(code):
        p = m.group("path").strip()
        entry = {"path": p, "qvd": p.rsplit("/", 1)[-1],
                 "line": line_of(code, m.start()), "external": False,
                 "external_service": None}
        lib = RE_LIB_QVD_PATH.search(p)
        if lib and lib.group("service").upper() != service.upper():
            entry["external"] = True
            entry["external_service"] = lib.group("service")
        qvd_loads.append(entry)

    sql_sources = []
    seen_src = set()
    for m in RE_SQL_FROM.finditer(code):
        db, obj = m.group("db").lower(), m.group("obj").lower()
        # Skip CTE self-references: a bare alias with no glue-db shape.
        if not db.startswith("raa_") and "_db" not in db:
            continue
        key = (db, obj)
        if key in seen_src:
            continue
        seen_src.add(key)
        sql_sources.append({"database": db, "object": obj,
                            "line": line_of(code, m.start())})

    variables = collect(RE_VAR, lambda m, ln: {
        "name": m.group("name"), "keyword": m.group("kw").upper(),
        "value": m.group("value").strip(), "line": ln})

    unqualified, qualified = [], []
    for m in RE_UNQUALIFY.finditer(code):
        unqualified.append({"fields": norm_fields(m.group("fields")),
                            "line": line_of(code, m.start())})
    for m in RE_QUALIFY.finditer(code):
        qualified.append({"fields": norm_fields(m.group("fields")),
                          "line": line_of(code, m.start())})

    peeks = collect(RE_PEEK, lambda m, ln: {
        "field": m.group("field"), "table": m.group("table"), "line": ln})

    em = RE_ERRORMODE.findall(code)

    return {
        "file": rel,
        "lines": raw.count("\n") + 1,
        "loads": extract_loads(code),
        "tables_defined": sorted({m.group("name") for m in RE_TABLE_LABEL.finditer(code)}),
        "stores": stores,
        "qvd_loads": qvd_loads,
        "sql_sources": sql_sources,
        "variables": variables,
        "qualify": qualified,
        "unqualify": unqualified,
        "subs": collect(RE_SUB, lambda m, ln: {"name": m.group("name"), "line": ln}),
        "calls": collect(RE_CALL, lambda m, ln: {"name": m.group("name"), "line": ln}),
        "tag_fields": collect(RE_TAG, lambda m, ln: {
            "field": m.group("field"),
            "tags": norm_fields(m.group("tags")), "line": ln}),
        "peeks": peeks,
        "error_modes": [int(x) for x in em],
        "connections": [m.group("conn") for m in RE_LIBCONNECT.finditer(code)],
        "counts": {
            "inline_loads": len(RE_INLINE.findall(code)),
            "mapping_loads": len(RE_MAPPING.findall(code)),
            "explicit_joins": len(RE_JOIN_KW.findall(code)),
            "concatenate": len(RE_CONCATENATE.findall(code)),
            "noconcatenate": len(RE_NOCONCAT.findall(code)),
            "while_iterno": len(RE_WHILE_ITER.findall(code)),
            "exists": len(RE_EXISTS.findall(code)),
        },
    }


def build(repo: Path, service: str) -> dict:
    files = sorted(repo.rglob("*.qvs"), key=lambda p: str(p).lower())
    files = [f for f in files if ".git" not in f.parts]
    if not files:
        raise SystemExit(f"No .qvs files found under {repo}")

    apps: dict[str, list[dict]] = {}
    for f in files:
        rel = f.relative_to(repo).as_posix()
        app = rel.split("/")[0] if "/" in rel else "(root)"
        apps.setdefault(app, []).append(scan_file(f, rel, service))

    # Section order is lexical by filename: that ordering IS the dependency
    # declaration, so record it explicitly rather than leaving it implied.
    app_list = []
    for name, scanned in sorted(apps.items()):
        app_list.append({
            "name": name,
            "section_order": [s["file"] for s in scanned],
            "files": scanned,
        })

    all_files = [s for a in app_list for s in a["files"]]

    def flat(key):
        return [dict(e, file=s["file"]) for s in all_files for e in s[key]]

    # Literal variable values, in script order, so the last assignment wins —
    # matching Qlik runtime, where the production branch of an IF assigns last.
    varmap: dict[str, str] = {}
    for v in flat("variables"):
        val = unquote(v["value"])
        if val and "&" not in val:  # skip concatenation expressions
            varmap[v["name"]] = val

    stores = flat("stores")
    qvd_loads = flat("qvd_loads")
    for e in stores + qvd_loads:
        annotate_path(e, varmap)

    published = sorted({s["qvd"] for s in stores if s["resolved"]})
    unresolved = [s for s in stores + qvd_loads if not s["resolved"]]
    consumed = sorted({q["qvd"] for q in qvd_loads if q["resolved"]})
    external = sorted({(q["external_service"], q["qvd"])
                       for q in qvd_loads if q["external"]})

    sources = {}
    for s in flat("sql_sources"):
        key = f'{s["database"]}.{s["object"]}'
        sources.setdefault(key, {"database": s["database"], "object": s["object"],
                                 "referenced_in": []})
        sources[key]["referenced_in"].append(f'{s["file"]}:{s["line"]}')

    variables = {}
    for v in flat("variables"):
        variables.setdefault(v["name"], {"name": v["name"], "defined_in": []})
        variables[v["name"]]["defined_in"].append(f'{v["file"]}:{v["line"]}')

    assoc_keys = {}
    for u in flat("unqualify"):
        for f in u["fields"]:
            if f == "*":
                continue
            assoc_keys.setdefault(f, []).append(f'{u["file"]}:{u["line"]}')

    # An app that STOREs QVDs is a generator; one that only reads them is a
    # consumer. Used to propose the generator name, never to decide it: the
    # operator confirms, because the folder name is a lasting convention.
    generators, consumers = [], []
    for app in app_list:
        if any(f["stores"] for f in app["files"]):
            generators.append(app["name"])
        elif any(f["qvd_loads"] for f in app["files"]):
            consumers.append(app["name"])

    return {
        "service": service,
        "repo": repo.name,
        "generators": generators,
        "consumers": consumers,
        "apps": app_list,
        "summary": {
            "app_count": len(app_list),
            "generator_apps": generators,
            "consumer_apps": consumers,
            "file_count": len(all_files),
            "total_lines": sum(s["lines"] for s in all_files),
            "qvds_published": published,
            "qvds_consumed": consumed,
            "external_qvd_dependencies": [
                {"service": svc, "qvd": q} for svc, q in external],
            "sql_sources": sorted(sources.keys()),
            "databases": sorted({v["database"] for v in sources.values()}),
            "association_keys": sorted(assoc_keys.keys()),
            "error_modes_set": sorted({m for s in all_files for m in s["error_modes"]}),
            "unresolved_paths": [
                {"file": u["file"], "line": u["line"], "path": u["path"],
                 "vars": u.get("unresolved_vars", [])} for u in unresolved],
        },
        "sql_sources": [sources[k] for k in sorted(sources)],
        "variables": [variables[k] for k in sorted(variables)],
        "association_keys": [{"field": k, "declared_in": v}
                             for k, v in sorted(assoc_keys.items())],
        "stores": stores,
        "qvd_loads": qvd_loads,
        "peeks": flat("peeks"),
        "tag_fields": flat("tag_fields"),
    }


def print_summary(inv: dict) -> None:
    s = inv["summary"]
    print(f'service            : {inv["service"]}  (repo: {inv["repo"]})')
    print(f'generator app(s)   : {", ".join(inv["summary"]["generator_apps"]) or "none detected"}')
    print(f'consumer app(s)    : {", ".join(inv["summary"]["consumer_apps"]) or "none"}')
    print(f'apps               : {s["app_count"]}  '
          f'files: {s["file_count"]}  lines: {s["total_lines"]}')
    for app in inv["apps"]:
        print(f'  - {app["name"]}  ({len(app["files"])} files)')
    print(f'databases          : {len(s["databases"])}')
    for d in s["databases"]:
        print(f'  - {d}')
    print(f'sql sources        : {len(s["sql_sources"])}')
    for src in s["sql_sources"]:
        print(f'  - {src}')
    print(f'qvds published     : {len(s["qvds_published"])}')
    for q in s["qvds_published"]:
        print(f'  - {q}')
    print(f'qvds consumed      : {len(s["qvds_consumed"])}')
    ext = s["external_qvd_dependencies"]
    print(f'external qvd deps  : {len(ext)}')
    for e in ext:
        print(f'  - {e["service"]}: {e["qvd"]}')
    print(f'association keys   : {len(s["association_keys"])}')
    for k in s["association_keys"]:
        print(f'  - {k}')
    print(f'variables          : {len(inv["variables"])}')
    print(f'ErrorMode values   : {s["error_modes_set"]}')
    unres = s["unresolved_paths"]
    print(f'unresolved paths   : {len(unres)}'
          '   (each must map to an entity or be declared dead code)')
    for u in unres:
        print(f'  - {u["file"]}:{u["line"]}  {u["path"]}  vars={u["vars"]}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", type=Path, help="Qlik service repo root")
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output path (default: "
                         "<repo>/extraction/<generator>/inventory.json)")
    ap.add_argument("--generator", default=None,
                    help="generator app name, e.g. PBB_DataModel. Names the "
                         "extraction folder. If omitted and exactly one "
                         "generator is detected, that one is used; otherwise "
                         "you are asked to pass it explicitly.")
    ap.add_argument("--service", default=None,
                    help="service code (default: inferred from repo dir name)")
    ap.add_argument("--summary", action="store_true",
                    help="print a human-readable summary as well")
    ap.add_argument("--dump-loads", metavar="FILE_SUBSTRING", nargs="?", const="",
                    help="print every LOAD field list verbatim, for files "
                         "matching the substring; use when authoring spec columns")
    args = ap.parse_args()

    repo = args.repo.resolve()
    if not repo.is_dir():
        raise SystemExit(f"Not a directory: {repo}")

    service = args.service or re.sub(r"[_-]?qlik$", "", repo.name, flags=re.I)
    inv = build(repo, service)

    gen = args.generator
    detected = inv["summary"]["generator_apps"]
    if not gen:
        if len(detected) == 1:
            gen = detected[0]
        elif not detected:
            raise SystemExit(
                "No generator app detected (no STORE ... INTO found). Pass "
                "--generator explicitly, naming the app this extraction covers.")
        else:
            raise SystemExit(
                f"Multiple generator apps detected: {', '.join(detected)}. "
                f"Pass --generator to say which one this extraction covers.")
    elif detected and gen not in detected:
        print(f"WARNING  --generator {gen!r} is not among the apps that STORE "
              f"QVDs ({', '.join(detected) or 'none'}). Continuing, but check "
              f"the name.\n"
              f"         Expected when the app's folder is not named after the "
              f"app - the detected names above are DIRECTORIES, while "
              f"--generator names the app and the bundle folder. If {gen!r} is "
              f"the app and one of those is its directory, this is fine: put the "
              f"directory in apps[].directory and in entities[].app.")
    inv["generator"] = gen

    out = args.out or (repo / "extraction" / gen / "inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=2) + "\n", encoding="utf-8")

    if args.summary:
        print_summary(inv)
        print()
    if args.dump_loads is not None:
        for app in inv["apps"]:
            for f in app["files"]:
                if args.dump_loads and args.dump_loads.lower() not in f["file"].lower():
                    continue
                for ld in f["loads"]:
                    print(f'--- {f["file"]}:{ld["line"]}  table={ld["table"]}  '
                          f'fields={ld["field_count"]}  [{ld["source_clause"]}]')
                    for fld in ld["fields"]:
                        print(f'    {" ".join(fld.split())}')
        print()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
