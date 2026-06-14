"""Editable PPTX engine (#19).

A parallel render path: builds a `.pptx` of NATIVE, editable PowerPoint shapes
(text boxes, autoshapes, native tables/charts) from the same `::: ` block source
the Quarto path uses — brand-tokenized from the resolved design tokens.

render.py forks here when the locked export is `pptx`. python-pptx is already a
dependency; this module imports it lazily so the module loads without it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# 16:9 deck geometry (EMU via Inches helper, applied lazily in build).
_SLIDE_W_IN = 13.333
_SLIDE_H_IN = 7.5

_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

# Blocks that begin a new slide on their own.
_SLIDE_BLOCKS = {"cover-slide", "section-slide"}


def _hex(color: str) -> str:
    return color.lstrip("#")


def split_slides(markdown: str) -> list[dict]:
    """Split source markdown into a list of slide dicts.

    A new slide starts at: a top-level `#`/`##` heading, or a `::: cover-slide` /
    `::: section-slide` block. Everything until the next such boundary is that
    slide's raw body. Each slide: {kind, title, body}. kind in
    {cover-slide, section-slide, content}.
    """
    lines = markdown.splitlines()
    slides: list[dict] = []
    cur: dict | None = None

    def _flush():
        nonlocal cur
        if cur is not None:
            cur["body"] = "\n".join(cur["_lines"]).strip()
            del cur["_lines"]
            slides.append(cur)
            cur = None

    i = 0
    while i < len(lines):
        line = lines[i]
        m_block = re.match(r"^:::+\s*(?:\{\.)?([a-z][a-z0-9-]*)\}?\s*$", line)
        if m_block and m_block.group(1) in _SLIDE_BLOCKS:
            _flush()
            name = m_block.group(1)
            body_lines = []
            i += 1
            while i < len(lines) and not re.match(r"^:::+\s*$", lines[i]):
                body_lines.append(lines[i])
                i += 1
            i += 1  # skip closing :::
            title = ""
            rest = []
            for bl in body_lines:
                h = re.match(r"^#+\s+(.*)$", bl)
                if h and not title:
                    title = h.group(1).strip()
                else:
                    rest.append(bl)
            slides.append(
                {"kind": name, "title": title, "body": "\n".join(rest).strip()}
            )
            continue
        h = re.match(r"^#{1,2}\s+(.*)$", line)
        if h:
            _flush()
            cur = {"kind": "content", "title": h.group(1).strip(), "_lines": []}
            i += 1
            continue
        if cur is None:
            cur = {"kind": "content", "title": "", "_lines": []}
        cur["_lines"].append(line)
        i += 1
    _flush()
    return [
        s
        for s in slides
        if s.get("title") or s.get("body") or s["kind"] in _SLIDE_BLOCKS
    ]


def build_pptx(markdown: str, tokens: dict[str, Any], out_path: Path) -> Path:
    """Build a .pptx from markdown + tokens, writing to out_path. Returns out_path."""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(_SLIDE_W_IN)
    prs.slide_height = Inches(_SLIDE_H_IN)
    blank = prs.slide_layouts[6]

    slides = split_slides(markdown)
    if not slides:
        # An empty source would yield a zero-slide deck, which some downstream
        # tools (e.g. the LibreOffice QA conversion) choke on. Emit one blank slide.
        slides = [{"kind": "content", "title": "", "body": ""}]
    for slide in slides:
        s = prs.slides.add_slide(blank)
        if slide["kind"] == "cover-slide":
            _render_cover(s, slide, tokens, prs)
        elif slide["kind"] == "section-slide":
            _render_section(s, slide, tokens, prs)
        else:
            _render_content(s, slide, tokens, prs)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


def _solid(shape, hex_color: str) -> None:
    from pptx.dml.color import RGBColor

    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(_hex(hex_color))
    shape.line.fill.background()


def _set_text(tf, text: str, *, size: int, color: str, bold: bool = False) -> None:
    from pptx.dml.color import RGBColor
    from pptx.util import Pt

    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(_hex(color))


def _render_cover(s, slide, tokens, prs) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    bg = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(_SLIDE_W_IN), Inches(_SLIDE_H_IN)
    )
    _solid(bg, c["neutral"])
    title = s.shapes.add_textbox(Inches(1), Inches(2.8), Inches(11), Inches(1.4))
    _set_text(
        title.text_frame,
        slide.get("title") or "",
        size=44,
        color=c["on_primary"],
        bold=True,
    )
    if slide.get("body"):
        sub = s.shapes.add_textbox(Inches(1), Inches(4.3), Inches(11), Inches(1.0))
        _set_text(
            sub.text_frame,
            slide["body"].splitlines()[0],
            size=20,
            color=c["on_primary"],
        )


def _render_section(s, slide, tokens, prs) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    bg = s.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(_SLIDE_W_IN), Inches(_SLIDE_H_IN)
    )
    _solid(bg, c["surface"])
    title = s.shapes.add_textbox(Inches(1), Inches(3.2), Inches(11), Inches(1.2))
    _set_text(
        title.text_frame,
        slide.get("title") or "",
        size=36,
        color=c["on_surface"],
        bold=True,
    )


def _render_content(s, slide, tokens, prs) -> None:
    from pptx.util import Inches

    c = tokens["color"]
    top = 0.4
    if slide.get("title"):
        t = s.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12), Inches(0.9))
        _set_text(t.text_frame, slide["title"], size=30, color=c["primary"], bold=True)
        top = 1.5

    for block in _content_blocks(slide.get("body", "")):
        top = _place_block(s, block, tokens, top)


def _content_blocks(body: str) -> list[dict]:
    """Sequence a slide body into blocks: fenced divs, markdown tables, text runs."""
    blocks: list[dict] = []
    text_acc: list[str] = []

    def _flush_text():
        if text_acc:
            joined = "\n".join(text_acc).strip()
            if joined:
                blocks.append({"kind": "text", "body": joined})
            text_acc.clear()

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^:::+\s*(?:\{\.)?([a-z][a-z0-9-]*)\}?\s*$", line)
        if m:
            _flush_text()
            name = m.group(1)
            inner = []
            i += 1
            while i < len(lines) and not re.match(r"^:::+\s*$", lines[i]):
                inner.append(lines[i])
                i += 1
            i += 1
            blocks.append({"kind": name, "body": "\n".join(inner).strip()})
            continue
        if line.strip().startswith("|") and "|" in line:
            _flush_text()
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            blocks.append({"kind": "table", "rows": _parse_table(tbl)})
            continue
        text_acc.append(line)
        i += 1
    _flush_text()
    return blocks


def _parse_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for ln in lines:
        if re.match(r"^\s*\|?\s*:?-{2,}", ln):  # separator row
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


_PANEL_FILL = {
    "panel": None,
    "highlight": "surface",
    "ds-callout": "surface",
    "pullquote": None,
    "stat-panel": "surface",
    "kpi": "surface",
}


def _place_block(s, block, tokens, top: float) -> float:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    kind = block["kind"]
    if kind == "table":
        return _place_table(s, block["rows"], tokens, top)
    if kind == "kpi":
        shp = s.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.6),
            Inches(top),
            Inches(6),
            Inches(1.6),
        )
        _solid(shp, c["surface"])
        _set_text(
            shp.text_frame, block["body"], size=40, color=c["tertiary"], bold=True
        )
        return top + 1.9
    if kind == "chart":
        return _place_chart(s, block["body"], tokens, top)
    if kind in ("flow", "process", "timeline", "hierarchy", "org"):
        return _place_diagram(s, kind, block["body"], tokens, top)
    if kind in _PANEL_FILL:
        h = 1.3
        shp = s.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(top), Inches(12), Inches(h)
        )
        fill = _PANEL_FILL[kind]
        if fill:
            _solid(shp, c[fill])
        else:
            shp.fill.background()
            from pptx.dml.color import RGBColor

            shp.line.color.rgb = RGBColor.from_string(_hex(c["secondary"]))
        # Surface-filled panels need on_surface for contrast; transparent panels
        # (panel/pullquote) sit on the slide background, so keep primary.
        text_color = c["on_surface"] if fill else c["primary"]
        _set_text(shp.text_frame, block["body"], size=18, color=text_color)
        return top + h + 0.3
    # default: text
    tb = s.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12), Inches(1.2))
    _set_text_multiline(tb.text_frame, block["body"], tokens)
    return top + 1.3


def _place_table(s, rows, tokens, top: float) -> float:
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    c = tokens["color"]
    if not rows:
        return top
    nrows, ncols = len(rows), max(len(r) for r in rows)
    gframe = s.shapes.add_table(
        nrows, ncols, Inches(0.6), Inches(top), Inches(8), Inches(0.4 * nrows)
    )
    tbl = gframe.table
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            cell = tbl.cell(ri, ci)
            cell.text = row[ci] if ci < len(row) else ""
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(14)
                    run.font.color.rgb = RGBColor.from_string(
                        # Header row sits on a surface fill → on_surface for contrast.
                        _hex(c["on_surface"] if ri == 0 else c["primary"])
                    )
            if ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(_hex(c["surface"]))
    return top + 0.4 * nrows + 0.3


def _place_chart(s, body, tokens, top: float) -> float:
    from pptx.util import Inches

    try:
        import yaml

        from . import charts as charts_mod

        spec = yaml.safe_load(body) or {}
        if not isinstance(spec, dict):
            raise ValueError("chart body must be a YAML mapping")
        ctype = spec.get("type", "bar")
        if ctype not in charts_mod.CHART_TYPES:
            raise ValueError(f"unknown chart type '{ctype}'")
        series = charts_mod._series(spec)
        cats = [str(v) for v in (spec.get("x") or spec.get("labels") or [])]
        _add_native_chart(s, ctype, spec, series, cats, tokens, top)
        return top + 4.2
    except Exception:  # noqa: BLE001 — degrade: a chart must never crash the deck
        tb = s.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12), Inches(0.8))
        _set_text(
            tb.text_frame,
            "[chart could not render]",
            size=14,
            color=tokens["color"]["secondary"],
        )
        return top + 1.0


_XL = {
    "bar": "COLUMN_CLUSTERED",
    "line": "LINE",
    "area": "AREA",
    "pie": "PIE",
    "scatter": "XY_SCATTER",
}


def _add_native_chart(s, ctype, spec, series, cats, tokens, top) -> None:
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches

    c = tokens["color"]
    xltype = getattr(XL_CHART_TYPE, _XL.get(ctype, "COLUMN_CLUSTERED"))
    cd = CategoryChartData()
    if ctype == "pie":
        cd.categories = cats or [str(i) for i in range(len(spec.get("values") or []))]
        cd.add_series(
            "", tuple(float(v) for v in (spec.get("values") or spec.get("y") or []))
        )
    else:
        cd.categories = cats or [
            str(i) for i in range(len(series[0]["y"]) if series else 0)
        ]
        for sname_y in series:
            cd.add_series(sname_y["name"] or "series", tuple(sname_y["y"]))
    gframe = s.shapes.add_chart(
        xltype, Inches(0.6), Inches(top), Inches(8.5), Inches(4.0), cd
    )
    chart = gframe.chart
    chart.has_legend = any(sy["name"] for sy in series)
    try:
        palette = [c["tertiary"], c["primary"], c["secondary"]]
        for plot in chart.plots:
            for si, ser in enumerate(plot.series):
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = RGBColor.from_string(
                    _hex(palette[si % len(palette)])
                )
    except Exception:  # noqa: BLE001 — colour is best-effort; never fail the render
        pass


def _place_diagram(s, kind, body, tokens, top: float) -> float:
    try:
        import yaml

        spec = yaml.safe_load(body) or {}
        if kind in ("flow", "process", "timeline"):
            if kind == "timeline":
                labels = [
                    str(e.get("label", ""))
                    for e in (spec.get("events") or [])
                    if isinstance(e, dict)
                ]
            else:
                labels = [
                    str(x) for x in (spec.get("nodes") or spec.get("steps") or [])
                ]
            _diagram_linear(s, labels, tokens, top)
        else:
            from . import diagrams as diagrams_mod

            nodes, edges = diagrams_mod._flatten_tree(spec)
            _diagram_tree(s, nodes, edges, tokens, top)
        return top + 4.2
    except Exception:  # noqa: BLE001 — degrade
        from pptx.util import Inches

        tb = s.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12), Inches(0.8))
        _set_text(
            tb.text_frame,
            f"[diagram '{kind}' could not render]",
            size=14,
            color=tokens["color"]["secondary"],
        )
        return top + 1.0


def _node_box(s, x_in, y_in, w_in, h_in, label, tokens):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x_in),
        Inches(y_in),
        Inches(w_in),
        Inches(h_in),
    )
    _solid(shp, c["neutral"])
    _set_text(shp.text_frame, label, size=14, color=c["on_primary"], bold=False)
    return shp


def _connect_v(s, a, b, tokens):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.util import Emu

    c = tokens["color"]
    conn = s.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Emu(a.left + a.width // 2),
        Emu(a.top + a.height),
        Emu(b.left + b.width // 2),
        Emu(b.top),
    )
    conn.line.color.rgb = RGBColor.from_string(_hex(c["tertiary"]))
    conn.line.width = Emu(19050)


def _connect_h(s, a, b, tokens):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.util import Emu

    c = tokens["color"]
    conn = s.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Emu(a.left + a.width),
        Emu(a.top + a.height // 2),
        Emu(b.left),
        Emu(b.top + b.height // 2),
    )
    conn.line.color.rgb = RGBColor.from_string(_hex(c["tertiary"]))
    conn.line.width = Emu(19050)


def _diagram_linear(s, labels, tokens, top: float) -> None:
    n = max(len(labels), 1)
    w = min(2.2, 11.0 / n - 0.3)
    gap = 0.3
    total = n * w + (n - 1) * gap
    x = max(0.6, (13.333 - total) / 2)
    boxes = []
    for lab in labels:
        boxes.append(_node_box(s, x, top + 1.4, w, 0.9, lab, tokens))
        x += w + gap
    for i in range(len(boxes) - 1):
        _connect_h(s, boxes[i], boxes[i + 1], tokens)


def _diagram_tree(s, nodes, edges, tokens, top: float) -> None:
    maxx = max((nd["x"] for nd in nodes), default=0) or 1
    maxd = max((nd["depth"] for nd in nodes), default=0) or 1
    w, h = 1.7, 0.7
    margin = 0.6
    # The x-coordinate positions the box's LEFT edge; the span must leave room for
    # a full box width on the right so the rightmost node stays on the 13.333" slide.
    span_w = max(_SLIDE_W_IN - 2 * margin - w, 1.0)
    row_h = 3.6 / (maxd + 1)
    placed = {}
    for nd in nodes:
        cx = margin + (nd["x"] / maxx) * span_w if maxx else margin
        cy = top + 1.0 + nd["depth"] * row_h
        placed[nd["id"]] = _node_box(s, cx, cy, w, h, nd["label"], tokens)
    for a, b in edges:
        _connect_v(s, placed[a], placed[b], tokens)


def _set_text_multiline(tf, text: str, tokens) -> None:
    from pptx.dml.color import RGBColor
    from pptx.util import Pt

    c = tokens["color"]
    tf.word_wrap = True
    first = True
    for ln in text.splitlines():
        ln = ln.rstrip()
        if not ln:
            continue
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = ("• " + ln[2:].strip()) if ln.strip().startswith("- ") else ln
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor.from_string(_hex(c["primary"]))
