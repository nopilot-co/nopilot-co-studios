# Editable PPTX Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `pptx` exports through a parallel python-pptx engine that builds native, editable, brand-tokenized shapes (text, tiles, panels, tables, charts, diagrams) from the same `::: ` block source — never flat images.

**Architecture:** `render.py` forks: when the locked export is `pptx`, it calls a new `studio/pptx_render.py` instead of Quarto. The pptx engine parses `source.md` (post meta-strip, raw `::: ` blocks — NOT diagrams/charts-expanded) into slides, maps each block to a native PowerPoint shape via python-pptx, brand-styled from the resolved token set. Output path / versioning / record-render are identical to the Quarto path. Reuses `charts._series` (chart data) and `diagrams._flatten_tree` (tree layout) so parsing/layout aren't duplicated. Built in 4 pixel-verified tiers.

**Tech Stack:** Python 3.12, python-pptx 1.0.2 (already a dep), libreoffice (PPTX→PDF for pixel verification, already present). Standalone tests run with `design/.venv/bin/python` (no pytest).

---

## Background the implementer needs

- **Spike proven (do not re-spike):** python-pptx builds native `add_chart` (real editable chart, `shape.has_chart==True`), `add_table`, `add_shape` (autoshapes), `add_textbox`; libreoffice renders the PPTX→PDF correctly. 16:9 = `Inches(13.333) x Inches(7.5)`, blank layout = `prs.slide_layouts[6]`.
- **render.py integration contract** (read `design/scripts/studio/render.py`):
  - `render(session_path, bump_kind)` returns `outputs: dict[str, Path]` (key = studio format e.g. `"pptx"`).
  - Reads state via `session_mod.read_state(session_path)`; `slug = state["brand"]`; `state["format"]` is the slug; `sfmt = formats_mod.studio_format(resolved)`.
  - `new_version = session_mod.next_version(session_path, bump_kind)`.
  - Output path: `session_path / "outputs" / f"{out_stem}.v{new_version}.pptx"` where `out_stem = _strip_version_label(state.get("source_filename","source.md").rsplit(".",1)[0] or "source")`.
  - Records via `session_mod.record_render(session_path, new_version, [sfmt], outputs)`.
  - The Quarto-presence check is the FIRST thing in `render()` (line ~59) — it must move AFTER the pptx fork so a pptx render doesn't require Quarto.
  - `tok = tokens_mod.resolve(slug)` gives the token dict (`color`/`space`/`radius`); `metacontent.strip(path)` gives clean markdown.
- **Token shape:** `tok["color"]` keys: `primary, secondary, tertiary, neutral, surface, on_primary` (hex strings).
- **Block grammar:** `::: <name>\n<body>\n:::` — same as `diagrams._DIV_RE`. Component classes (from slice 2/4a): `cover-slide, section-slide, kpi, pullquote, ds-callout, highlight, panel, stat-panel, chart, flow, process, timeline, hierarchy, org`. Plain markdown between blocks = headings/paragraphs/bullets.

All work is on branch `feat/pptx-engine` (already checked out; spec committed there).

---

## File Structure

**New:**
- `design/scripts/studio/pptx_render.py` — Markdown→PPTX builder (parse slides, emit native shapes, brand tokens).
- `tests/test_pptx.py` — standalone tests.

**Modified:**
- `design/scripts/studio/render.py` — fork pptx to the new engine; move the Quarto check.

---

## Task 1 (Tier 1): pptx_render skeleton — tokens, blank deck, slide split, text

**Files:**
- Create: `design/scripts/studio/pptx_render.py`
- Test: `tests/test_pptx.py`

- [ ] **Step 1: Write the failing test** (creates `tests/test_pptx.py`)

