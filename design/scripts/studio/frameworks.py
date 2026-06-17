"""Framework / grid / lane renderers (Phase 2) — the engine for the viz types
that previously shipped CSV-only.

Renders `::: bullseye | matrix | funnel | heatmap | swimlane | decision-tree`
fenced divs (YAML body) to brand-styled SVG via matplotlib — the SAME SVG
embedded inline in HTML and placed with Typst `#image()` in PDF, so the two
targets are identical (true parity, like charts.py).

matplotlib is imported LAZILY so the module loads even when it's absent; in that
case each block degrades to a visible fallback panel (the render never crashes).

Runs in render.py's preprocess step, after charts.expand. The normalised-CSV
sidecar is emitted separately by viz_data.py from the same authored YAML.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Same fenced-div grammar as charts.py / diagrams.py.
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

FRAMEWORK_CLASSES = {"bullseye", "matrix", "funnel", "heatmap", "swimlane", "decision-tree"}

# Conventional traffic-light colours for RAG grids (semantic, not brand).
_RAG = {
    "red": "#C62828", "r": "#C62828", "amber": "#F9A825", "a": "#F9A825",
    "orange": "#F9A825", "green": "#2E7D32", "g": "#2E7D32",
}


def _palette(tokens: dict) -> list[str]:
    c = tokens["color"]
    return [c["tertiary"], c["primary"], c["secondary"], c["neutral"], c["surface"]]


def _pos(v: Any) -> float:
    """Map a low/med/high axis position (or a 0..1 number) to a coordinate."""
    if isinstance(v, (int, float)):
        f = float(v)
        return f if 0.0 <= f <= 1.0 else max(0.0, min(1.0, f))
    return {"low": 0.25, "lo": 0.25, "med": 0.5, "medium": 0.5, "mid": 0.5,
            "high": 0.75, "hi": 0.75}.get(str(v).strip().lower(), 0.5)


def render_svg(name: str, spec: dict, tokens: dict) -> str:
    """Render one framework spec to an SVG string. Raises on bad spec (caller catches)."""
    import io

    import matplotlib

    matplotlib.use("svg")
    import matplotlib.pyplot as plt

    c = tokens["color"]
    palette = _palette(tokens)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    try:
        if name == "bullseye":
            _draw_bullseye(ax, spec, c, palette)
        elif name == "matrix":
            _draw_matrix(ax, spec, c, palette)
        elif name == "funnel":
            _draw_funnel(ax, spec, c, palette)
        elif name == "heatmap":
            _draw_heatmap(ax, spec, c, palette)
        elif name == "swimlane":
            _draw_swimlane(ax, spec, c, palette)
        elif name == "decision-tree":
            _draw_decision_tree(ax, spec, c, palette)
        else:
            raise ValueError(f"unknown framework '{name}'")
        if spec.get("title"):
            ax.set_title(str(spec["title"]), color=c["primary"])
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        fig.tight_layout()
        buf = io.StringIO()
        fig.savefig(buf, format="svg")
        return buf.getvalue()
    finally:
        plt.close(fig)


# ------------------------------------------------------------------ bullseye


def _bands(spec: dict) -> list[tuple[str, list[str]]]:
    """Normalise to ordered (ring_label, items) from centre outward."""
    rings = spec.get("rings")
    out: list[tuple[str, list[str]]] = []
    if isinstance(rings, list):
        for r in rings:
            if isinstance(r, dict):
                out.append((str(r.get("ring", "")), [str(x) for x in (r.get("items") or [])]))
            else:
                out.append((str(r), []))
        return out
    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for it in spec.get("items") or []:
        ring = str(it.get("ring", "")) if isinstance(it, dict) else ""
        label = str(it.get("label", it.get("name", ""))) if isinstance(it, dict) else str(it)
        if ring not in grouped:
            grouped[ring] = []
            order.append(ring)
        grouped[ring].append(label)
    return [(r, grouped[r]) for r in order]


def _draw_bullseye(ax, spec, c, palette) -> None:
    from matplotlib.patches import Circle

    bands = _bands(spec) or [("", [])]
    n = len(bands)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    # Draw outermost first so inner rings sit on top. bands[0] = core (centre).
    for j in range(n - 1, -1, -1):
        r = (j + 1) / n
        ax.add_patch(
            Circle((0, 0), r, facecolor=palette[j % len(palette)],
                   edgecolor=c["surface"], lw=1.0, alpha=0.85)
        )
    for j, (label, items) in enumerate(bands):
        midr = (2 * j + 1) / (2 * n)
        txt = (label + ": " if label and items else label) + ", ".join(items)
        ax.text(0, midr, txt, ha="center", va="center", color=c["on_primary"], fontsize=8)


# ------------------------------------------------------------------ matrix


def _matrix_items(spec: dict) -> list[dict]:
    if isinstance(spec.get("quadrants"), list):
        items = []
        for q in spec["quadrants"]:
            qn = str(q.get("quadrant", "")) if isinstance(q, dict) else str(q)
            for it in (q.get("items") if isinstance(q, dict) else None) or []:
                d = dict(it) if isinstance(it, dict) else {"label": str(it)}
                d.setdefault("quadrant", qn)
                items.append(d)
        return items
    return [it if isinstance(it, dict) else {"label": str(it)} for it in (spec.get("items") or [])]


def _draw_matrix(ax, spec, c, palette) -> None:
    axes = spec.get("axes") or {}
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(0.5, color=c["secondary"], lw=1.0)
    ax.axvline(0.5, color=c["secondary"], lw=1.0)
    if axes.get("x"):
        ax.set_xlabel(str(axes["x"]), color=c["primary"])
    if axes.get("y"):
        ax.set_ylabel(str(axes["y"]), color=c["primary"])
    # Faint quadrant labels in the corners (distinct names only).
    seen = []
    for it in _matrix_items(spec):
        q = str(it.get("quadrant", ""))
        if q and q not in seen:
            seen.append(q)
    for it in _matrix_items(spec):
        x, y = _pos(it.get("x")), _pos(it.get("y"))
        label = str(it.get("label", it.get("name", "")))
        ax.scatter([x], [y], color=palette[0], s=70, zorder=3, edgecolor=c["surface"])
        ax.text(x, y + 0.045, label, ha="center", va="bottom", fontsize=8, color=c["primary"])


# ------------------------------------------------------------------ funnel


def _draw_funnel(ax, spec, c, palette) -> None:
    labels, vals = [], []
    for st in spec.get("stages") or []:
        if isinstance(st, dict):
            labels.append(str(st.get("stage", st.get("label", ""))))
            try:
                vals.append(float(st.get("value", 0) or 0))
            except (TypeError, ValueError):
                vals.append(0.0)
        else:
            labels.append(str(st))
            vals.append(0.0)
    n = len(labels) or 1
    maxv = max(vals) if any(vals) else 1.0
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, n - 0.5)
    ax.axis("off")
    for i, (lab, v) in enumerate(zip(labels, vals)):
        w = (v / maxv) if maxv else 1.0
        w = max(w, 0.08)  # keep a sliver visible even at 0
        y = n - 1 - i
        ax.barh(y, w, left=(1 - w) / 2, height=0.74, color=palette[i % len(palette)])
        vtxt = ("" if not v else f"  ({int(v) if float(v).is_integer() else v})")
        ax.text(0.5, y, f"{lab}{vtxt}", ha="center", va="center",
                color=c["on_primary"], fontsize=8)


# ------------------------------------------------------------------ heatmap


def _heatmap_grid(spec: dict) -> tuple[list[str], list[str], list[list[Any]]]:
    data = spec.get("data")
    rag = bool(spec.get("rag"))
    if isinstance(data, list) and data:
        rows: list[str] = []
        cols: list[str] = []
        cell: dict[tuple[str, str], Any] = {}
        for d in data:
            if not isinstance(d, dict):
                continue
            r, co = str(d.get("row", "")), str(d.get("col", ""))
            if r not in rows:
                rows.append(r)
            if co not in cols:
                cols.append(co)
            val = d.get("rag") if (rag and d.get("rag") not in (None, "")) else d.get("value", "")
            cell[(r, co)] = val
        grid = [[cell.get((r, co), "") for co in cols] for r in rows]
        return rows, cols, grid
    rows = [str(r) for r in (spec.get("rows") or [])]
    cols = [str(co) for co in (spec.get("cols") or spec.get("columns") or [])]
    cells = spec.get("cells") or spec.get("values") or []
    grid = [
        [(cells[ri][ci] if ri < len(cells) and ci < len(cells[ri]) else "") for ci in range(len(cols))]
        for ri in range(len(rows))
    ]
    return rows, cols, grid


def _draw_heatmap(ax, spec, c, palette) -> None:
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Rectangle

    rag = bool(spec.get("rag"))
    rows, cols, grid = _heatmap_grid(spec)
    nrows, ncols = len(rows), len(cols)
    nums = []
    for row in grid:
        for v in row:
            try:
                nums.append(float(v))
            except (TypeError, ValueError):
                pass
    vmin, vmax = (min(nums), max(nums)) if nums else (0.0, 1.0)

    def cell_color(v: Any) -> Any:
        if rag:
            return _RAG.get(str(v).strip().lower(), c["surface"])
        try:
            f = float(v)
        except (TypeError, ValueError):
            return c["surface"]
        t = 0.5 if vmax == vmin else (f - vmin) / (vmax - vmin)
        return to_rgba(c["tertiary"], alpha=0.15 + 0.85 * t)

    ax.set_xlim(0, max(ncols, 1))
    ax.set_ylim(0, max(nrows, 1))
    for ri in range(nrows):
        for ci in range(ncols):
            v = grid[ri][ci]
            y = nrows - 1 - ri
            ax.add_patch(Rectangle((ci, y), 1, 1, facecolor=cell_color(v), edgecolor="white", lw=1.0))
            ax.text(ci + 0.5, y + 0.5, str(v), ha="center", va="center", fontsize=8,
                    color=("white" if rag else c["primary"]))
    ax.set_xticks([i + 0.5 for i in range(ncols)])
    ax.set_xticklabels(cols)
    ax.set_yticks([i + 0.5 for i in range(nrows)])
    ax.set_yticklabels(list(reversed(rows)))
    ax.tick_params(length=0, colors=c["secondary"])
    for sp in ax.spines.values():
        sp.set_visible(False)


# ------------------------------------------------------------------ swimlane


def _lanes(spec: dict) -> list[tuple[str, list[str]]]:
    lanes = spec.get("lanes")
    if isinstance(lanes, list):
        out = []
        for ln in lanes:
            if isinstance(ln, dict):
                out.append((str(ln.get("lane", "")), [str(x) for x in (ln.get("nodes") or [])]))
            else:
                out.append((str(ln), []))
        return out
    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for nd in spec.get("nodes") or []:
        lane = str(nd.get("lane", "")) if isinstance(nd, dict) else ""
        label = str(nd.get("label", "")) if isinstance(nd, dict) else str(nd)
        if lane not in grouped:
            grouped[lane] = []
            order.append(lane)
        grouped[lane].append(label)
    return [(ln, grouped[ln]) for ln in order]


def _draw_swimlane(ax, spec, c, palette) -> None:
    from matplotlib.patches import FancyBboxPatch

    lanes = _lanes(spec) or [("", [])]
    nlanes = len(lanes)
    maxcols = max((len(nodes) for _, nodes in lanes), default=1) or 1
    ax.set_xlim(-0.7, maxcols + 0.1)
    ax.set_ylim(0, nlanes)
    ax.axis("off")
    pos: dict[str, tuple[float, float]] = {}
    flat: list[str] = []
    for li, (name, nodes) in enumerate(lanes):
        y = nlanes - 1 - li
        ax.axhspan(y, y + 1, facecolor=palette[li % len(palette)], alpha=0.12)
        ax.text(-0.6, y + 0.5, name, ha="left", va="center", fontsize=8,
                color=c["primary"], fontweight="bold")
        for ci, lab in enumerate(nodes):
            ax.add_patch(
                FancyBboxPatch((ci + 0.12, y + 0.28), 0.76, 0.44,
                               boxstyle="round,pad=0.02", facecolor=c["neutral"],
                               edgecolor=c["surface"], lw=1.0)
            )
            ax.text(ci + 0.5, y + 0.5, lab, ha="center", va="center", fontsize=7,
                    color=c["on_primary"])
            pos[lab] = (ci + 0.5, y + 0.5)
            flat.append(lab)
    edges = spec.get("edges")
    pairs: list[tuple[str, str]] = []
    if isinstance(edges, list) and edges:
        for e in edges:
            if isinstance(e, dict):
                pairs.append((str(e.get("from", "")), str(e.get("to", ""))))
    else:
        pairs = [(flat[i], flat[i + 1]) for i in range(len(flat) - 1)]
    for a, b in pairs:
        if a in pos and b in pos:
            ax.annotate("", xy=pos[b], xytext=pos[a],
                        arrowprops=dict(arrowstyle="-|>", color=c["tertiary"], lw=1.2,
                                        shrinkA=18, shrinkB=18))


# ------------------------------------------------------------------ decision-tree


def _walk_decision(spec: Any) -> tuple[list[dict], list[tuple[int, int, str]]]:
    """Positioned nodes + condition-labelled edges (centred like diagrams._flatten_tree)."""
    nodes: list[dict] = []
    edges: list[tuple[int, int, str]] = []
    leaf = [0]

    def norm(n: Any) -> dict:
        if isinstance(n, dict):
            return {"label": str(n.get("root", n.get("label", ""))),
                    "children": n.get("children") or [],
                    "condition": str(n.get("condition", ""))}
        return {"label": str(n), "children": [], "condition": ""}

    def walk(raw: Any, depth: int) -> int:
        node = norm(raw)
        nid = len(nodes)
        nodes.append({"id": nid, "label": node["label"], "depth": depth, "x": 0.0,
                      "kind": "decision" if node["children"] else "outcome"})
        kids = []
        for ch in node["children"]:
            cid = walk(ch, depth + 1)
            edges.append((nid, cid, norm(ch)["condition"]))
            kids.append(cid)
        nodes[nid]["x"] = (
            sum(nodes[k]["x"] for k in kids) / len(kids) if kids else float(leaf[0])
        )
        if not kids:
            leaf[0] += 1
        return nid

    walk(spec, 0)
    return nodes, edges


def _draw_decision_tree(ax, spec, c, palette) -> None:
    from matplotlib.patches import FancyBboxPatch

    nodes, edges = _walk_decision(spec)
    maxx = max((n["x"] for n in nodes), default=1.0) or 1.0
    maxd = max((n["depth"] for n in nodes), default=0)
    ax.set_xlim(-0.7, maxx + 0.7)
    ax.set_ylim(-maxd - 0.7, 0.7)
    ax.axis("off")
    for n in nodes:
        x, y = n["x"], -n["depth"]
        fc = c["neutral"] if n["kind"] == "decision" else c["tertiary"]
        ax.add_patch(
            FancyBboxPatch((x - 0.42, y - 0.19), 0.84, 0.38, boxstyle="round,pad=0.02",
                           facecolor=fc, edgecolor=c["surface"], lw=1.0)
        )
        ax.text(x, y, n["label"], ha="center", va="center", fontsize=7, color=c["on_primary"])
    for a, b, cond in edges:
        xa, ya = nodes[a]["x"], -nodes[a]["depth"]
        xb, yb = nodes[b]["x"], -nodes[b]["depth"]
        ax.annotate("", xy=(xb, yb + 0.19), xytext=(xa, ya - 0.19),
                    arrowprops=dict(arrowstyle="-|>", color=c["tertiary"], lw=1.0))
        if cond:
            ax.text((xa + xb) / 2, (ya + yb) / 2, cond, fontsize=6, ha="center", va="center",
                    color=c["primary"],
                    bbox=dict(boxstyle="round,pad=0.12", fc=c["surface"], ec="none", alpha=0.75))


# ------------------------------------------------------------------ expand


def _fallback(name: str, body: str, err: str) -> str:
    return (
        f"::: panel\n**[{name} could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )


def expand(markdown: str, export: str, tokens: dict[str, Any], out_dir: Path) -> str:
    """Replace every framework div with an image of its rendered SVG, for `export`.

    HTML: a markdown image referencing the written SVG (Quarto inlines it).
    PDF:  a Typst `#image()` raw block (keeps the SVG as vector).
    Other exports / non-framework divs pass through unchanged.
    """
    if export not in ("html", "pdf"):
        return markdown

    counter = [0]

    def _sub(m: re.Match) -> str:
        name = m.group("name")
        if name not in FRAMEWORK_CLASSES:
            return m.group(0)
        try:
            spec = yaml.safe_load(m.group("body")) or {}
            if not isinstance(spec, dict):
                raise ValueError(f"{name} body must be a YAML mapping")
            svg = render_svg(name, spec, tokens)
        except Exception as e:  # noqa: BLE001 — never crash a render
            return _fallback(name, m.group("body"), str(e))
        counter[0] += 1
        fn = f"_framework-{counter[0]}.svg"
        (out_dir / fn).write_text(svg, encoding="utf-8")
        if export == "pdf":
            return f'```{{=typst}}\n#image("{fn}", width: 100%)\n```\n'
        return f"![]({fn})\n"

    return _DIV_RE.sub(_sub, markdown)
