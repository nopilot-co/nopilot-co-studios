# Slice 4a: Diagram Engine + Deck-Visual Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the decks bucket's diagrams (flow, timeline, process, hierarchy, organigram) and deck-visual components (kpi, cover-slide, section-slide) as designed, on-brand elements in HTML and PDF, from one structured-YAML authoring convention.

**Architecture:** A new `studio/diagrams.py` runs in `render.py`'s preprocess step (right after `metacontent.strip`). Because each session locks exactly ONE export, it expands `::: <diagram> ... yaml ... :::` divs to the engine for the known target — Mermaid fenced blocks for HTML, fletcher `{=typst}` raw blocks for PDF — brand-tokenized on both sides. Deck-visual *components* (prose-wrapped) extend the proven slice-2 Lua-bridge + token pattern. Verification bar is rendered pixels, not "it compiled".

**Tech Stack:** Python 3.12 (PyYAML), Quarto Mermaid (HTML, bundled), Typst `@preview/fletcher` (PDF, fetched+cached on first use). Standalone tests run with `design/.venv/bin/python` (no pytest).

---

## Background the implementer needs

- **Spike proven (do not re-spike):** fletcher renders branded linear flows AND trees (org charts) to PDF; Quarto renders Mermaid to inline SVG in HTML natively. Both pixel-verified.
- **The render preprocess seam** is `design/scripts/studio/render.py` ~line 99-100:
  ```python
  source_md = session_path / "inputs" / "source.md"
  (tmp / "source.md").write_text(metacontent.strip(source_md), encoding="utf-8")
  ```
  This is where the diagram expansion hooks in. The export name comes from `formats_mod.studio_format(resolved)` already computed earlier in `render()` as the variable `sfmt` (values: `"pdf"`, `"html"`, `"pptx"`, `"revealjs"`). The resolved token set is the variable `tok` (computed ~line 116; for the preprocess call, move the `tokens_mod.resolve(slug)` line up or pass slug).
