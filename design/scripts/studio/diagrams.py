"""Structured-diagram engine (slice 4a).

Expands `::: <diagram>` fenced divs whose body is YAML into the render engine for
the session's single locked export — Mermaid for HTML, Typst `fletcher` for PDF —
brand-tokenized on both sides. Runs in render.py's preprocess step, before Quarto.

Diagram classes: flow, timeline, process, hierarchy, org.
Unknown/malformed YAML degrades to a visible panel (never crashes the render).
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# A fenced div opening `::: name` or `::: {.name}`, body, then a closing `:::`.
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

DIAGRAM_CLASSES = {"flow", "timeline", "process", "hierarchy", "org"}


def expand(markdown: str, export: str, tokens: dict[str, Any]) -> str:
    """Replace every diagram div with its engine block for `export` (html|pdf).

    Other exports (pptx/revealjs) and non-diagram divs pass through unchanged.
    """
    if export not in ("html", "pdf"):
        return markdown

    def _sub(m: re.Match) -> str:
        name = m.group("name")
        if name not in DIAGRAM_CLASSES:
            return m.group(0)  # not a diagram — leave for the Lua bridge / Quarto
        try:
            spec = yaml.safe_load(m.group("body")) or {}
            if not isinstance(spec, dict):
                raise ValueError("diagram body must be a YAML mapping")
            return _render(name, spec, export, tokens)
        except Exception as e:  # noqa: BLE001 — never crash a render on bad input
            return _fallback(name, m.group("body"), str(e))

    return _DIV_RE.sub(_sub, markdown)


def _render(name: str, spec: dict, export: str, tokens: dict) -> str:
    if name in ("flow", "process"):
        labels = spec.get("nodes") or spec.get("steps") or []
        labels = [str(x) for x in labels]
        numbered = name == "process"
        return (
            _linear_html(labels, numbered)
            if export == "html"
            else _linear_pdf(labels, numbered, tokens)
        )
    if name == "timeline":
        events = spec.get("events") or []
        pairs = [
            (str(e.get("at", "")), str(e.get("label", "")))
            for e in events
            if isinstance(e, dict)
        ]
        return (
            _timeline_html(pairs) if export == "html" else _timeline_pdf(pairs, tokens)
        )
    if name in ("hierarchy", "org"):
        nodes, edges = _flatten_tree(spec)
        return (
            _tree_html(nodes, edges)
            if export == "html"
            else _tree_pdf(nodes, edges, tokens)
        )
    raise NotImplementedError(f"diagram '{name}' not implemented")


def _esc_mermaid(s: str) -> str:
    return s.replace('"', "'")


def _esc_typst(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _linear_html(labels: list[str], numbered: bool) -> str:
    nodes = []
    for i, lab in enumerate(labels):
        text = f"{i + 1}. {lab}" if numbered else lab
        nodes.append(f'n{i}["{_esc_mermaid(text)}"]')
    chain = " --> ".join(f"n{i}" for i in range(len(labels)))
    body = "\n  ".join(nodes + ([chain] if len(labels) > 1 else []))
    return f"```mermaid\nflowchart LR\n  {body}\n```\n"


def _fletcher_header(tokens: dict) -> str:
    c = tokens["color"]
    return (
        '#import "@preview/fletcher:0.5.5" as fletcher: diagram, node, edge\n'
        f'#let _nf = rgb("{c["neutral"]}")\n'
        f'#let _ac = rgb("{c["tertiary"]}")\n'
        f'#let _tx = rgb("{c["on_primary"]}")\n'
    )


def _linear_pdf(labels: list[str], numbered: bool, tokens: dict) -> str:
    lines = [
        _fletcher_header(tokens),
        "#figure(diagram(spacing: 2.2em, node-stroke: 0.5pt, node-fill: _nf,",
    ]
    parts = []
    for i, lab in enumerate(labels):
        text = f"{i + 1}. {lab}" if numbered else lab
        parts.append(
            f"node(({i},0), text(fill: _tx)[{_esc_typst(text)}], "
            f"corner-radius: 3pt, inset: 8pt)"
        )
        if i < len(labels) - 1:
            parts.append('edge("-|>", stroke: _ac + 1pt)')
    body = ",\n  ".join(parts)
    lines.append("  " + body + "\n))")
    return "```{=typst}\n" + "\n".join(lines) + "\n```\n"


def _timeline_html(pairs: list[tuple[str, str]]) -> str:
    lines = ["```mermaid", "timeline"]
    for at, label in pairs:
        lines.append(f"  {_esc_mermaid(at)} : {_esc_mermaid(label)}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _timeline_pdf(pairs: list[tuple[str, str]], tokens: dict) -> str:
    head = _fletcher_header(tokens)
    nodes = []
    for i, (at, label) in enumerate(pairs):
        nodes.append(
            f"node(({i},0), text(fill: _tx, size: 0.85em)[{_esc_typst(label)}], "
            f"corner-radius: 3pt, inset: 6pt)"
        )
        nodes.append(
            f'node(({i},-0.7), text(fill: _ac, weight: "bold")[{_esc_typst(at)}], '
            f"fill: none, stroke: none)"
        )
        if i < len(pairs) - 1:
            nodes.append(
                "edge((" + str(i) + ",0), (" + str(i + 1) + ",0), stroke: _ac + 1pt)"
            )
    body = ",\n  ".join(nodes)
    return (
        "```{=typst}\n"
        + head
        + "#figure(diagram(spacing: 3em, node-stroke: 0.5pt, node-fill: _nf,\n  "
        + body
        + "\n))\n```\n"
    )


def _flatten_tree(spec: Any) -> tuple[list[dict], list[tuple[int, int]]]:
    """Walk a nested {root, children} tree into positioned nodes + parent/child edges.

    Returns (nodes, edges). Each node: {id, label, depth, x}. Leaves are assigned
    sequential x positions left-to-right; a parent's x is centred over its subtree.
    """
    nodes: list[dict] = []
    edges: list[tuple[int, int]] = []
    leaf_counter = [0]

    def _norm(n: Any) -> dict:
        if isinstance(n, dict):
            return {
                "label": str(n.get("root", "")),
                "children": n.get("children", []) or [],
            }
        return {"label": str(n), "children": []}

    def _walk(raw: Any, depth: int) -> int:
        node = _norm(raw)
        nid = len(nodes)
        nodes.append({"id": nid, "label": node["label"], "depth": depth, "x": 0.0})
        kids = [_walk(c, depth + 1) for c in node["children"]]
        for k in kids:
            edges.append((nid, k))
        if kids:
            nodes[nid]["x"] = sum(nodes[k]["x"] for k in kids) / len(kids)
        else:
            nodes[nid]["x"] = float(leaf_counter[0])
            leaf_counter[0] += 1
        return nid

    _walk(spec, 0)
    return nodes, edges


def _tree_html(nodes: list[dict], edges: list[tuple[int, int]]) -> str:
    lines = ["```mermaid", "flowchart TD"]
    for n in nodes:
        lines.append(f'  n{n["id"]}["{_esc_mermaid(n["label"])}"]')
    for a, b in edges:
        lines.append(f"  n{a} --> n{b}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _tree_pdf(nodes: list[dict], edges: list[tuple[int, int]], tokens: dict) -> str:
    head = _fletcher_header(tokens)
    parts = []
    for n in nodes:
        parts.append(
            f'node(({n["x"]:.3f},{n["depth"]}), text(fill: _tx)[{_esc_typst(n["label"])}], '
            f'corner-radius: 3pt, inset: 8pt)'
        )
    for a, b in edges:
        na, nb = nodes[a], nodes[b]
        parts.append(
            f'edge(({na["x"]:.3f},{na["depth"]}), ({nb["x"]:.3f},{nb["depth"]}), '
            f'"-|>", stroke: _ac + 1pt)'
        )
    body = ",\n  ".join(parts)
    return (
        "```{=typst}\n"
        + head
        + "#figure(diagram(spacing: (2em, 3em), node-stroke: 0.5pt, node-fill: _nf,\n  "
        + body
        + "\n))\n```\n"
    )


def _fallback(name: str, body: str, err: str) -> str:
    return (
        f"::: panel\n**[diagram '{name}' could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )
