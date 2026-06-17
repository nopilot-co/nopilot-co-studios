"""Normalised CSV sidecar for every visualisation in a render (#viz-data).

Whatever the studio draws, it also ships the *underlying data* as a normalised
(tidy / long-form) CSV in the docket, so a downstream data editor (nopilot.co)
can pick up and edit the numbers behind any chart, diagram, table, or framework.

This module is deliberately decoupled from the render engines: it does ONE pass
over the meta-stripped source body, mints a stable document-order viz-id per
block, and writes CSV(s) from the *authored* YAML — reusing the engines' own
normalisers (``charts._series``, ``diagrams._flatten_tree``) so the CSV matches
the picture. Because it reads the authored intent, it ships data for every
export (html / pdf / pptx / revealjs) AND for any future/unknown visualisation
type that has no renderer yet — those emit ``rendered: false`` in the manifest
but the CSV is still real.

Never crashes a render: every emit is wrapped; a bad block is skipped with a
stderr warning (mirrors the fallback-panel discipline in charts/diagrams).

``scan_session`` is the single entry point called from ``render.render``; it
returns a manifest list that ``session.record_render`` persists as
``version.json``'s per-render ``data[]``.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Any

from . import charts as charts_mod
from . import diagrams as diagrams_mod
from . import metacontent

# Mirrors the fenced-div grammar in charts.py / diagrams.py (kept local so this
# module doesn't depend on a private name in those modules).
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

# Visualisation families ----------------------------------------------------
_CHART = {"chart"}
_FLOWLIKE = {"flow", "process", "timeline", "swimlane", "decision-tree"}
_TREELIKE = {"hierarchy", "org"}
_FRAMEWORKS = {"bullseye", "matrix", "funnel"}
_GRID = {"heatmap"}
_ALL_DIV_CLASSES = _CHART | _FLOWLIKE | _TREELIKE | _FRAMEWORKS | _GRID

# Flow-family types rendered by the diagrams engine; swimlane/decision-tree
# render via the frameworks engine (Phase 2).
_RENDERED_FLOW = {"flow", "process", "timeline"}

_SEP_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


# --------------------------------------------------------------- small helpers


def _num(v: Any) -> Any:
    """Coerce numeric-looking values to int/float; leave everything else as-is."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return int(f) if f.is_integer() else f


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _write_rows(path: Path, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


# --------------------------------------------------------------- table finder


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _blocked_ranges(body: str) -> list[tuple[int, int]]:
    """Char spans where a markdown table must NOT be detected: fenced divs and
    fenced code blocks (so example tables / div bodies aren't double-counted)."""
    spans = [(m.start(), m.end()) for m in _DIV_RE.finditer(body)]
    for m in re.finditer(r"^(```|~~~).*?^\1[ \t]*$", body, re.MULTILINE | re.DOTALL):
        spans.append((m.start(), m.end()))
    return spans


def _find_tables(body: str) -> list[tuple[int, list[list[str]]]]:
    """GFM pipe tables outside blocked spans → (start_offset, rows incl header)."""
    blocked = _blocked_ranges(body)

    def is_blocked(pos: int) -> bool:
        return any(a <= pos < b for a, b in blocked)

    lines = body.splitlines(keepends=True)
    offsets, off = [], 0
    for ln in lines:
        offsets.append(off)
        off += len(ln)

    tables: list[tuple[int, list[list[str]]]] = []
    i = 0
    while i < len(lines) - 1:
        if is_blocked(offsets[i]) or "|" not in lines[i]:
            i += 1
            continue
        if _SEP_RE.match(lines[i + 1]) and "-" in lines[i + 1]:
            rowlines = [lines[i]]
            j = i + 2
            while (
                j < len(lines)
                and "|" in lines[j]
                and lines[j].strip()
                and not is_blocked(offsets[j])
            ):
                rowlines.append(lines[j])
                j += 1
            tables.append((offsets[i], [_split_row(rl) for rl in rowlines]))
            i = j
        else:
            i += 1
    return tables


def _collect(body: str) -> list[tuple[int, str, Any]]:
    """All viz blocks (known fenced divs + tables) in document order."""
    import yaml

    items: list[tuple[int, str, Any]] = []
    for m in _DIV_RE.finditer(body):
        name = m.group("name")
        if name not in _ALL_DIV_CLASSES:
            continue
        try:
            spec = yaml.safe_load(m.group("body")) or {}
        except Exception:  # noqa: BLE001 — malformed YAML still gets an (empty) entry
            spec = {}
        items.append((m.start(), name, spec if isinstance(spec, dict) else {}))
    for start, rows in _find_tables(body):
        items.append((start, "table", rows))
    items.sort(key=lambda t: t[0])
    return items


# --------------------------------------------------------------- emitters
# Each returns (files_written, data_row_count). They never validate the render;
# they serialise the authored data into a normalised CSV.


def _emit_chart(spec: dict, ctype: str, viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    rows: list[list] = []
    if ctype == "pie":
        values = spec.get("values") or spec.get("y") or []
        labels = spec.get("x") or spec.get("labels") or [str(i) for i in range(len(values))]
        for lab, val in zip(labels, values):
            rows.append([viz_id, "pie", str(lab), str(lab), _num(val)])
    else:
        x = [str(v) for v in (spec.get("x") or spec.get("labels") or [])]
        for s in charts_mod._series(spec):
            for i, y in enumerate(s["y"]):
                rows.append([viz_id, ctype, s["name"], x[i] if i < len(x) else str(i), _num(y)])
    f = data_dir / f"{viz_id}.csv"
    _write_csv(f, ["viz_id", "type", "series", "x", "y"], rows)
    return [f], len(rows)


def _emit_table(rows: list[list[str]], viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    f = data_dir / f"{viz_id}.csv"
    _write_rows(f, rows)  # verbatim: header + data rows exactly as authored
    return [f], max(len(rows) - 1, 0)


def _emit_flowlike(name: str, spec: dict, viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    nf = data_dir / f"{viz_id}.nodes.csv"
    ef = data_dir / f"{viz_id}.edges.csv"

    if name == "timeline":
        events = spec.get("events") or []
        nodes, edges = [], []
        for i, e in enumerate(events):
            at = str(e.get("at", "")) if isinstance(e, dict) else ""
            lab = str(e.get("label", "")) if isinstance(e, dict) else str(e)
            nodes.append([viz_id, f"n{i}", lab, i, at])
        edges = [[viz_id, f"n{i}", f"n{i+1}", ""] for i in range(len(events) - 1)]
        _write_csv(nf, ["viz_id", "node_id", "label", "order", "at"], nodes)
        _write_csv(ef, ["viz_id", "source", "target", "label"], edges)
        return [nf, ef], len(nodes)

    if name == "swimlane":
        nodes, id_by_label, idx = [], {}, 0
        lanes = spec.get("lanes")
        if isinstance(lanes, list):
            for lane in lanes:
                lname = str(lane.get("lane", "")) if isinstance(lane, dict) else str(lane)
                lnodes = (lane.get("nodes") if isinstance(lane, dict) else None) or []
                for lab in lnodes:
                    nid = f"n{idx}"
                    nodes.append([viz_id, nid, str(lab), idx, lname])
                    id_by_label.setdefault(str(lab), nid)
                    idx += 1
        else:
            for lab in spec.get("nodes") or []:
                text = str(lab.get("label", "")) if isinstance(lab, dict) else str(lab)
                lane = str(lab.get("lane", "")) if isinstance(lab, dict) else ""
                nid = f"n{idx}"
                nodes.append([viz_id, nid, text, idx, lane])
                id_by_label.setdefault(text, nid)
                idx += 1
        spec_edges = spec.get("edges")
        if isinstance(spec_edges, list) and spec_edges:
            edges = []
            for e in spec_edges:
                if not isinstance(e, dict):
                    continue
                src = id_by_label.get(str(e.get("from", "")), str(e.get("from", "")))
                tgt = id_by_label.get(str(e.get("to", "")), str(e.get("to", "")))
                edges.append([viz_id, src, tgt, str(e.get("label", ""))])
        else:
            edges = [[viz_id, f"n{i}", f"n{i+1}", ""] for i in range(len(nodes) - 1)]
        _write_csv(nf, ["viz_id", "node_id", "label", "order", "lane"], nodes)
        _write_csv(ef, ["viz_id", "source", "target", "label"], edges)
        return [nf, ef], len(nodes)

    if name == "decision-tree":
        nodes, edges = [], []

        def walk(node: Any, parent_id: str | None, condition: str, depth: int) -> None:
            if isinstance(node, dict):
                label = str(node.get("root", node.get("label", "")))
                children = node.get("children") or []
            else:
                label, children = str(node), []
            nid = f"n{len(nodes)}"
            nodes.append([viz_id, nid, label, depth, "decision" if children else "outcome"])
            if parent_id is not None:
                edges.append([viz_id, parent_id, nid, condition])
            for ch in children:
                cond = str(ch.get("condition", "")) if isinstance(ch, dict) else ""
                walk(ch, nid, cond, depth + 1)

        walk(spec, None, "", 0)
        _write_csv(nf, ["viz_id", "node_id", "label", "depth", "kind"], nodes)
        _write_csv(ef, ["viz_id", "source", "target", "condition"], edges)
        return [nf, ef], len(nodes)

    # flow / process — a linear chain
    labels = [str(x) for x in (spec.get("nodes") or spec.get("steps") or [])]
    nodes = [[viz_id, f"n{i}", lab, i] for i, lab in enumerate(labels)]
    edges = [[viz_id, f"n{i}", f"n{i+1}", ""] for i in range(len(labels) - 1)]
    _write_csv(nf, ["viz_id", "node_id", "label", "order"], nodes)
    _write_csv(ef, ["viz_id", "source", "target", "label"], edges)
    return [nf, ef], len(nodes)


def _emit_treelike(name: str, spec: dict, viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    nodes, edges = diagrams_mod._flatten_tree(spec)
    parent = {b: a for a, b in edges}
    nrows = [
        [viz_id, f"n{nd['id']}", nd["label"], nd["depth"],
         (f"n{parent[nd['id']]}" if nd["id"] in parent else "")]
        for nd in nodes
    ]
    erows = [[viz_id, f"n{a}", f"n{b}"] for a, b in edges]
    nf = data_dir / f"{viz_id}.nodes.csv"
    ef = data_dir / f"{viz_id}.edges.csv"
    _write_csv(nf, ["viz_id", "node_id", "label", "depth", "parent"], nrows)
    _write_csv(ef, ["viz_id", "source", "target"], erows)
    return [nf, ef], len(nrows)


def _emit_framework(name: str, spec: dict, viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    f = data_dir / f"{viz_id}.csv"
    if name == "bullseye":
        rows = []
        rings = spec.get("rings")
        if isinstance(rings, list):
            for ring in rings:
                rname = str(ring.get("ring", "")) if isinstance(ring, dict) else str(ring)
                items = (ring.get("items") if isinstance(ring, dict) else None) or []
                for it in items:
                    if isinstance(it, dict):
                        rows.append([viz_id, "bullseye", str(it.get("label", it.get("name", ""))), rname, _num(it.get("value", ""))])
                    else:
                        rows.append([viz_id, "bullseye", str(it), rname, ""])
        else:
            for it in spec.get("items") or []:
                if isinstance(it, dict):
                    rows.append([viz_id, "bullseye", str(it.get("label", it.get("name", ""))), str(it.get("ring", "")), _num(it.get("value", ""))])
                else:
                    rows.append([viz_id, "bullseye", str(it), "", ""])
        _write_csv(f, ["viz_id", "type", "item", "ring", "value"], rows)
        return [f], len(rows)

    if name == "matrix":
        rows = []

        def add_item(it: Any, quad: str = "") -> None:
            if isinstance(it, dict):
                rows.append([viz_id, "matrix", str(it.get("label", it.get("name", ""))),
                             str(it.get("x", "")), str(it.get("y", "")),
                             str(it.get("quadrant", quad)), _num(it.get("value", ""))])
            else:
                rows.append([viz_id, "matrix", str(it), "", "", quad, ""])

        if isinstance(spec.get("quadrants"), list):
            for q in spec["quadrants"]:
                qn = str(q.get("quadrant", "")) if isinstance(q, dict) else str(q)
                for it in (q.get("items") if isinstance(q, dict) else None) or []:
                    add_item(it, qn)
        else:
            for it in spec.get("items") or []:
                add_item(it)
        _write_csv(f, ["viz_id", "type", "item", "x_axis", "y_axis", "quadrant", "value"], rows)
        return [f], len(rows)

    # funnel
    rows = []
    for i, st in enumerate(spec.get("stages") or []):
        if isinstance(st, dict):
            rows.append([viz_id, "funnel", str(st.get("stage", st.get("label", ""))), i, _num(st.get("value", ""))])
        else:
            rows.append([viz_id, "funnel", str(st), i, ""])
    _write_csv(f, ["viz_id", "type", "stage", "order", "value"], rows)
    return [f], len(rows)


def _emit_heatmap(spec: dict, viz_id: str, data_dir: Path) -> tuple[list[Path], int]:
    rag_flag = bool(spec.get("rag"))
    rows: list[list] = []
    data = spec.get("data")
    if isinstance(data, list) and data:
        for d in data:
            if not isinstance(d, dict):
                continue
            val, rag = d.get("value", ""), d.get("rag", "")
            if rag_flag and rag == "":
                rag, val = val, ""
            rows.append([viz_id, "heatmap", str(d.get("row", "")), str(d.get("col", "")),
                         _num(val) if val != "" else "", str(rag)])
    else:
        rnames = [str(r) for r in (spec.get("rows") or [])]
        cnames = [str(c) for c in (spec.get("cols") or spec.get("columns") or [])]
        cells = spec.get("cells") or spec.get("values") or []
        for ri, rn in enumerate(rnames):
            for ci, cn in enumerate(cnames):
                try:
                    cell = cells[ri][ci]
                except (IndexError, TypeError, KeyError):
                    cell = ""
                if rag_flag:
                    rows.append([viz_id, "heatmap", rn, cn, "", str(cell)])
                else:
                    rows.append([viz_id, "heatmap", rn, cn, _num(cell) if cell != "" else "", ""])
    f = data_dir / f"{viz_id}.csv"
    _write_csv(f, ["viz_id", "type", "row", "col", "value", "rag"], rows)
    return [f], len(rows)


# --------------------------------------------------------------- orchestration


def scan(body: str, data_dir: Path, *, rel_to: Path | None = None) -> list[dict]:
    """Emit a normalised CSV per viz block in ``body``; return the data manifest.

    ``data_dir`` is where CSVs are written. ``rel_to`` makes manifest ``files``
    paths relative to it (the session root) for portable downstream discovery.
    """
    manifest: list[dict] = []
    n = 0
    for _start, name, payload in _collect(body):
        n += 1
        viz_id = ""
        try:
            if name == "chart":
                ctype = str((payload or {}).get("type", "bar"))
                viz_id = f"{n:02d}-{ctype}"
                files, rows = _emit_chart(payload, ctype, viz_id, data_dir)
                engine, type_, family, rendered = "charts", ctype, "charts", True
            elif name == "table":
                viz_id = f"{n:02d}-table"
                files, rows = _emit_table(payload, viz_id, data_dir)
                engine, type_, family, rendered = "table", "table", "tables", True
            elif name in _FLOWLIKE:
                viz_id = f"{n:02d}-{name}"
                files, rows = _emit_flowlike(name, payload, viz_id, data_dir)
                # flow/process/timeline → diagrams engine; swimlane/decision-tree → frameworks engine
                engine = "diagrams" if name in _RENDERED_FLOW else "frameworks"
                type_, family, rendered = name, "process-flow", True
            elif name in _TREELIKE:
                viz_id = f"{n:02d}-{name}"
                files, rows = _emit_treelike(name, payload, viz_id, data_dir)
                engine, type_, family, rendered = "diagrams", name, "hierarchy", True
            elif name in _FRAMEWORKS:
                viz_id = f"{n:02d}-{name}"
                files, rows = _emit_framework(name, payload, viz_id, data_dir)
                engine, type_, family, rendered = "frameworks", name, "frameworks", True
            elif name in _GRID:
                viz_id = f"{n:02d}-heatmap"
                files, rows = _emit_heatmap(payload, viz_id, data_dir)
                engine, type_, family, rendered = "frameworks", "heatmap", "heatmap", True
            else:  # pragma: no cover — _collect already filters
                n -= 1
                continue
        except Exception as e:  # noqa: BLE001 — never crash a render
            print(f"⚠ viz_data: skipped '{name}' block ({e})", file=sys.stderr)
            continue
        files_rel = [str(p.relative_to(rel_to)) if rel_to else str(p) for p in files]
        manifest.append(
            {
                "viz_id": viz_id,
                "type": type_,
                "family": family,
                "files": files_rel,
                "rows": rows,
                "page_key": None,  # showcase panel join is a follow-up (issue #100)
                "engine": engine,
                "rendered": rendered,
            }
        )
    return manifest


def scan_session(session_path: Path, state: dict | None = None) -> list[dict]:
    """Read the session's source, emit CSV sidecars under ``outputs/data/``, and
    return the manifest. Safe to call for any export; returns [] if no source."""
    src = session_path / "inputs" / "source.md"
    if not src.exists():
        return []
    try:
        body = metacontent.strip(src)
    except Exception:  # noqa: BLE001
        body = src.read_text(encoding="utf-8")
    data_dir = session_path / "outputs" / "data"
    return scan(body, data_dir, rel_to=session_path)