```python
#!/usr/bin/env python3
"""Editable PPTX engine (#19). Standalone; run:
    design/.venv/bin/python tests/test_pptx.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import pptx_render  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


TOK = {
    "color": {"neutral": "#142F54", "surface": "#21456b", "tertiary": "#B14B33",
              "on_primary": "#FFFFFF", "secondary": "#6B7280", "primary": "#2A3548"},
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# split_slides: headings and cover/section blocks start new slides.
md = (
    "::: cover-slide\n# Q3 Strategy\nSubtitle here.\n:::\n\n"
    "## Context\nA point about the market.\n\n"
    "## Plan\n- First\n- Second\n"
)
slides = pptx_render.split_slides(md)
check("split: 3 slides", len(slides) == 3, str(len(slides)))
check("split: first is cover", slides[0]["kind"] == "cover-slide", str(slides[0]))

# build_pptx writes a real .pptx with the right slide count.
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "deck.pptx"
    pptx_render.build_pptx(md, TOK, out)
    check("pptx written", out.exists() and out.stat().st_size > 0)
    from pptx import Presentation
    prs = Presentation(str(out))
    check("pptx slide count", len(prs.slides.__iter__.__self__._sldIdLst) == 3 or len(list(prs.slides)) == 3,
          str(len(list(prs.slides))))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: pptx (tier 1)")
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: FAIL — `No module named 'studio.pptx_render'`.

- [ ] **Step 3: Create `design/scripts/studio/pptx_render.py`**

```python
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
    slide's raw body. Each slide: {kind, title, body}. kind ∈
    {cover-slide, section-slide, content}.
    """
    # Tokenize into (boundary?, line) — find slide-start positions.
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
            # consume the whole fenced div as this slide's body
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
            slides.append({"kind": name, "title": title, "body": "\n".join(rest).strip()})
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
    # Drop empty leading content slides with no title and no body.
    return [s for s in slides if s.get("title") or s.get("body") or s["kind"] in _SLIDE_BLOCKS]


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
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                            Inches(_SLIDE_W_IN), Inches(_SLIDE_H_IN))
    _solid(bg, c["neutral"])
    title = s.shapes.add_textbox(Inches(1), Inches(2.8), Inches(11), Inches(1.4))
    _set_text(title.text_frame, slide.get("title") or "", size=44, color=c["on_primary"], bold=True)
    if slide.get("body"):
        sub = s.shapes.add_textbox(Inches(1), Inches(4.3), Inches(11), Inches(1.0))
        _set_text(sub.text_frame, slide["body"].splitlines()[0], size=20, color=c["on_primary"])


def _render_section(s, slide, tokens, prs) -> None:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                            Inches(_SLIDE_W_IN), Inches(_SLIDE_H_IN))
    _solid(bg, c["surface"])
    title = s.shapes.add_textbox(Inches(1), Inches(3.2), Inches(11), Inches(1.2))
    _set_text(title.text_frame, slide.get("title") or "", size=36, color=c["primary"], bold=True)


def _render_content(s, slide, tokens, prs) -> None:
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    c = tokens["color"]
    if slide.get("title"):
        t = s.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12), Inches(0.9))
        _set_text(t.text_frame, slide["title"], size=30, color=c["primary"], bold=True)
    body = slide.get("body", "")
    bullets = [ln[2:].strip() for ln in body.splitlines() if ln.strip().startswith("- ")]
    paras = [ln.strip() for ln in body.splitlines()
             if ln.strip() and not ln.strip().startswith("- ")]
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: PASS: pptx (tier 1).

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/pptx_render.py tests/test_pptx.py
git commit -m "pptx engine tier 1: slide split + cover/section/content text shapes (#19)"
```

---

## Task 2: Fork `render.py` to the pptx engine

**Files:**
- Modify: `design/scripts/studio/render.py`

- [ ] **Step 1: Read `render.py`'s `render()` top** (lines ~58-92). Confirm: the Quarto check is first; `state`, `slug`, `resolved`, `sfmt`, `new_version` are computed as described in Background.

- [ ] **Step 2: Add the import.** With the other `from . import ... as ..._mod` lines, add:
```python
from . import pptx_render as pptx_mod
```

- [ ] **Step 3: Move the Quarto check + add the fork.** The function currently starts:
```python
def render(session_path: Path, bump_kind: str) -> dict[str, Path]:
    if detect_quarto() is None:
        raise RuntimeError(
            "quarto not found on PATH.\n"
            ...
        )

    state = session_mod.read_state(session_path)
    slug = state["brand"]
    ...
    resolved = formats_mod.resolve(fmt_slug)
    sfmt = formats_mod.studio_format(resolved)
    ...
    formats = [sfmt]

    brand_yml = brand_mod.brand_yml_path(slug)
    if not brand_yml.exists():
        raise FileNotFoundError(f"brand spec missing: {brand_yml}")

    new_version = session_mod.next_version(session_path, bump_kind)
```
Make two edits:
(a) DELETE the leading `if detect_quarto() is None: raise RuntimeError(...)` block from the top of `render()`.
(b) Right AFTER the `new_version = session_mod.next_version(session_path, bump_kind)` line, insert the pptx fork, then the Quarto check (so Quarto is only required for non-pptx):
```python
    # pptx renders through the native python-pptx engine (#19), not Quarto.
    if sfmt == "pptx":
        out_stem = _strip_version_label(
            state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
        )
        dest = session_path / "outputs" / f"{out_stem}.v{new_version}.pptx"
        dest.parent.mkdir(parents=True, exist_ok=True)
        tok = tokens_mod.resolve(slug)
        body = metacontent.strip(session_path / "inputs" / "source.md")
        pptx_mod.build_pptx(body, tok, dest)
        outputs = {sfmt: dest}
        session_mod.record_render(session_path, new_version, [sfmt], outputs)
        return outputs

    # Non-pptx (html/pdf/revealjs) render through Quarto.
    if detect_quarto() is None:
        raise RuntimeError(
            "quarto not found on PATH.\n"
            "  Install: brew install --cask quarto  (or download from https://quarto.org/docs/get-started/)\n"
            "  Then re-run: studio render ..."
        )
```

- [ ] **Step 4: Verify render imports + pptx render works end to end.** Run:
```bash
design/.venv/bin/python -c "import sys; sys.path.insert(0,'design/scripts'); import studio.render; print('render imports OK')"
design/.venv/bin/python tests/test_pptx.py
```
Expected: `render imports OK`; `PASS: pptx (tier 1)`.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/render.py
git commit -m "render: fork pptx export to the native pptx engine; Quarto only for html/pdf (#19)"
```

---

## Task 3 (Tier 1 gate): PIXEL VERIFICATION — basic branded deck

**Files:** none (verification)

- [ ] **Step 1: Render a deck and convert.** Run this exactly:
```bash
cd /Users/ted/Projects/nopilot-co-studios
TMP=$(mktemp -d); STUDIO=design/.venv/bin/studio; PY=design/.venv/bin/python
BRAND=$($PY -c "import sys;sys.path.insert(0,'design/scripts');from studio import brand;print(brand.brand_root('360'))")
STUDIOS_DOCKET_ROOT="$TMP" $STUDIO ingest --brand 360 --import-from "$BRAND" >/dev/null 2>&1
printf '::: cover-slide\n# Q3 Strategy\nThe one-line setup.\n:::\n\n## Context\nThe market shifted this quarter.\n\n## Plan\n- Ship the engine\n- Win the room\n' > "$TMP/d.md"
SP="$TMP/360/outputs/deck"
STUDIOS_DOCKET_ROOT="$TMP" $STUDIO session init --brand 360 --name deck --format pitch-pptx --source "$TMP/d.md" >/dev/null 2>&1
STUDIOS_DOCKET_ROOT="$TMP" $STUDIO render --session "$SP" --bump minor; echo "rc=$?"
PPTX=$(ls "$SP"/outputs/*.pptx | head -1); echo "PPTX=$PPTX"
soffice --headless --convert-to pdf --outdir "$TMP" "$PPTX" >/dev/null 2>&1
PDF="$TMP/$(basename "${PPTX%.pptx}").pdf"
$PY -c "import pypdfium2 as p; d=p.PdfDocument('$PDF'); print('pages',len(d)); [d[i].render(scale=1.2).to_pil().save(f'/tmp/pptx_t1_{i+1}.png') for i in range(min(3,len(d)))]"
```
Expected: `rc=0`, a `.pptx` produced, 3 pages, PNGs written.

- [ ] **Step 2: Inspect `/tmp/pptx_t1_1.png` … `_3.png`.** CONFIRM: slide 1 is a neutral-fill cover with white title + subtitle; slides 2–3 are content slides with a brand-coloured title and body/bullets. If blank/unstyled/wrong slide count, STOP and report with the image. Do not proceed on "it saved".

- [ ] **Step 3: Confirm shapes are NATIVE (not images).** Run:
```bash
design/.venv/bin/python -c "
from pptx import Presentation
prs = Presentation('$PPTX')
from pptx.enum.shapes import MSO_SHAPE_TYPE
for i, sl in enumerate(prs.slides):
    kinds=[str(sh.shape_type) for sh in sl.shapes]
    print(i, kinds)
    assert not any('PICTURE' in k for k in kinds), 'found a picture — not native!'
print('all shapes native')
"
```
Expected: shapes are AUTO_SHAPE / TEXT_BOX, `all shapes native`. (Replace `$PPTX` with the path printed above.)

- [ ] **Step 4: No commit.** If green, proceed. If not, report.

---

## Task 4 (Tier 2): tiles, panels, native table

**Files:**
- Modify: `design/scripts/studio/pptx_render.py`, `tests/test_pptx.py`

- [ ] **Step 1: Add assertions** to `tests/test_pptx.py` before the final `if failures:`:

```python
# Tier 2: a slide bearing ::: kpi / ::: panel / a markdown table emits native shapes.
md2 = (
    "## Numbers\n\n"
    "::: kpi\n87% faster\n:::\n\n"
    "::: panel\nA framed aside.\n:::\n\n"
    "| Metric | Value |\n|---|---|\n| Revenue | 1.8M |\n| Margin | 17% |\n"
)
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "d2.pptx"
    pptx_render.build_pptx(md2, TOK, out)
    from pptx import Presentation
    prs = Presentation(str(out))
    sl = list(prs.slides)[0]
    has_table = any(getattr(sh, "has_table", False) for sh in sl.shapes)
    has_auto = any("AUTO_SHAPE" in str(sh.shape_type) for sh in sl.shapes)
    check("tier2 native table", has_table, str([str(sh.shape_type) for sh in sl.shapes]))
    check("tier2 panel autoshape", has_auto)
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: FAIL — tier2 assertions (no table/autoshape yet; content renderer only does text).

- [ ] **Step 3: Implement tier-2 blocks.** In `pptx_render.py`, rewrite `_render_content` to walk the slide body as a sequence of blocks (fenced divs, markdown tables, and text), stacking them vertically. Replace the whole `_render_content` function with:

```python
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
    pos = 0
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
            # gather a contiguous markdown table
            _flush_text()
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i]); i += 1
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


_PANEL_FILL = {"panel": None, "highlight": "surface", "ds-callout": "surface",
               "pullquote": None, "stat-panel": "surface", "kpi": "surface"}


def _place_block(s, block, tokens, top: float) -> float:
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    kind = block["kind"]
    if kind == "table":
        return _place_table(s, block["rows"], tokens, top)
    if kind == "kpi":
        shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(0.6), Inches(top), Inches(6), Inches(1.6))
        _solid(shp, c["surface"])
        _set_text(shp.text_frame, block["body"], size=40, color=c["tertiary"], bold=True)
        return top + 1.9
    if kind in _PANEL_FILL:
        h = 1.3
        shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(0.6), Inches(top), Inches(12), Inches(h))
        fill = _PANEL_FILL[kind]
        if fill:
            _solid(shp, c[fill])
        else:
            shp.fill.background()
            from pptx.dml.color import RGBColor
            shp.line.color.rgb = RGBColor.from_string(_hex(c["secondary"]))
        txt_color = c["primary"]
        _set_text(shp.text_frame, block["body"], size=18, color=txt_color)
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
    gframe = s.shapes.add_table(nrows, ncols, Inches(0.6), Inches(top),
                                Inches(8), Inches(0.4 * nrows))
    tbl = gframe.table
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            cell = tbl.cell(ri, ci)
            cell.text = row[ci] if ci < len(row) else ""
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(14)
                    run.font.color.rgb = RGBColor.from_string(
                        _hex(c["on_primary"] if ri == 0 else c["primary"]))
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: PASS — tier2 native table + autoshape assertions green; tier-1 still green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/pptx_render.py tests/test_pptx.py
git commit -m "pptx engine tier 2: kpi / panels / native table as native shapes (#19)"
```

---

## Task 5 (Tier 2 gate): PIXEL VERIFICATION — tiles, panels, table

**Files:** none (verification)

- [ ] **Step 1: Render + convert** (same harness as Task 3 Step 1, but body):
```
## Numbers

::: kpi
87% faster delivery
:::

::: panel
A neutral framed aside for supporting content.
:::

| Metric | Q1 | Q2 |
|---|---|---|
| Revenue | 1.2 | 1.8 |
| Margin | 12% | 17% |
```
Use `--format pitch-pptx`, render, `soffice --convert-to pdf`, rasterize page 1 to `/tmp/pptx_t2_1.png`.

- [ ] **Step 2: Inspect `/tmp/pptx_t2_1.png`.** CONFIRM: a surface-fill rounded KPI tile with the large accent figure; a framed/outlined panel; a branded table with a surface header row. If wrong, STOP and report.

- [ ] **Step 3: No commit.** Proceed if green.

---

## Task 6 (Tier 3): native chart

**Files:**
- Modify: `design/scripts/studio/pptx_render.py`, `tests/test_pptx.py`

- [ ] **Step 1: Add assertions** to `tests/test_pptx.py` before the final `if failures:`:

```python
# Tier 3: ::: chart -> a NATIVE editable chart object.
md3 = "## Revenue\n\n::: chart\ntype: bar\nx: [Q1, Q2, Q3]\ny: [12, 18, 15]\n:::\n"
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "d3.pptx"
    pptx_render.build_pptx(md3, TOK, out)
    from pptx import Presentation
    prs = Presentation(str(out))
    sl = list(prs.slides)[0]
    check("tier3 native chart", any(getattr(sh, "has_chart", False) for sh in sl.shapes),
          str([str(sh.shape_type) for sh in sl.shapes]))
# bad chart YAML -> slide still builds (degrade)
md3b = "## Oops\n\n::: chart\ntype: nope\n:::\n"
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "d3b.pptx"
    pptx_render.build_pptx(md3b, TOK, out)  # must not raise
    check("tier3 bad chart no crash", out.exists())
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: FAIL — tier3 native chart (chart block currently falls to the panel/text path).

- [ ] **Step 3: Implement the chart block.** In `pptx_render.py`, add a `chart` branch to `_place_block` BEFORE the `if kind in _PANEL_FILL:` check:

```python
    if kind == "chart":
        return _place_chart(s, block["body"], tokens, top)
```

And add the chart renderer + a small type map (reuse `charts._series` for data parsing):

```python
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
        from pptx.util import Inches as _In

        tb = s.shapes.add_textbox(_In(0.6), _In(top), _In(12), _In(0.8))
        _set_text(tb.text_frame, "[chart could not render]", size=14,
                  color=tokens["color"]["secondary"])
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
        cd.add_series("", tuple(float(v) for v in (spec.get("values") or spec.get("y") or [])))
    else:
        cd.categories = cats or [str(i) for i in range(len(series[0]["y"]) if series else 0)]
        for sname_y in series:
            cd.add_series(sname_y["name"] or "series", tuple(sname_y["y"]))
    gframe = s.shapes.add_chart(xltype, Inches(0.6), Inches(top), Inches(8.5), Inches(4.0), cd)
    chart = gframe.chart
    chart.has_legend = any(sy["name"] for sy in series)
    # Brand the first series accent (best-effort; native chart keeps its editability).
    try:
        palette = [c["tertiary"], c["primary"], c["secondary"]]
        for pi, plot in enumerate(chart.plots):
            for si, ser in enumerate(plot.series):
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = RGBColor.from_string(
                    _hex(palette[si % len(palette)]))
    except Exception:  # noqa: BLE001 — colour is best-effort; never fail the render
        pass
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: PASS — tier3 native chart + bad-chart-degrades green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/pptx_render.py tests/test_pptx.py
git commit -m "pptx engine tier 3: ::: chart -> native editable chart object, brand-coloured (#19)"
```

---

## Task 7 (Tier 3 gate): PIXEL VERIFICATION — native chart

**Files:** none (verification)

- [ ] **Step 1: Render + convert** a deck whose body is:
```
## Revenue

::: chart
type: bar
title: Revenue by quarter
x: [Q1, Q2, Q3, Q4]
y: [12, 18, 15, 24]
:::
```
`--format pitch-pptx`, render, convert via soffice, rasterize page 1 to `/tmp/pptx_t3_1.png`. Also assert the chart is native:
```bash
design/.venv/bin/python -c "from pptx import Presentation; prs=Presentation('PPTX_PATH'); print('native chart:', any(getattr(sh,'has_chart',False) for sl in prs.slides for sh in sl.shapes))"
```
(Replace PPTX_PATH.)

- [ ] **Step 2: Inspect `/tmp/pptx_t3_1.png`.** CONFIRM a real bar chart with the four quarters and brand-accent bars. `native chart: True`. If a flat image or wrong, STOP and report.

- [ ] **Step 3: No commit.** Proceed if green.

---

## Task 8 (Tier 4 — HARD): diagrams as native autoshapes + connectors

**Files:**
- Modify: `design/scripts/studio/pptx_render.py`, `tests/test_pptx.py`

> **Honest-ceiling note:** this tier (native shape layout + connectors in EMU) is the
> riskiest. If it does not reach a clean pixel result after a reasonable attempt,
> STOP, commit tiers 1–3, and report it as DONE_WITH_CONCERNS with a recommendation
> to split tier 4 into a follow-up issue. Do NOT ship broken/overlapping diagrams.

- [ ] **Step 1: Add assertions** to `tests/test_pptx.py` before the final `if failures:`:

```python
# Tier 4: ::: flow / ::: org -> native autoshapes (boxes) + connectors.
md4 = "## Process\n\n::: flow\nnodes: [Brief, Plan, Render]\n:::\n"
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "d4.pptx"
    pptx_render.build_pptx(md4, TOK, out)
    from pptx import Presentation
    prs = Presentation(str(out))
    sl = list(prs.slides)[0]
    autoshapes = [sh for sh in sl.shapes if "AUTO_SHAPE" in str(sh.shape_type)]
    check("tier4 flow boxes", len(autoshapes) >= 3, str(len(autoshapes)))
md4b = ("## Org\n\n::: org\nroot: CEO\nchildren:\n  - root: CTO\n"
        "    children: [Eng, Data]\n  - COO\n:::\n")
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "d4b.pptx"
    pptx_render.build_pptx(md4b, TOK, out)
    prs = Presentation(str(out))
    sl = list(prs.slides)[0]
    autoshapes = [sh for sh in sl.shapes if "AUTO_SHAPE" in str(sh.shape_type)]
    check("tier4 org boxes", len(autoshapes) >= 5, str(len(autoshapes)))
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: FAIL — diagram blocks currently hit the panel/text path, not boxes.

- [ ] **Step 3: Implement diagram blocks.** In `_place_block`, add BEFORE the `_PANEL_FILL` check:
```python
    if kind in ("flow", "process", "timeline", "hierarchy", "org"):
        return _place_diagram(s, kind, block["body"], tokens, top)
```
Add the renderer (reuse `diagrams._flatten_tree` for trees; linear for flow/process/timeline):
```python
def _place_diagram(s, kind, body, tokens, top: float) -> float:
    try:
        import yaml

        spec = yaml.safe_load(body) or {}
        if kind in ("flow", "process", "timeline"):
            if kind == "timeline":
                labels = [str(e.get("label", "")) for e in (spec.get("events") or [])
                          if isinstance(e, dict)]
            else:
                labels = [str(x) for x in (spec.get("nodes") or spec.get("steps") or [])]
            _diagram_linear(s, labels, tokens, top)
        else:
            from . import diagrams as diagrams_mod

            nodes, edges = diagrams_mod._flatten_tree(spec)
            _diagram_tree(s, nodes, edges, tokens, top)
        return top + 4.2
    except Exception:  # noqa: BLE001 — degrade
        from pptx.util import Inches

        tb = s.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12), Inches(0.8))
        _set_text(tb.text_frame, f"[diagram '{kind}' could not render]", size=14,
                  color=tokens["color"]["secondary"])
        return top + 1.0


def _node_box(s, x_in, y_in, w_in, h_in, label, tokens):
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    c = tokens["color"]
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(x_in), Inches(y_in), Inches(w_in), Inches(h_in))
    _solid(shp, c["neutral"])
    _set_text(shp.text_frame, label, size=14, color=c["on_primary"], bold=False)
    return shp


def _connect(s, a, b, tokens):
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.dml.color import RGBColor
    from pptx.util import Emu

    c = tokens["color"]
    conn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                  Emu(a.left + a.width // 2), Emu(a.top + a.height),
                                  Emu(b.left + b.width // 2), Emu(b.top))
    conn.line.color.rgb = RGBColor.from_string(_hex(c["tertiary"]))
    conn.line.width = Emu(19050)  # ~1.5pt


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


def _connect_h(s, a, b, tokens):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.util import Emu

    c = tokens["color"]
    conn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                  Emu(a.left + a.width), Emu(a.top + a.height // 2),
                                  Emu(b.left), Emu(b.top + b.height // 2))
    conn.line.color.rgb = RGBColor.from_string(_hex(c["tertiary"]))
    conn.line.width = Emu(19050)


def _diagram_tree(s, nodes, edges, tokens, top: float) -> None:
    maxx = max((nd["x"] for nd in nodes), default=0) or 1
    maxd = max((nd["depth"] for nd in nodes), default=0) or 1
    w, h = 1.7, 0.7
    left0, span_w = 1.0, 11.0
    row_h = 3.6 / (maxd + 1)
    placed = {}
    for nd in nodes:
        cx = left0 + (nd["x"] / maxx) * span_w if maxx else left0
        cy = top + 1.0 + nd["depth"] * row_h
        placed[nd["id"]] = _node_box(s, cx, cy, w, h, nd["label"], tokens)
    for a, b in edges:
        _connect(s, placed[a], placed[b], tokens)
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: PASS — tier4 box-count assertions green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/pptx_render.py tests/test_pptx.py
git commit -m "pptx engine tier 4: flow/process/timeline/org as native shapes + connectors (#19)"
```

---

## Task 9 (Tier 4 gate): PIXEL VERIFICATION — diagrams as native shapes

**Files:** none (verification)

- [ ] **Step 1: Render + convert** a deck with a `::: flow` and a `::: org` (one per slide via `## ` headings), `--format pitch-pptx`, soffice→PDF, rasterize pages to `/tmp/pptx_t4_*.png`.

- [ ] **Step 2: Inspect.** CONFIRM: flow = a row of branded boxes joined by accent connectors; org = a tree of boxes with parent→child connectors, no major overlaps. **If overlapping/broken/illegible:** STOP. Commit tiers 1–3 (already committed), and report DONE_WITH_CONCERNS recommending tier 4 be split to a follow-up issue. Do not force it.

- [ ] **Step 3: No commit.**

---

## Task 10: README + full regression + PR

**Files:**
- Modify: `design/formats/README.md`

- [ ] **Step 1: Update `design/formats/README.md`.** Add a short "### PPTX (native editable decks)" subsection: pptx exports render through `studio.pptx_render` (NOT Quarto) into native editable shapes — text, kpi/panels, native tables + charts, and diagram shapes; same `::: ` block source. ≤18 lines.

- [ ] **Step 2: Full regression**

Run: `design/.venv/bin/python tests/test_pptx.py && design/.venv/bin/python tests/test_charts.py && design/.venv/bin/python tests/test_diagrams.py && design/.venv/bin/python tests/test_components.py && design/.venv/bin/python tests/test_formats.py && design/.venv/bin/python tests/test_storage_root.py && design/.venv/bin/python tests/test_docket.py`
Expected: all seven PASS.

- [ ] **Step 3: Commit + push + PR**

```bash
git add design/formats/README.md
git commit -m "docs: pptx native-editable deck authoring (#19)"
git push -u origin feat/pptx-engine
gh pr create --title "Editable PPTX engine (#19): native shapes via parallel python-pptx path" \
  --body "Implements docs/superpowers/specs/2026-06-02-pptx-engine-design.md. Closes #19. render.py forks pptx to studio/pptx_render.py — native editable text/kpi/panels/tables/charts/diagrams from the same ::: blocks, brand-tokenized. Pixel-verified per tier (libreoffice->PDF). gslide import deferred. If tier 4 (diagrams) was split, that's noted in the PR."
```

- [ ] **Step 4: Final confirmation**

Run: `design/.venv/bin/python tests/test_pptx.py`
Expected: PASS.

---

## Self-Review (completed by plan author)

- **Spec coverage:** parallel render fork → T2; pptx_render module → T1; tier 1 text/cover/section → T1; tier 2 tiles/panels/table → T4; tier 3 native chart (reusing charts._series) → T6; tier 4 diagrams (reusing diagrams._flatten_tree) → T8; pixel gates per tier → T3/T5/T7/T9; degrade-on-bad-input → T6/T8; README → T10; PPTX↔native verification (has_chart/has_table/no-picture) → T3/T4/T6. gslide import explicitly deferred (spec). ✔ no gaps.
- **Placeholder scan:** none — full code in every code step; verification steps name exact images + native-shape assertions; the honest tier-4 split is an explicit instruction, not a vague hedge.
- **Type consistency:** `pptx_render.split_slides(markdown) -> list[dict]`, `build_pptx(markdown, tokens, out_path) -> Path`, `_render_cover/_render_section/_render_content`, `_content_blocks`, `_place_block/_place_table/_place_chart/_place_diagram`, `_node_box/_connect/_connect_h/_diagram_linear/_diagram_tree`, `_solid/_set_text/_set_text_multiline/_hex` — names consistent across tasks. Reuses `charts._series`, `charts.CHART_TYPES`, `diagrams._flatten_tree` (verified to exist). `sfmt`/`tok`/`new_version`/`out_stem` match render.py locals.
