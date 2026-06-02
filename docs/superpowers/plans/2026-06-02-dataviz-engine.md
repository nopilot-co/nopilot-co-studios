# data-viz Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `::: chart` data-viz blocks (bar, line, pie, scatter, area) as designed, on-brand charts in HTML and PDF with true parity, from one matplotlib SVG engine.

**Architecture:** A new `studio/charts.py` generates a brand-styled SVG per chart with matplotlib. `charts.expand()` runs in `render.py`'s preprocess (right after `diagrams.expand`), finds `::: chart` divs, writes each to `<tmp>/_chart-N.svg`, and replaces the div with an inline image (HTML) or a Typst `#image()` block (PDF) — the SAME SVG both sides. matplotlib is a normal Python dep that degrades to a visible fallback panel when absent. Verification bar is rendered pixels.

**Tech Stack:** Python 3.12, matplotlib (SVG backend), PyYAML. Standalone tests run with `design/.venv/bin/python` (no pytest).

---

## Background the implementer needs

- **Spike proven (do not re-spike):** matplotlib emits SVG for all 5 chart types; the SVG renders in HTML natively (Quarto inlines it) AND through Typst `#image("chart.svg")` into PDF with crisp text + brand colour — pixel-verified.
- **The preprocess seam** is `design/scripts/studio/render.py`. The current block (around line 104-107) is:
  ```python
  tok = tokens_mod.resolve(slug)
  body = metacontent.strip(source_md)
  body = diagrams_mod.expand(body, sfmt, tok)
  (tmp / "source.md").write_text(body, encoding="utf-8")
  ```
  `sfmt` is the locked studio format ("pdf"/"html"/...), `tok` the resolved tokens, `tmp` the writable render project dir (`session_path / "_render"`). The charts call goes between the `diagrams_mod.expand` line and the `write_text` line.
- **Mirror `diagrams.py` conventions:** the `_DIV_RE` regex for fenced divs, the `_fallback` panel for bad input, and the `expand(markdown, export, tokens, ...)` signature shape. Charts differ in ONE way: they take an extra `out_dir` (charts write a file; diagrams emit inline source).
- **Token shape:** `tokens["color"]` has keys `primary, secondary, tertiary, neutral, surface, on_primary` (hex strings); also `space`, `radius`. Use `tertiary` as the primary series colour (the brand accent), then `primary`, `secondary`.
- **Dependency:** matplotlib goes in `design/pyproject.toml` `dependencies` (lines 12-20). The design venv is uv-managed; install with `VIRTUAL_ENV=design/.venv uv pip install matplotlib` (there is no `pip` in the venv). matplotlib import must be LAZY (inside functions) so `import studio.charts` doesn't fail when matplotlib is absent — that's what lets the degrade-to-fallback path work.

All work is on branch `feat/dataviz-engine` (already checked out; the approved spec is committed there).

---

## File Structure

**New:**
- `design/scripts/studio/charts.py` — parse `::: chart` YAML, render brand-styled SVG (matplotlib), expand per export.
- `tests/test_charts.py` — standalone tests.

**Modified:**
- `design/scripts/studio/render.py` — call `charts.expand()` in preprocess.
- `design/pyproject.toml` — add matplotlib dependency.
- `design/formats/assets/data-viz.yml` — structured-YAML authoring + render_notes.
- `design/formats/README.md` — chart authoring section.

---

## Task 1: Install matplotlib + declare the dependency

**Files:**
- Modify: `design/pyproject.toml`

- [ ] **Step 1: Add matplotlib to dependencies.** In `design/pyproject.toml`, the `dependencies = [ ... ]` list (lines 12-20) ends with `"click>=8.1",`. Add a line before the closing `]`:
```toml
  "matplotlib>=3.8",
```

- [ ] **Step 2: Install it into the design venv**

Run: `VIRTUAL_ENV=design/.venv uv pip install "matplotlib>=3.8"`
Expected: resolves + installs matplotlib (and numpy). If `uv` is not found, try `/Users/ted/.local/bin/uv`.

- [ ] **Step 3: Verify import**

Run: `design/.venv/bin/python -c "import matplotlib; matplotlib.use('svg'); print('matplotlib', matplotlib.__version__)"`
Expected: prints a version ≥ 3.8.

- [ ] **Step 4: Commit**

```bash
git add design/pyproject.toml
git commit -m "deps: add matplotlib for the data-viz engine (#20)"
```

---

## Task 2: `charts.py` — render a bar chart SVG from a spec

**Files:**
- Create: `design/scripts/studio/charts.py`
- Test: `tests/test_charts.py`

- [ ] **Step 1: Write the failing test** (creates `tests/test_charts.py`)

```python
#!/usr/bin/env python3
"""data-viz engine (#20) — matplotlib SVG charts, expanded per export.
Standalone; run: design/.venv/bin/python tests/test_charts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import charts  # noqa: E402

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

# bar: a single series renders to SVG with the data + brand colour.
svg = charts.render_svg({"type": "bar", "title": "Revenue",
                         "x": ["Q1", "Q2", "Q3", "Q4"], "y": [12, 18, 15, 24]}, TOK)
check("bar: is svg", svg.lstrip().startswith("<?xml") or "<svg" in svg[:400], svg[:80])
check("bar: has title", "Revenue" in svg)
check("bar: brand accent", "B14B33" in svg or "b14b33" in svg.lower(), "accent colour missing")

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: charts (bar)")
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_charts.py`
Expected: FAIL — `No module named 'studio.charts'`.

- [ ] **Step 3: Create `design/scripts/studio/charts.py`**

```python
"""data-viz engine (#20).

Renders `::: chart` fenced divs (YAML body) to brand-styled SVG via matplotlib —
the SAME SVG embedded inline in HTML and placed with Typst `#image()` in PDF, so
the two targets are identical (true parity, no per-engine divergence).

matplotlib is imported LAZILY so the module loads even when it's absent; in that
case each chart degrades to a visible fallback panel (the render never crashes).

Runs in render.py's preprocess step, after diagrams.expand.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Same fenced-div grammar as diagrams.py.
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

CHART_CLASS = "chart"
CHART_TYPES = {"bar", "line", "pie", "scatter", "area"}


def _series(spec: dict) -> list[dict]:
    """Normalise to a list of {name, y} series. Supports single `y` or `series`."""
    if spec.get("series"):
        out = []
        for s in spec["series"]:
            out.append({"name": str(s.get("name", "")), "y": [float(v) for v in s.get("y", [])]})
        return out
    if spec.get("y") is not None:
        return [{"name": str(spec.get("name", "")), "y": [float(v) for v in spec["y"]]}]
    return []


def _palette(tokens: dict) -> list[str]:
    c = tokens["color"]
    return [c["tertiary"], c["primary"], c["secondary"], c["neutral"], c["surface"]]


def render_svg(spec: dict, tokens: dict) -> str:
    """Render one chart spec to an SVG string. Raises on bad spec (caller catches)."""
    import matplotlib

    matplotlib.use("svg")
    import io

    import matplotlib.pyplot as plt

    ctype = spec.get("type", "bar")
    if ctype not in CHART_TYPES:
        raise ValueError(f"unknown chart type '{ctype}'")

    c = tokens["color"]
    palette = _palette(tokens)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = [str(v) for v in (spec.get("x") or spec.get("labels") or [])]
    series = _series(spec)

    if ctype == "pie":
        values = [float(v) for v in (spec.get("values") or spec.get("y") or [])]
        labels = x or [str(i) for i in range(len(values))]
        ax.pie(values, labels=labels, colors=palette,
               textprops={"color": c["primary"]})
        ax.set_aspect("equal")
    elif ctype == "bar":
        n = len(series)
        idx = range(len(x))
        width = 0.8 / max(n, 1)
        for si, s in enumerate(series):
            offs = [i + si * width - 0.4 + width / 2 for i in idx]
            ax.bar(offs, s["y"], width=width, color=palette[si % len(palette)],
                   label=s["name"] or None)
        ax.set_xticks(list(idx))
        ax.set_xticklabels(x)
    elif ctype in ("line", "area"):
        for si, s in enumerate(series):
            col = palette[si % len(palette)]
            ax.plot(range(len(s["y"])), s["y"], color=col, label=s["name"] or None)
            if ctype == "area":
                ax.fill_between(range(len(s["y"])), s["y"], color=col, alpha=0.25)
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x)
    elif ctype == "scatter":
        for si, s in enumerate(series):
            ax.scatter(range(len(s["y"])), s["y"], color=palette[si % len(palette)],
                       label=s["name"] or None)
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x)

    if spec.get("title"):
        ax.set_title(str(spec["title"]), color=c["primary"])
    ax.tick_params(colors=c["secondary"])
    for sp in ("top", "right"):
        if sp in ax.spines:
            ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        if sp in ax.spines:
            ax.spines[sp].set_color(c["secondary"])
    if any(s["name"] for s in series) and ctype != "pie":
        ax.legend(frameon=False, labelcolor=c["primary"])
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    fig.tight_layout()

    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    plt.close(fig)
    return buf.getvalue()