- **Component pattern (slice 2)** lives in `design/templates/components/{components.lua,components.typ,components.css}`. A component class `foo` needs: an entry in the `COMPONENTS` table in `components.lua`, a `#let c_foo(body)` in `components.typ`, and a `.foo {}` rule in `components.css`. Hyphens in class names become underscores in the Typst function name (the Lua does `gsub("-", "_")`), so class `cover-slide` → `#let c_cover_slide`.
- **Authoring convention for diagrams:** a fenced div whose body is YAML, e.g.
  ```
  ::: flow
  nodes: [Brief, Plan, Render, Review]
  :::
  ```
  The diagram classes are: `flow`, `timeline`, `process`, `hierarchy`, `org`. These are NOT in the Lua COMPONENTS table (they're handled by the Python preprocessor, before Quarto), so the Lua filter must NOT also try to bridge them.

All work is on branch `feat/slice4a-diagrams` (already checked out; the approved spec is already committed there).

---

## File Structure

**New:**
- `design/scripts/studio/diagrams.py` — parse diagram divs, compute layout, emit Mermaid (HTML) or fletcher (PDF).
- `tests/test_diagrams.py` — standalone expansion tests.

**Modified:**
- `design/scripts/studio/render.py` — call `diagrams.expand()` in preprocess.
- `design/templates/components/components.lua` — add kpi / cover-slide / section-slide classes.
- `design/templates/components/components.typ` — add `c_kpi` / `c_cover_slide` / `c_section_slide`.
- `design/templates/components/components.css` — add `.kpi` / `.cover-slide` / `.section-slide`.
- `tests/test_components.py` — assert the 3 new component fns exist.
- `design/formats/assets/{flow-diagram,timeline,process,hierarchy-diagram,organigram}.yml` — update `authoring.syntax` + `render_notes` to the structured-YAML form.
- `design/formats/README.md` — document diagram authoring.

---

## Task 1: `diagrams.py` skeleton — find divs, parse YAML, dispatch by export

**Files:**
- Create: `design/scripts/studio/diagrams.py`
- Test: `tests/test_diagrams.py`

- [ ] **Step 1: Write the failing test** (creates `tests/test_diagrams.py`)

```python
#!/usr/bin/env python3
"""Slice 4a diagram engine — structured ::: <diagram> YAML expanded per export.
Standalone; run: design/.venv/bin/python tests/test_diagrams.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import diagrams  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


TOK = {
    "color": {"neutral": "#142F54", "surface": "#21456b", "tertiary": "#B14B33",
              "on_primary": "#FFFFFF", "secondary": "#6B7280", "primary": "#142F54"},
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# A doc with one flow diagram between ordinary paragraphs.
DOC = """Intro paragraph.

::: flow
nodes: [Brief, Plan, Render]
:::

Closing paragraph.
"""

# HTML target -> a mermaid fenced block; div + yaml gone; prose preserved.
html = diagrams.expand(DOC, "html", TOK)
check("html: mermaid block", "```mermaid" in html, html)
check("html: flowchart", "flowchart" in html, html)
check("html: node label", "Brief" in html and "Render" in html)
check("html: no raw div", "::: flow" not in html)
check("html: prose kept", "Intro paragraph." in html and "Closing paragraph." in html)

# PDF target -> a typst raw block importing fletcher.
pdf = diagrams.expand(DOC, "pdf", TOK)
check("pdf: typst raw block", "```{=typst}" in pdf, pdf)
check("pdf: fletcher import", "fletcher" in pdf, pdf)
check("pdf: node label", "Brief" in pdf and "Render" in pdf)
check("pdf: brand colour", "#142F54" in pdf or "142F54" in pdf, pdf)
check("pdf: no raw div", "::: flow" not in pdf)

# Non-diagram docs pass through untouched.
plain = "Just text.\n\n::: pullquote\nA quote.\n:::\n"
check("passthrough: pullquote untouched", diagrams.expand(plain, "html", TOK) == plain)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: diagrams (flow)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: FAIL — `No module named 'studio.diagrams'`.

- [ ] **Step 3: Create `design/scripts/studio/diagrams.py`**

```python
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
    raise NotImplementedError  # filled in Task 2+


def _fallback(name: str, body: str, err: str) -> str:
    return (
        f"::: panel\n**[diagram '{name}' could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )
```

- [ ] **Step 4: Run test to verify it fails differently**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: FAIL — now on the flow assertions (NotImplementedError caught → fallback panel), proving the div is found and dispatched. (The passthrough check should already pass.)

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/diagrams.py tests/test_diagrams.py
git commit -m "diagrams.py skeleton: find diagram divs, parse YAML, dispatch by export (slice 4a)"
```
(If a pre-commit hook reformats and aborts, re-`git add` and re-commit.)

---

## Task 2: `flow` + `process` (linear layouts)

**Files:**
- Modify: `design/scripts/studio/diagrams.py`
- Test: `tests/test_diagrams.py` (already covers flow; add process)

- [ ] **Step 1: Add the process assertions** to `tests/test_diagrams.py` before the final `if failures:`:

```python
# process: numbered steps, both targets.
PROC = "::: process\nsteps: [Discover, Design, Build, Ship]\n:::\n"
ph = diagrams.expand(PROC, "html", TOK)
check("process html mermaid", "```mermaid" in ph and "Discover" in ph)
pp = diagrams.expand(PROC, "pdf", TOK)
check("process pdf fletcher", "fletcher" in pp and "Ship" in pp)
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: FAIL on flow + process (NotImplementedError → fallback).

- [ ] **Step 3: Implement linear rendering.** Replace the `_render` stub and add helpers in `diagrams.py`:

```python
def _render(name: str, spec: dict, export: str, tokens: dict) -> str:
    if name in ("flow", "process"):
        labels = spec.get("nodes") or spec.get("steps") or []
        labels = [str(x) for x in labels]
        numbered = name == "process"
        return _linear_html(labels, numbered) if export == "html" \
            else _linear_pdf(labels, numbered, tokens)
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
    lines = [_fletcher_header(tokens),
             "#figure(diagram(spacing: 2.2em, node-stroke: 0.5pt, node-fill: _nf,"]
    parts = []
    for i, lab in enumerate(labels):
        text = f"{i + 1}. {lab}" if numbered else lab
        parts.append(
            f'node(({i},0), text(fill: _tx)[{_esc_typst(text)}], '
            f'corner-radius: 3pt, inset: 8pt)'
        )
        if i < len(labels) - 1:
            parts.append('edge("-|>", stroke: _ac + 1pt)')
    body = ",\n  ".join(parts)
    lines.append("  " + body + "\n))")
    return "```{=typst}\n" + "\n".join(lines) + "\n```\n"
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: PASS: diagrams (flow) — flow + process assertions green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/diagrams.py tests/test_diagrams.py
git commit -m "diagrams: flow + process linear layouts (mermaid + fletcher) (slice 4a)"
```

---

## Task 3: `timeline`

**Files:**
- Modify: `design/scripts/studio/diagrams.py`, `tests/test_diagrams.py`

- [ ] **Step 1: Add timeline assertions** before the final `if failures:`:

```python
# timeline: events with at/label.
TL = ("::: timeline\nevents:\n  - {at: Q1, label: Kickoff}\n"
      "  - {at: Q2, label: Beta}\n  - {at: Q3, label: GA}\n:::\n")
th = diagrams.expand(TL, "html", TOK)
check("timeline html", "```mermaid" in th and "Kickoff" in th and "Q3" in th)
tp = diagrams.expand(TL, "pdf", TOK)
check("timeline pdf", "fletcher" in tp and "Beta" in tp and "Q1" in tp)
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: FAIL on timeline (NotImplementedError → fallback panel).

- [ ] **Step 3: Implement timeline.** In `diagrams.py`, extend `_render` and add helpers:

In `_render`, before the final `raise`, add:

```python
    if name == "timeline":
        events = spec.get("events") or []
        pairs = [(str(e.get("at", "")), str(e.get("label", ""))) for e in events
                 if isinstance(e, dict)]
        return _timeline_html(pairs) if export == "html" else _timeline_pdf(pairs, tokens)
```

Add helpers:

```python
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
        # marker node on the axis with the period above and the label below
        nodes.append(
            f'node(({i},0), text(fill: _tx, size: 0.85em)[{_esc_typst(label)}], '
            f'corner-radius: 3pt, inset: 6pt)'
        )
        nodes.append(f'node(({i},-0.7), text(fill: _ac, weight: "bold")[{_esc_typst(at)}])')
        if i < len(pairs) - 1:
            nodes.append('edge((' + str(i) + ',0), (' + str(i + 1) + ',0), stroke: _ac + 1pt)')
    body = ",\n  ".join(nodes)
    return (
        "```{=typst}\n" + head
        + "#figure(diagram(spacing: 3em, node-stroke: 0.5pt, node-fill: _nf,\n  "
        + body + "\n))\n```\n"
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: PASS — timeline green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/diagrams.py tests/test_diagrams.py
git commit -m "diagrams: timeline (mermaid timeline + fletcher axis) (slice 4a)"
```

---

## Task 4: `hierarchy` + `org` (tree layout with computed coordinates)

**Files:**
- Modify: `design/scripts/studio/diagrams.py`, `tests/test_diagrams.py`

Tree spec shape (nestable):
```yaml
root: CEO
children:
  - root: CTO
    children: [Eng, Data]
  - COO
```
A child is either a string (leaf) or a `{root, children}` mapping.

- [ ] **Step 1: Add tree assertions** before the final `if failures:`:

```python
# hierarchy/org: nested tree, computed layout.
TREE = ("::: org\nroot: CEO\nchildren:\n  - root: CTO\n    children: [Eng, Data]\n"
        "  - COO\n:::\n")
oh = diagrams.expand(TREE, "html", TOK)
check("org html mermaid TD", "flowchart TD" in oh and "CEO" in oh and "Eng" in oh)
check("org html edges", oh.count("-->") >= 4, oh)  # CEO->CTO, CEO->COO, CTO->Eng, CTO->Data
op = diagrams.expand(TREE, "pdf", TOK)
check("org pdf fletcher", "fletcher" in op and "CEO" in op and "Data" in op)
check("org pdf edges", op.count("edge(") >= 4, op)
# layout helper assigns distinct coordinates to siblings
nodes, edges = diagrams._flatten_tree({"root": "A", "children": ["B", "C"]})
xs = {n["x"] for n in nodes if n["depth"] == 1}
check("layout: siblings distinct x", len(xs) == 2, str(nodes))
```

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: FAIL — `_flatten_tree` missing / org not implemented.

- [ ] **Step 3: Implement tree layout.** In `diagrams.py`, extend `_render` and add the layout + emitters:

In `_render`, before the final `raise`, add:

```python
    if name in ("hierarchy", "org"):
        nodes, edges = _flatten_tree(spec)
        return _tree_html(nodes, edges) if export == "html" \
            else _tree_pdf(nodes, edges, tokens)
```

Add:

```python
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
            return {"label": str(n.get("root", "")), "children": n.get("children", []) or []}
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
        # y grows downward with depth; x from layout. Negate x->grid not needed.
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
        "```{=typst}\n" + head
        + "#figure(diagram(spacing: (2em, 3em), node-stroke: 0.5pt, node-fill: _nf,\n  "
        + body + "\n))\n```\n"
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: PASS — hierarchy/org + layout assertions green.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/diagrams.py tests/test_diagrams.py
git commit -m "diagrams: hierarchy/org tree layout with computed coordinates (slice 4a)"
```

---

## Task 5: Wire `diagrams.expand` into `render.py`

**Files:**
- Modify: `design/scripts/studio/render.py`

- [ ] **Step 1: Read the current preprocess block.** Confirm lines ~99-100 and ~116:
```python
source_md = session_path / "inputs" / "source.md"
(tmp / "source.md").write_text(metacontent.strip(source_md), encoding="utf-8")
...
tok = tokens_mod.resolve(slug)
```

- [ ] **Step 2: Add the import.** Near the other `from . import` lines at the top of `render.py`, add:
```python
from . import diagrams as diagrams_mod
```

- [ ] **Step 3: Hook the expansion in.** Replace:
```python
    source_md = session_path / "inputs" / "source.md"
    (tmp / "source.md").write_text(metacontent.strip(source_md), encoding="utf-8")
```
with:
```python
    source_md = session_path / "inputs" / "source.md"
    # Preprocess order: strip meta-content (issue #11), then expand structured
    # `::: <diagram>` blocks for THIS export — Mermaid for HTML, fletcher for PDF
    # (slice 4a). `sfmt` is the locked studio format; `tok` the resolved tokens.
    tok = tokens_mod.resolve(slug)
    body = metacontent.strip(source_md)
    body = diagrams_mod.expand(body, sfmt, tok)
    (tmp / "source.md").write_text(body, encoding="utf-8")
```

- [ ] **Step 4: Remove the now-duplicate `tok =` line.** Further down (~line 116) there is a second `tok = tokens_mod.resolve(slug)`. Delete that second assignment line ONLY (the comment and the lines using `tok` stay), since `tok` is now defined above. Verify `tok` is still in scope for the component-CSS/preamble block.

- [ ] **Step 5: Verify render.py imports clean**

Run: `design/.venv/bin/python -c "import sys; sys.path.insert(0,'design/scripts'); import studio.render; print('render imports OK')"`
Expected: `render imports OK`

- [ ] **Step 6: Commit**

```bash
git add design/scripts/studio/render.py
git commit -m "render: expand structured diagrams in preprocess for the locked export (slice 4a)"
```

---

## Task 6: PIXEL VERIFICATION — render every diagram to PDF + HTML and look

**Files:** none (verification task; produces images for review)

- [ ] **Step 1: Write a verification script** at `/tmp/diag_verify.sh`:

```bash
#!/usr/bin/env bash
set -uo pipefail
cd /Users/ted/Projects/nopilot-co-studios
STUDIO=design/.venv/bin/studio
PY=design/.venv/bin/python
TMP=$(mktemp -d); echo "TMP=$TMP"
BRAND=$($PY -c "import sys;sys.path.insert(0,'design/scripts');from studio import brand;print(brand.brand_root('360'))")
STUDIOS_DOCKET_ROOT="$TMP" $STUDIO ingest --brand 360 --import-from "$BRAND" >/dev/null 2>&1
cat > "$TMP/d.md" <<'DOC'
# Diagram test

::: flow
nodes: [Brief, Plan, Render, Review]
:::

::: process
steps: [Discover, Design, Build, Ship]
:::

::: timeline
events:
  - {at: Q1, label: Kickoff}
  - {at: Q2, label: Beta}
  - {at: Q3, label: GA}
:::

::: org
root: CEO
children:
  - root: CTO
    children: [Eng, Data]
  - COO
:::
DOC
for fmt in proposal-pdf proposal-html; do
  NAME="diag-${fmt##*-}"
  SP="$TMP/360/outputs/$NAME"
  STUDIOS_DOCKET_ROOT="$TMP" $STUDIO session init --brand 360 --name "$NAME" --format "$fmt" --source "$TMP/d.md" >/dev/null 2>&1
  STUDIOS_DOCKET_ROOT="$TMP" $STUDIO render --session "$SP" --bump minor; echo "$fmt rc=$?"
done
PDF=$(ls "$TMP"/360/outputs/diag-pdf/outputs/*.pdf 2>/dev/null | head -1)
[ -n "$PDF" ] && $PY -c "import pypdfium2 as p; d=p.PdfDocument('$PDF'); print('pdf pages',len(d)); [d[i].render(scale=1.6).to_pil().save(f'/tmp/diag_pdf_{i+1}.png') for i in range(min(2,len(d)))]"
echo "DONE"
```

- [ ] **Step 2: Run it**

Run: `bash /tmp/diag_verify.sh`
Expected: both `rc=0`; `pdf pages N` printed; `/tmp/diag_pdf_1.png` (and `_2`) written. **Note:** the PDF render may pause a few seconds on first run while Typst fetches the fletcher package — that is expected and cached after.

- [ ] **Step 3: Inspect the pixels.** Read `/tmp/diag_pdf_1.png` (and `_2`). CONFIRM VISUALLY: flow + process show branded boxes with arrows; timeline shows the period/label axis; org shows a tree with parent→child edges. If any diagram is broken/unstyled, STOP and report which — do not proceed on "it compiled".

- [ ] **Step 4: Commit a note** (no code; record the verification in the branch history via an empty-tree-safe doc touch is unnecessary — instead just proceed). If everything renders, continue to Task 7. If something failed, report back with the specific diagram + image.

---

## Task 7: Deck-visual components — kpi, cover-slide, section-slide

**Files:**
- Modify: `design/templates/components/components.lua`, `components.typ`, `components.css`, `tests/test_components.py`

- [ ] **Step 1: Add assertions** to `tests/test_components.py`. Find the loop that checks `for fn in ( ... ):` and add the three new function names to that tuple: `"c_kpi", "c_cover_slide", "c_section_slide"`. Then find the CSS loop `for cls in ( ... ):` and add `".kpi", ".cover-slide", ".section-slide"`.

- [ ] **Step 2: Run to verify it fails**

Run: `design/.venv/bin/python tests/test_components.py`
Expected: FAIL — new fns/classes not found.

- [ ] **Step 3: Add the Lua classes.** In `components.lua`, the COMPONENTS table currently ends with `figure = true, embed = true,`. Add to it:
```lua
  kpi = true, ["cover-slide"] = true, ["section-slide"] = true,
```

- [ ] **Step 4: Add the Typst functions.** Append to `components.typ`:
```typst

// Deck-visual components (slice 4a). Proportioned for slides but valid inline.
#let c_kpi(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.lg, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.md,
)[
  #set text(fill: ds.color.tertiary, size: 2.2em, weight: "bold")
  #body
]

#let c_cover_slide(body) = block(
  width: 100%, fill: ds.color.neutral, inset: ds.space.lg, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.lg,
)[
  #set text(fill: ds.color.on_primary)
  #body
]

#let c_section_slide(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.lg, radius: ds.radius.md,
  above: ds.space.lg, below: ds.space.lg,
)[
  #set text(size: 1.6em, weight: "bold", fill: ds.color.primary)
  #body
]
```

- [ ] **Step 5: Add the CSS rules.** Append to `components.css`:
```css

/* Deck-visual components (slice 4a). */
.kpi {
  background: var(--ds-color-surface); border-radius: var(--ds-radius-lg);
  padding: 2rem; margin: 1.5rem 0;
  color: var(--ds-color-tertiary); font-size: 2.2rem; font-weight: 700;
}
.cover-slide {
  background: var(--ds-color-neutral); color: var(--ds-color-on-primary);
  border-radius: var(--ds-radius-lg); padding: 2.5rem; margin: 0 0 2rem;
}
.cover-slide h1, .cover-slide h2 { color: var(--ds-color-on-primary); }
.section-slide {
  background: var(--ds-color-surface); color: var(--ds-color-primary);
  border-radius: var(--ds-radius-md); padding: 2rem; margin: 2rem 0;
  font-size: 1.6rem; font-weight: 700;
}
@media print { .kpi, .cover-slide, .section-slide { break-inside: avoid; } }
```

- [ ] **Step 6: Run to verify it passes**

Run: `design/.venv/bin/python tests/test_components.py`
Expected: PASS — the three new component fns + classes found.

- [ ] **Step 7: Commit**

```bash
git add design/templates/components/ tests/test_components.py
git commit -m "components: deck-visual kpi / cover-slide / section-slide (slice 4a)"
```

---

## Task 8: PIXEL VERIFICATION — deck components render on-brand

**Files:** none (verification)

- [ ] **Step 1: Render a doc with the three components** (reuse the Task 6 script pattern; body below) to `presentation-pdf` AND `presentation-html`:

```
::: cover-slide
# Q3 Strategy
A one-line subtitle.
:::

::: kpi
**87%** faster delivery
:::

::: section-slide
Part One — Context
:::
```

Run via the same `studio ingest/session init/render` flow with `--format presentation-pdf` then `presentation-html`, rasterize page 1 of the PDF to `/tmp/deck_pdf_1.png`.

- [ ] **Step 2: Inspect `/tmp/deck_pdf_1.png`.** CONFIRM: cover-slide is a filled neutral banner with light text; kpi shows a large accent-coloured figure on a surface tile; section-slide is a bold surface divider. If unstyled, STOP and report.

- [ ] **Step 3: No commit** (verification only). Proceed to Task 9.

---

## Task 9: Update diagram asset contracts + README + run all suites

**Files:**
- Modify: `design/formats/assets/{flow-diagram,timeline,process,hierarchy-diagram,organigram}.yml`, `design/formats/README.md`, and re-run all tests.

- [ ] **Step 1: Update each diagram asset YAML's `authoring` + `render_notes`.** For each of the five files, set `authoring.syntax` to the structured form and `render_notes` to name the engines. Example for `design/formats/assets/flow-diagram.yml` — replace its `authoring:` and `render_notes:` blocks with:
```yaml
authoring:
  syntax: |
    ::: flow
    nodes: [Brief, Plan, Render, Review]
    :::
  notes: Structured YAML fenced div; expanded per export by studio.diagrams.
render_notes:
  html: "Mermaid flowchart LR (inline SVG)"
  pdf: "Typst fletcher diagram, brand-tokenized nodes/edges"
```
Apply the analogous structured `authoring.syntax` to the others:
- `process` → `steps: [Discover, Design, Build, Ship]`
- `timeline` → `events:` list of `{at, label}`
- `hierarchy-diagram` and `organigram` → `root:` + nested `children:` (use class `hierarchy` and `org` respectively in the `:::` line)
Set each `render_notes` to the matching Mermaid form (`flowchart`, `timeline`, `flowchart TD`) + "Typst fletcher".

- [ ] **Step 2: Validate the asset library still passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS (asset schema unchanged; only authoring text edited).

- [ ] **Step 3: Update `design/formats/README.md`.** Add a short "Diagrams" subsection under the existing asset-library section: the five diagram classes, the structured-YAML authoring shape, and that they expand per locked export (Mermaid→HTML, fletcher→PDF). ≤25 added lines.

- [ ] **Step 4: Run the full suite (no regressions)**

Run: `design/.venv/bin/python tests/test_diagrams.py && design/.venv/bin/python tests/test_components.py && design/.venv/bin/python tests/test_formats.py && design/.venv/bin/python tests/test_storage_root.py && design/.venv/bin/python tests/test_docket.py`
Expected: all five PASS.

- [ ] **Step 5: Commit**

```bash
git add design/formats/ design/formats/README.md
git commit -m "diagram asset contracts -> structured-YAML authoring + README (slice 4a)"
```

---

## Task 10: Open PR

- [ ] **Step 1: Push and open the PR**

```bash
git push -u origin feat/slice4a-diagrams
gh pr create --title "Slice 4a: structured-diagram engine + deck-visual components" \
  --body "Implements docs/superpowers/specs/2026-06-01-slice4a-diagram-engine-design.md. Closes #18. Diagrams (flow/timeline/process/hierarchy/org) expand per locked export — Mermaid for HTML, Typst fletcher for PDF — brand-tokenized; deck-visual components (kpi/cover-slide/section-slide) via the slice-2 pattern. Pixel-verified against the 360 brand. data-viz (#20) and editable PPTX (#19) remain separate."
```

- [ ] **Step 2: Final confirmation**

Run: `design/.venv/bin/python tests/test_diagrams.py`
Expected: PASS.

---

## Self-Review (completed by plan author)

- **Spec coverage:** diagrams.py per-export expansion → Tasks 1-5; flow/process → T2; timeline → T3; hierarchy/org tree layout → T4; render wiring → T5; kpi/cover-slide/section-slide → T7; asset-contract + README updates → T9; pixel verification (the spec's stated bar) → T6 + T8; fallback-on-bad-YAML → T1. data-viz + editable-PPTX explicitly out (separate issues). ✔ no gaps.
- **Placeholder scan:** none — every code step has complete code; verification tasks specify exact docs + what to confirm visually.
- **Type consistency:** `diagrams.expand(markdown, export, tokens)`, `_render`, `_flatten_tree`, `_fletcher_header`, `_esc_mermaid`/`_esc_typst`, `_linear_html/_linear_pdf`, `_timeline_html/_pdf`, `_tree_html/_pdf` — names consistent across tasks. Component fns `c_kpi`/`c_cover_slide`/`c_section_slide` match the hyphen→underscore Lua rule. `sfmt`/`tok` variable names match render.py's existing locals.
