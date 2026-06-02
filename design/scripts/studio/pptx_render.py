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

    for slide in split_slides(markdown):
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
        color=c["primary"],
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
        _set_text(shp.text_frame, block["body"], size=18, color=c["primary"])
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
                        _hex(c["on_primary"] if ri == 0 else c["primary"])
                    )
            if ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(_hex(c["surface"]))
    return top + 0.4 * nrows + 0.3


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
