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
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    c = tokens["color"]
    if slide.get("title"):
        t = s.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12), Inches(0.9))
        _set_text(t.text_frame, slide["title"], size=30, color=c["primary"], bold=True)
    body = slide.get("body", "")
    bullets = [
        ln[2:].strip() for ln in body.splitlines() if ln.strip().startswith("- ")
    ]
    paras = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip() and not ln.strip().startswith("- ")
    ]
    tb = s.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(12), Inches(5))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for para in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = para
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor.from_string(_hex(c["primary"]))
    for b in bullets:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = 0
        run = p.add_run()
        run.text = "• " + b
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor.from_string(_hex(c["primary"]))