def _fallback(body: str, err: str) -> str:
    return (
        f"::: panel\n**[chart could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )


def expand(markdown: str, export: str, tokens: dict[str, Any], out_dir: Path) -> str:
    """Replace every `::: chart` div with an image of its rendered SVG, for `export`.

    HTML: a markdown image referencing the written SVG (Quarto inlines it).
    PDF:  a Typst `#image()` raw block (keeps the SVG as vector).
    Other exports / non-chart divs pass through unchanged.
    """
    if export not in ("html", "pdf"):
        return markdown

    counter = [0]

    def _sub(m: re.Match) -> str:
        if m.group("name") != CHART_CLASS:
            return m.group(0)
        try:
            spec = yaml.safe_load(m.group("body")) or {}
            if not isinstance(spec, dict):
                raise ValueError("chart body must be a YAML mapping")
            svg = render_svg(spec, tokens)
        except Exception as e:  # noqa: BLE001 — never crash a render
            return _fallback(m.group("body"), str(e))
        counter[0] += 1
        name = f"_chart-{counter[0]}.svg"
        (out_dir / name).write_text(svg, encoding="utf-8")
        if export == "pdf":
            return f'```{{=typst}}\n#image("{name}", width: 100%)\n```\n'
        return f"![]({name})\n"

    return _DIV_RE.sub(_sub, markdown)
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_charts.py`
Expected: PASS: charts (bar).

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/charts.py tests/test_charts.py
git commit -m "charts.py: matplotlib SVG bar chart from a spec (#20)"
```
(If a pre-commit hook reformats, re-`git add` and re-commit.)

---

## Task 3: All chart types + multi-series + fallback (test coverage)

**Files:**
- Modify: `tests/test_charts.py` (the implementation in Task 2 already handles all types; this task proves it)

- [ ] **Step 1: Add assertions** to `tests/test_charts.py` before the final `if failures:`:

```python
# every type renders valid SVG.
for ctype in ("line", "pie", "scatter", "area"):
    spec = {"type": ctype, "x": ["A", "B", "C"], "y": [3, 5, 4]}
    if ctype == "pie":
        spec = {"type": "pie", "labels": ["A", "B", "C"], "values": [3, 5, 4]}
    s = charts.render_svg(spec, TOK)
    check(f"{ctype}: is svg", "<svg" in s[:400], ctype)

# multi-series bar.
ms = charts.render_svg({"type": "bar", "x": ["Q1", "Q2"],
                        "series": [{"name": "Plan", "y": [10, 14]},
                                   {"name": "Actual", "y": [12, 18]}]}, TOK)
check("multi-series legend", "Plan" in ms and "Actual" in ms)

# bad type -> render_svg raises (so expand can catch it).
import tempfile
raised = False
try:
    charts.render_svg({"type": "nope", "y": [1]}, TOK)
except Exception:
    raised = True
check("bad type raises", raised)

# expand: writes an SVG file + replaces the div; bad chart -> fallback, no crash.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    doc = "Intro.\n\n::: chart\ntype: bar\nx: [Q1, Q2]\ny: [3, 9]\n:::\n\nOutro.\n"
    h = charts.expand(doc, "html", TOK, out)
    check("expand html img", "![](_chart-1.svg)" in h, h)
    check("expand wrote svg", (out / "_chart-1.svg").exists())
    check("expand prose kept", "Intro." in h and "Outro." in h)
    p = charts.expand(doc, "pdf", TOK, out)
    check("expand pdf image", "#image(" in p and "_chart-" in p, p)
    bad = charts.expand("::: chart\ntype: nope\n:::\n", "html", TOK, out)
    check("expand bad -> fallback", "could not render" in bad and "::: panel" in bad)
    # non-chart div passes through
    other = "::: pullquote\nhi\n:::\n"
    check("expand passthrough", charts.expand(other, "html", TOK, out) == other)
```

- [ ] **Step 2: Run to verify**

Run: `design/.venv/bin/python tests/test_charts.py`
Expected: PASS (all type + expand + fallback assertions green). If any chart type raises inside `render_svg`, fix the type's branch in `charts.py` until the SVG is produced.

- [ ] **Step 3: Commit**

```bash
git add tests/test_charts.py
git commit -m "charts: cover all 5 types + multi-series + expand/fallback (#20)"
```

---

## Task 4: Wire `charts.expand` into `render.py`

**Files:**
- Modify: `design/scripts/studio/render.py`

- [ ] **Step 1: Read the preprocess block** (around lines 104-107) and confirm it matches:
```python
    tok = tokens_mod.resolve(slug)
    body = metacontent.strip(source_md)
    body = diagrams_mod.expand(body, sfmt, tok)
    (tmp / "source.md").write_text(body, encoding="utf-8")
```

- [ ] **Step 2: Add the import.** Near the other `from . import ... as ..._mod` lines, add:
```python
from . import charts as charts_mod
```

- [ ] **Step 3: Insert the charts expansion.** Replace:
```python
    body = diagrams_mod.expand(body, sfmt, tok)
    (tmp / "source.md").write_text(body, encoding="utf-8")
```
with:
```python
    body = diagrams_mod.expand(body, sfmt, tok)
    # Charts write a brand-styled SVG into the render dir and reference it (#20).
    body = charts_mod.expand(body, sfmt, tok, tmp)
    (tmp / "source.md").write_text(body, encoding="utf-8")
```

- [ ] **Step 4: Verify render imports clean**

Run: `design/.venv/bin/python -c "import sys; sys.path.insert(0,'design/scripts'); import studio.render; print('render imports OK')"`
Expected: `render imports OK`

Also: `design/.venv/bin/python tests/test_charts.py && design/.venv/bin/python tests/test_diagrams.py`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/render.py
git commit -m "render: expand ::: chart blocks to SVG in preprocess (#20)"
```

---

## Task 5: PIXEL VERIFICATION — render all 5 chart types to PDF + HTML and look

**Files:** none (verification; produces images for review)

- [ ] **Step 1: Write `/tmp/chart_verify.sh`:**

```bash
#!/usr/bin/env bash
set -uo pipefail
cd /Users/ted/Projects/nopilot-co-studios
STUDIO=design/.venv/bin/studio; PY=design/.venv/bin/python
TMP=$(mktemp -d); echo "TMP=$TMP"
BRAND=$($PY -c "import sys;sys.path.insert(0,'design/scripts');from studio import brand;print(brand.brand_root('360'))")
STUDIOS_DOCKET_ROOT="$TMP" $STUDIO ingest --brand 360 --import-from "$BRAND" >/dev/null 2>&1
cat > "$TMP/c.md" <<'DOC'
# Chart test

::: chart
type: bar
title: Revenue by quarter
x: [Q1, Q2, Q3, Q4]
y: [12, 18, 15, 24]
:::

::: chart
type: line
title: Trend
x: [Q1, Q2, Q3, Q4]
series:
  - {name: Plan, y: [10, 14, 12, 20]}
  - {name: Actual, y: [12, 18, 15, 24]}
:::

::: chart
type: pie
title: Mix
labels: [Direct, Partner, Online]
values: [40, 35, 25]
:::

::: chart
type: scatter
title: Spread
x: [1, 2, 3, 4, 5]
y: [5, 9, 4, 11, 7]
:::

::: chart
type: area
title: Cumulative
x: [Q1, Q2, Q3, Q4]
y: [12, 18, 15, 24]
:::
DOC
for fmt in proposal-pdf proposal-html; do
  NAME="chart-${fmt##*-}"; SP="$TMP/360/outputs/$NAME"
  STUDIOS_DOCKET_ROOT="$TMP" $STUDIO session init --brand 360 --name "$NAME" --format "$fmt" --source "$TMP/c.md" >/dev/null 2>&1
  STUDIOS_DOCKET_ROOT="$TMP" $STUDIO render --session "$SP" --bump minor; echo "$fmt rc=$?"
done
PDF=$(ls "$TMP"/360/outputs/chart-pdf/outputs/*.pdf 2>/dev/null | head -1)
[ -n "$PDF" ] && $PY -c "import pypdfium2 as p; d=p.PdfDocument('$PDF'); print('pdf pages',len(d)); [d[i].render(scale=1.4).to_pil().save(f'/tmp/chart_pdf_{i+1}.png') for i in range(min(3,len(d)))]"
H=$(ls "$TMP"/360/outputs/chart-html/outputs/*.html 2>/dev/null | head -1)
[ -n "$H" ] && echo "html inline svg count: $(grep -c '<svg\|data:image/svg\|_chart-' "$H")"
echo DONE
```

- [ ] **Step 2: Run it**

Run: `bash /tmp/chart_verify.sh`
Expected: both `rc=0`; PDF pages printed; `/tmp/chart_pdf_1.png` (+`_2`) written; HTML shows inline SVG present.

- [ ] **Step 3: Inspect the pixels.** Read `/tmp/chart_pdf_1.png` (and `_2`). CONFIRM each chart is a correct, on-brand chart: bar (proportional navy/accent bars + labels), line (two series + legend), pie (3 wedges), scatter (points), area (filled line). If any chart is wrong/unstyled/missing, STOP and report which + the image. Do NOT proceed on "it compiled".

- [ ] **Step 4: Inspect HTML.** Confirm the HTML actually contains the chart SVG inline (the `<svg` count > 0, or the `.html` embeds the `_chart-*.svg`). If Quarto did NOT inline the external SVG (broken image in standalone HTML), report it — the fix is to inline the SVG as a base64 data URI in `charts.expand` (HTML branch) instead of `![](file)`. (This is the spec's flagged embed-resources risk.)

- [ ] **Step 5: No commit** (verification only). Proceed to Task 6 if green; if Step 4 found the embed issue, fix `charts.expand` HTML branch to emit a data-URI `<img>` and re-verify before continuing.

---

## Task 6: Asset contract + README + full regression

**Files:**
- Modify: `design/formats/assets/data-viz.yml`, `design/formats/README.md`

- [ ] **Step 1: Update `design/formats/assets/data-viz.yml`.** Replace its `authoring:` and `render_notes:` blocks (keep `asset`, `name`, `description`, `buckets`, `exports`, `style`):
```yaml
authoring:
  syntax: |
    ::: chart
    type: bar          # bar | line | pie | scatter | area
    title: Revenue
    x: [Q1, Q2, Q3, Q4]
    y: [12, 18, 15, 24]
    :::
  notes: Structured YAML fenced div; rendered to SVG by studio.charts (matplotlib).
render_notes:
  html: "Inline matplotlib SVG"
  pdf: "Same SVG placed via Typst #image()"
```

- [ ] **Step 2: Validate the asset library still passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS.

- [ ] **Step 3: Update `design/formats/README.md`.** Add a short "### Charts (data-viz)" subsection near the diagram section: the `::: chart` YAML shape (type + x/y or series), the 5 types, and that `studio.charts` renders ONE matplotlib SVG embedded inline in HTML and placed via Typst `#image()` in PDF — identical both sides. ≤20 added lines.

- [ ] **Step 4: Run the FULL suite**

Run: `design/.venv/bin/python tests/test_charts.py && design/.venv/bin/python tests/test_diagrams.py && design/.venv/bin/python tests/test_components.py && design/.venv/bin/python tests/test_formats.py && design/.venv/bin/python tests/test_storage_root.py && design/.venv/bin/python tests/test_docket.py`
Expected: all six PASS.

- [ ] **Step 5: Commit**

```bash
git add design/formats/
git commit -m "data-viz asset contract -> ::: chart authoring + README (#20)"
```

---

## Task 7: Open PR

- [ ] **Step 1: Push and open the PR**

```bash
git push -u origin feat/dataviz-engine
gh pr create --title "data-viz engine (#20): unified-SVG charts (bar/line/pie/scatter/area)" \
  --body "Implements docs/superpowers/specs/2026-06-02-dataviz-engine-design.md. Closes #20. One matplotlib SVG engine renders bar/line/pie/scatter/area, embedded inline in HTML and placed via Typst #image() in PDF — true parity. matplotlib added as a degrade-on-missing Python dep. Pixel-verified against the 360 brand. PPTX/gslide charts remain out (slice-4b-class)."
```

- [ ] **Step 2: Final confirmation**

Run: `design/.venv/bin/python tests/test_charts.py`
Expected: PASS.

---

## Self-Review (completed by plan author)

- **Spec coverage:** charts.py render_svg (5 types + multi-series) → T2/T3; matplotlib dep + degrade (lazy import) → T1 + charts.py lazy import; expand per export (HTML img / PDF #image) → T2; render wiring → T4; pixel verification incl. embed-resources HTML check (spec's flagged risk) → T5; asset contract + README → T6; fallback-on-bad-input → T2/T3. PPTX/gslide + interactive explicitly out (spec). ✔ no gaps.
- **Placeholder scan:** none — full code in every code step; verification specifies exact images + what to confirm; the embed-resources fallback (data-URI) is spelled out in T5 Step 4.
- **Type consistency:** `charts.render_svg(spec, tokens) -> str`, `charts.expand(markdown, export, tokens, out_dir) -> str`, `_series`, `_palette`, `_fallback`, `CHART_TYPES`, `CHART_CLASS` — names consistent across tasks. `sfmt`/`tok`/`tmp` match render.py locals. matplotlib lazy-imported inside `render_svg` (degrade path intact).
