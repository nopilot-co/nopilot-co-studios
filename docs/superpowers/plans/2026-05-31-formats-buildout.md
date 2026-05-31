# Formats Build-out (Slice 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build out `design/formats/` into a 3-bucket taxonomy with a normalized, tokenized asset-type library and per-bucket design language — the contract every downstream rendering slice targets — plus fix the filename version-compounding bug.

**Architecture:** Formats stay `<purpose>-<export>` resolved by deep-merge (`purposes/<p>.yml` ← `exports/<e>.yml` ← slug `overrides`). New: a normalized asset library at `design/formats/assets/<asset>.yml` (one file per asset type, token-referenced styling, Quarto fenced-div authoring), referenced by formats via an `assets:` list. Slice 1 is **contracts only** — no rendering. Correctness is enforced by an aggregate validation test, since the bulk files are data, not logic.

**Tech Stack:** Python 3.12 (Click CLI, PyYAML, jsonschema Draft 2020-12), standalone test scripts run with `design/.venv/bin/python` (no pytest, matching existing `tests/`).

---

## File Structure

**New files:**
- `design/scripts/studio/schemas/asset.schema.json` — validates an asset-library file.
- `design/scripts/studio/assets.py` — load/list/validate the asset library; format↔asset reference checks.
- `design/formats/assets/<asset>.yml` — 27 asset definitions (catalog in Task 5).
- `design/formats/exports/gslide.yml` — new export.
- `design/formats/purposes/{post,article,whitepaper,sow,presentation,report,status,approach}.yml` — 8 new purposes.
- `design/formats/<slug>.yml` — ~25 new slug files (matrix in Task 8).
- `tests/test_formats.py` — aggregate validation (standalone).

**Modified files:**
- `design/scripts/studio/schemas/format.schema.json` — add `assets`.
- `design/scripts/studio/formats.py` — surface `assets` on resolved; helper for referenced assets.
- `design/scripts/studio/cli.py` — `studio formats assets`; asset validation in `studio formats validate`.
- `design/scripts/studio/render.py` — strip a trailing `-v<semver>` from the output stem.
- `design/formats/purposes/{pitch,proposal}.yml` — enrich + add `assets`.
- `design/formats/exports/{html,pdf,pptx}.yml` — minor enrichment.
- `design/formats/{pitch-pptx,pitch-html,pitch-pdf,proposal-html,proposal-pdf}.yml` — add `assets` where needed.
- `design/formats/README.md` — document buckets + asset library + output-folder convention.

All work happens on branch `feat/formats-buildout` (already checked out).

---

## Task 1: Schemas — `asset.schema.json` + `assets` on `format.schema.json`

**Files:**
- Create: `design/scripts/studio/schemas/asset.schema.json`
- Modify: `design/scripts/studio/schemas/format.schema.json`
- Test: `tests/test_formats.py`

- [ ] **Step 1: Write the failing test** (creates `tests/test_formats.py`)

```python
#!/usr/bin/env python3
"""Formats build-out (slice 1) — schema load + (later) aggregate validation.
Standalone; run: design/.venv/bin/python tests/test_formats.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMAS = REPO / "design" / "scripts" / "studio" / "schemas"
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. Both schemas are valid JSON and declare the 2020-12 dialect.
for s in ("asset.schema.json", "format.schema.json"):
    data = json.loads((SCHEMAS / s).read_text())
    check(f"{s} is 2020-12", data.get("$schema", "").endswith("2020-12/schema"), s)

check("format schema has assets",
      "assets" in json.loads((SCHEMAS / "format.schema.json").read_text())["properties"])
asset_schema = json.loads((SCHEMAS / "asset.schema.json").read_text())
check("asset schema requires core fields",
      set(asset_schema.get("required", [])) >= {"asset", "name", "buckets", "exports"})

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: test_formats (schemas)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: FAIL — `asset.schema.json` does not exist (FileNotFoundError) or "format schema has assets" fails.

- [ ] **Step 3: Create `asset.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://studios/design/asset.schema.json",
  "title": "Design-studio asset-library entry",
  "type": "object",
  "required": ["asset", "name", "description", "buckets", "exports", "authoring"],
  "additionalProperties": true,
  "properties": {
    "asset": { "type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "buckets": {
      "type": "array", "minItems": 1,
      "items": { "enum": ["editorial", "documents", "decks"] }
    },
    "exports": {
      "type": "array", "minItems": 1,
      "items": { "enum": ["html", "pdf", "pptx", "gslide"] }
    },
    "style": { "type": "object" },
    "authoring": {
      "type": "object",
      "required": ["syntax"],
      "properties": {
        "syntax": { "type": "string" },
        "notes": { "type": "string" }
      }
    },
    "render_notes": { "type": "object" }
  }
}
```

- [ ] **Step 4: Add `assets` to `format.schema.json`**

In `design/scripts/studio/schemas/format.schema.json`, inside `"properties"`, add (after the `"description"` property):

```json
    "assets": {
      "description": "Asset-library slugs this format may use (design/formats/assets/<slug>.yml).",
      "type": "array",
      "items": { "type": "string" }
    },
```

- [ ] **Step 5: Run test to verify it passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS: test_formats (schemas)

- [ ] **Step 6: Commit**

```bash
git add design/scripts/studio/schemas/asset.schema.json design/scripts/studio/schemas/format.schema.json tests/test_formats.py
git commit -m "Add asset.schema.json + assets field on format schema (slice 1)"
```

---

## Task 2: `assets.py` — load / list / validate the asset library

**Files:**
- Create: `design/scripts/studio/assets.py`
- Test: `tests/test_formats.py` (extend)

- [ ] **Step 1: Write the failing test** (append before the final `if failures:` block in `tests/test_formats.py`)

```python
# 2. assets.py API (operates on a temp fixture library).
import importlib
import tempfile

sys.path.insert(0, str(REPO / "design" / "scripts"))
assets = importlib.import_module("studio.assets")

with tempfile.TemporaryDirectory() as td:
    adir = Path(td) / "assets"
    adir.mkdir()
    (adir / "pullquote.yml").write_text(
        "asset: pullquote\nname: Pull quote\ndescription: x\n"
        "buckets: [editorial, documents]\nexports: [html, pdf]\n"
        "authoring: {syntax: '::: pullquote'}\n"
    )
    (adir / "bad.yml").write_text("asset: bad\nname: Bad\n")  # missing required
    check("list_assets", assets.list_assets(adir) == ["bad", "pullquote"])
    check("load_asset", assets.load_asset(adir, "pullquote")["name"] == "Pull quote")
    check("validate good asset", assets.validate_asset(adir, "pullquote") == [])
    check("validate bad asset", len(assets.validate_asset(adir, "bad")) > 0)
    # export compatibility: pullquote supports html+pdf, not pptx
    check("asset supports export", assets.supports_export(assets.load_asset(adir, "pullquote"), "html"))
    check("asset rejects export", not assets.supports_export(assets.load_asset(adir, "pullquote"), "pptx"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.assets'`.

- [ ] **Step 3: Create `design/scripts/studio/assets.py`**

```python
"""Asset library: design/formats/assets/<slug>.yml — a normalized, tokenized
catalog of asset types (pullquote, cover, data-table, …) referenced by formats.

Slice 1 owns the contracts + validation only; rendering is later slices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, SCHEMAS

ASSETS_DIR = FORMATS / "assets"


def assets_dir(base: Path | None = None) -> Path:
    return base if base is not None else ASSETS_DIR


def list_assets(base: Path | None = None) -> list[str]:
    d = assets_dir(base)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yml"))


def load_asset(base: Path | None, slug: str) -> dict[str, Any]:
    path = assets_dir(base) / f"{slug}.yml"
    if not path.exists():
        raise FileNotFoundError(f"no asset '{slug}' at {path}")
    return yaml.safe_load(path.read_text()) or {}


def _schema() -> dict[str, Any]:
    return json.loads((SCHEMAS / "asset.schema.json").read_text())


def validate_asset(base: Path | None, slug: str) -> list[str]:
    try:
        data = load_asset(base, slug)
    except FileNotFoundError as e:
        return [str(e)]
    validator = Draft202012Validator(_schema())
    return [
        ("/".join(str(p) for p in e.path) + ": " + e.message) if e.path else e.message
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def supports_export(asset: dict[str, Any], export: str) -> bool:
    return export in (asset.get("exports") or [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS: test_formats (schemas) — and no new failures.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/assets.py tests/test_formats.py
git commit -m "Add assets.py: load/list/validate the asset library (slice 1)"
```

---

## Task 3: `render.py` — strip trailing `-v<semver>` from the output stem

**Files:**
- Modify: `design/scripts/studio/render.py`
- Test: `tests/test_formats.py` (extend)

- [ ] **Step 1: Write the failing test** (append before the final `if failures:` block)

```python
# 3. render output-stem de-versioning (fixes …-v1.0.0.v1.1.0 compounding).
render_mod = importlib.import_module("studio.render")
check("strip versioned stem",
      render_mod._strip_version_label("client-proposition-pitch-pdf-v1.0.0") == "client-proposition-pitch-pdf")
check("leave unversioned stem",
      render_mod._strip_version_label("client-proposition") == "client-proposition")
check("only trailing label stripped",
      render_mod._strip_version_label("v1.2.3-notes") == "v1.2.3-notes")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: FAIL — `module 'studio.render' has no attribute '_strip_version_label'`.

- [ ] **Step 3: Add the helper and use it in `render.py`**

Add this function near the top of `design/scripts/studio/render.py` (after the `_EXT` dict, before `def render`):

```python
import re

_VER_LABEL_RE = re.compile(r"-v\d+\.\d+\.\d+$")


def _strip_version_label(stem: str) -> str:
    """Remove a trailing -v<semver> label so the render version isn't compounded
    onto a content filename that already carries one (e.g. foo-v1.0.0 -> foo)."""
    return _VER_LABEL_RE.sub("", stem)
```

Then change the `out_stem` line inside `render()` from:

```python
    out_stem = state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
```

to:

```python
    out_stem = _strip_version_label(
        state.get("source_filename", "source.md").rsplit(".", 1)[0] or "source"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS — all three de-versioning checks pass.

- [ ] **Step 5: Commit**

```bash
git add design/scripts/studio/render.py tests/test_formats.py
git commit -m "Fix output-filename version compounding: strip trailing -v<semver> from stem (slice 1)"
```

---

## Task 4: Exports — new `gslide.yml`, enrich `html/pdf/pptx`

**Files:**
- Create: `design/formats/exports/gslide.yml`
- Modify: `design/formats/exports/{html,pdf,pptx}.yml`

No code logic — validated by the aggregate test in Task 9.

- [ ] **Step 1: Create `design/formats/exports/gslide.yml`** (mirrors `glide`'s not-renderable signalling)

```yaml
# Export: gslide — Google Slides deck (editable native blocks).
# Canonical contract exists; the studio produces this in slice 4 via PPTX import.
export: gslide
name: Google Slides
asset_type: deck
render:
  engine: gslide
  studio_format: null      # not renderable yet; `studio render` will refuse
  status: planned
requires:
  render: [quarto]
style_guide:
  layout: 16:9 slides; one idea per slide; editable native shapes
  notes: parity with pptx/html/pdf; blocks must remain natively editable in Google Slides
ruleset:
  supported: false         # renderer guard
  max_slides: 20
  max_words_per_view: 40
```

- [ ] **Step 2: Enrich `exports/html.yml`** — append a `print` note under `style_guide` (documents bucket prints from HTML). Replace its `style_guide` block with:

```yaml
style_guide:
  layout: single responsive scroll; no pagination
  notes: progressive disclosure; links and anchors are first-class
  print: clean print-from-HTML expected for documents (proposal/whitepaper/sow)
```

- [ ] **Step 3: Enrich `exports/pdf.yml`** — add portrait + page-break notes. Replace its `style_guide` block with:

```yaml
style_guide:
  layout: paginated A4/Letter portrait with fixed page geometry
  notes: mind page breaks; keep sections/panels together; design for print and screen
  page_discipline: avoid orphaned headings and split panels; group asset + caption
```

- [ ] **Step 4: Enrich `exports/pptx.yml`** — add editable-block intent. Append under `style_guide.notes` (or add `notes`):

```yaml
style_guide:
  layout: 16:9 slides; one idea per slide
  notes: blocks render as native editable shapes/text (slice 4); parity with gslide/html/pdf
```

(Preserve any existing keys in `pptx.yml`; only add/replace the `style_guide` block.)

- [ ] **Step 5: Verify exports resolve** (sanity, full validation in Task 9)

Run: `design/.venv/bin/studio formats list`
Expected: no traceback; existing slugs still list. (gslide slugs appear after Task 8.)

- [ ] **Step 6: Commit**

```bash
git add design/formats/exports/
git commit -m "Add gslide export; enrich html/pdf/pptx export contracts (slice 1)"
```

---

## Task 5: Asset library — author all 27 `assets/<asset>.yml`

**Files:**
- Create: `design/formats/assets/<asset>.yml` (×27)

Every file follows this **template** (token references resolve against `design.md` token shape; they are inert strings until slice 2):

```yaml
asset: <slug>
name: <Name>
description: <one line>
buckets: [<editorial|documents|decks>, ...]
exports: [<html|pdf|pptx|gslide>, ...]
style:
  <token-referenced visual hints, e.g. typography: "{typography.h3}">
authoring:
  syntax: |
    ::: <slug>
    ...author content...
    :::
  notes: Quarto fenced div with class `<slug>`.
render_notes:
  html: <how it renders in HTML>
  pdf: <Typst equivalent>
  pptx: <PPTX/gslide equivalent, if applicable>
```

- [ ] **Step 1: Author the catalog.** Create one file per row. `buckets`/`exports`/`class` are authoritative; write a one-line `description`, a sensible `style` (2–4 token-referenced hints), an `authoring.syntax` using the fenced-div class, and `render_notes` per listed export.

| asset (file) | name | buckets | exports | fenced class | style hints (tokens) |
|---|---|---|---|---|---|
| `precis` | Précis | editorial, documents, decks | html, pdf, pptx, gslide | `precis` | `typography: "{typography.lead}"`, `color: "{colors.secondary}"` |
| `pullquote` | Pull quote | editorial, documents, decks | html, pdf, pptx, gslide | `pullquote` | `typography: "{typography.h3}"`, `rule: "left 3px {colors.tertiary}"` |
| `stat-panel` | Stat panel | editorial, documents, decks | html, pdf, pptx, gslide | `stat-panel` | `figure: "{typography.display}"`, `accent: "{colors.tertiary}"` |
| `author-attribution` | Byline | editorial, documents | html, pdf | `byline` | `typography: "{typography.label}"`, `color: "{colors.secondary}"` |
| `cover` | Document cover | documents | html, pdf | `cover` | `bg: "{colors.neutral}"`, `title: "{typography.display}"` |
| `section-interstitial` | Section interstitial | documents | html, pdf | `section` | `bg: "{colors.surface}"`, `title: "{typography.h1}"` |
| `contents` | Contents / index | documents | html, pdf | `contents` | `typography: "{typography.body}"`, `leader: "{colors.secondary}"` |
| `highlight-panel` | Highlight panel | documents, decks | html, pdf, pptx, gslide | `highlight` | `bg: "{colors.surface}"`, `rounded: "{rounded.lg}"`, `pad: "{spacing.lg}"` |
| `callout-panel` | Callout | documents | html, pdf | `callout` | `bg: "{colors.surface}"`, `accent: "{colors.tertiary}"` |
| `general-panel` | Panel | documents, decks | html, pdf, pptx, gslide | `panel` | `border: "1px {colors.secondary}"`, `rounded: "{rounded.md}"` |
| `data-table` | Data table | documents, decks | html, pdf, pptx, gslide | `data-table` | `header-bg: "{colors.surface}"`, `rule: "{colors.secondary}"` |
| `figure-caption` | Figure + caption | documents | html, pdf | `figure` | `caption: "{typography.label}"`, `color: "{colors.secondary}"` |
| `source-reference` | Source reference | documents | html, pdf | `reference` | `typography: "{typography.label}"` |
| `anchor-link` | Anchor link | documents | html, pdf | `anchor` | `color: "{colors.tertiary}"` |
| `cta` | Call to action | documents | html, pdf | `cta` | `primary-bg: "{colors.tertiary}"`, `on: "{colors.on-primary}"` |
| `author-bio` | Author bio | documents | html, pdf | `bio` | `bg: "{colors.surface}"`, `name: "{typography.h3}"` |
| `header-footer` | Running header/footer | documents | html, pdf | `running` | `typography: "{typography.label}"`, `color: "{colors.secondary}"` |
| `cover-slide` | Deck cover | decks | pptx, gslide, html, pdf | `cover-slide` | `bg: "{colors.neutral}"`, `title: "{typography.display}"` |
| `section-slide` | Section slide | decks | pptx, gslide, html, pdf | `section-slide` | `bg: "{colors.surface}"`, `title: "{typography.h1}"` |
| `kpi-tile` | KPI tile | decks | pptx, gslide, html, pdf | `kpi` | `figure: "{typography.display}"`, `accent: "{colors.tertiary}"` |
| `flow-diagram` | Flow diagram | decks | pptx, gslide, html, pdf | `flow` | `node: "{colors.surface}"`, `arrow: "{colors.secondary}"` |
| `timeline` | Timeline | decks | pptx, gslide, html, pdf | `timeline` | `axis: "{colors.secondary}"`, `marker: "{colors.tertiary}"` |
| `process` | Process | decks | pptx, gslide, html, pdf | `process` | `step: "{colors.surface}"`, `index: "{colors.tertiary}"` |
| `hierarchy-diagram` | Hierarchy | decks | pptx, gslide, html, pdf | `hierarchy` | `node: "{colors.surface}"`, `line: "{colors.secondary}"` |
| `organigram` | Organigram | decks | pptx, gslide, html, pdf | `org` | `node: "{colors.surface}"`, `line: "{colors.secondary}"` |
| `data-viz` | Data visualisation | decks | pptx, gslide, html, pdf | `chart` | `series: "{colors.tertiary}"`, `grid: "{colors.secondary}"` |
| `asset-embed` | Asset embed | decks | pptx, gslide, html, pdf | `embed` | `caption: "{typography.label}"` |

**Worked example — `design/formats/assets/pullquote.yml`** (copy this shape for the rest):

```yaml
asset: pullquote
name: Pull quote
description: A short extract lifted from the body for rhythm and a visual anchor.
buckets: [editorial, documents, decks]
exports: [html, pdf, pptx, gslide]
style:
  typography: "{typography.h3}"
  accent: "{colors.tertiary}"
  rule: "left-border 3px {colors.tertiary}"
  spacing: "{spacing.lg}"
authoring:
  syntax: |
    ::: pullquote
    The line worth lifting.
    — Attribution
    :::
  notes: Quarto fenced div with class `pullquote`.
render_notes:
  html: "<blockquote class='pullquote'> with left accent rule"
  pdf: "Typst block: left rule {colors.tertiary}, h3 type, generous margin"
  pptx: "styled text box, accent rule on left edge"
```

**Worked example — `design/formats/assets/data-table.yml`:**

```yaml
asset: data-table
name: Data table
description: A styled table with a header band and rules for scannable data.
buckets: [documents, decks]
exports: [html, pdf, pptx, gslide]
style:
  header-bg: "{colors.surface}"
  rule: "{colors.secondary}"
  typography: "{typography.body}"
authoring:
  syntax: |
    Standard Markdown table; the renderer applies the data-table style.
  notes: No fenced div needed; pipe tables are styled automatically.
render_notes:
  html: "<table class='data-table'> header band + zebra rows"
  pdf: "Typst table: header fill {colors.surface}, hairline rules"
  pptx: "native table with branded header row"
```

- [ ] **Step 2: Verify all asset files validate**

Run: `design/.venv/bin/python -c "import sys; sys.path.insert(0,'design/scripts'); from studio import assets; errs={s:assets.validate_asset(None,s) for s in assets.list_assets()}; bad={k:v for k,v in errs.items() if v}; print('invalid:', bad or 'none'); print('count:', len(assets.list_assets()))"`
Expected: `invalid: none` and `count: 27`.

- [ ] **Step 3: Commit**

```bash
git add design/formats/assets/
git commit -m "Author the asset library: 27 tokenized asset-type contracts (slice 1)"
```

---

## Task 6: Purposes — author 8 new + enrich 2 existing

**Files:**
- Create: `design/formats/purposes/{post,article,whitepaper,sow,presentation,report,status,approach}.yml`
- Modify: `design/formats/purposes/{pitch,proposal}.yml`

Each purpose MUST satisfy `format.schema.json`'s required `execution_brief` (`objective` + `required_sections`) and provide `style_guide`, `ruleset`, and an `assets:` list. Below: the full content for one purpose per bucket (worked examples), then field-level specs for the rest.

- [ ] **Step 1: Bucket A — `purposes/post.yml`** (worked example)

```yaml
# Purpose: post — a single social/LinkedIn post. Plainest bucket; CSS inherited.
purpose: post
name: Post
description: A short, punchy social post that earns a stop-scroll and one idea.
assets: [precis, pullquote, stat-panel, author-attribution]
style_guide:
  voice: first-person, direct, momentum; one clear idea
  pov:
    paragraph_length: 1–3 short sentences; frequent line breaks for rhythm
    bullets: sparingly; only to list, never to think
    punctuation: em-dashes and full stops; avoid semicolons; no exclamation spam
    newline_usage: single blank line between beats; whitespace is pacing
    target_length: 80–220 words
    tone: confident, plain, a little opinionated
    rhetoric: licensed — anaphora, rule-of-three, a single rhetorical question
  do: [Open with the hook, One idea, End on a line that lands]
  dont: [Wall of text, Hashtag stuffing, Hedging]
execution_brief:
  objective: Earn a stop-scroll and land one idea.
  audience: A professional feed (peers, prospects)
  required_sections: [hook, body, takeaway]
ruleset:
  required_sections: [hook, takeaway]
  max_words_per_view: 220
  tone: [direct, plain]
```

- [ ] **Step 2: Bucket B — `purposes/whitepaper.yml`** (worked example)

```yaml
# Purpose: whitepaper — an authoritative, evidenced point of view.
purpose: whitepaper
name: Whitepaper
description: A credible, evidenced argument that establishes authority on a topic.
assets: [cover, section-interstitial, contents, highlight-panel, callout-panel,
         general-panel, data-table, figure-caption, source-reference, anchor-link,
         cta, author-bio, header-footer, pullquote, stat-panel, precis, data-viz]
style_guide:
  voice: authoritative, evidenced, measured
  hierarchy:
    h1: section titles; one per major theme
    h2: sub-arguments
    h3: supporting points
    h4: rare; inline emphasis only
    body: "{typography.body}"; generous leading
    lists: parallel structure; lead with the noun
  page_discipline: keep headings with their first paragraph; never split a panel or
    a figure from its caption; group references at section ends
  print: must print cleanly from HTML (documents bucket)
  do: [Cite sources, Quantify claims, Lead with the thesis]
  dont: [Marketing fluff, Unsupported superlatives]
execution_brief:
  objective: Establish authority and move the reader to a considered next step.
  audience: Evaluators and informed practitioners
  required_sections: [summary, context, argument, evidence, implications, references]
ruleset:
  required_sections: [summary, argument, evidence, references]
  max_pages: 20
  tone: [authoritative, evidenced]
```

- [ ] **Step 3: Bucket C — `purposes/presentation.yml`** (worked example)

```yaml
# Purpose: presentation — inform/persuade a room; visually consumed, low word-count.
purpose: presentation
name: Presentation
description: A visual deck that conveys key points fast to a live or async audience.
assets: [cover-slide, section-slide, kpi-tile, flow-diagram, timeline, process,
         hierarchy-diagram, organigram, data-viz, asset-embed, pullquote,
         stat-panel, callout-panel, data-table, highlight-panel]
style_guide:
  visual: one idea per slide; image/diagram over paragraphs; generous whitespace
  word_count: very low — headline + ≤3 supporting lines per slide
  consistency: identical structure across pptx, gslide, html, pdf
  typography: "{typography.h1}" headlines; "{typography.label}" eyebrows
  do: [One idea per view, Show don't tell, A single focal point]
  dont: [Paragraphs on a slide, More than one CTA per view]
execution_brief:
  objective: Convey the key points fast and memorably.
  audience: A room or an async viewer
  narrative_arc: cover -> context -> insight -> implication -> ask
  required_sections: [cover, agenda, body, summary]
ruleset:
  required_sections: [cover, summary]
  max_slides: 20
  max_words_per_view: 40
  tone: [crisp, visual]
```

- [ ] **Step 4: Author the remaining purposes** using the matching bucket template above. Field specs (fill `style_guide`/`execution_brief`/`ruleset` in the bucket's shape; set `assets` as given):

| purpose | bucket | assets | objective | required_sections (ruleset) | key ruleset |
|---|---|---|---|---|---|
| `article` | A | precis, pullquote, stat-panel, author-attribution, figure-caption, source-reference | Inform and persuade with a considered argument | [hook, body, conclusion] | `max_words_per_view: 1400`, tone [considered, clear] |
| `sow` | B | cover, section-interstitial, contents, data-table, general-panel, callout-panel, figure-caption, source-reference, anchor-link, header-footer, cta, precis | Define scope and terms precisely enough to sign | [summary, scope, deliverables, pricing, terms] | `max_pages: 20`, must group scope/pricing tables, tone [precise, contractual] |
| `report` | C | cover-slide, section-slide, kpi-tile, data-viz, data-table, timeline, process, callout-panel, stat-panel, pullquote, highlight-panel | Present findings clearly and defensibly | [cover, findings, recommendation] | `max_slides: 24`, `max_words_per_view: 50`, tone [clear, evidenced] |
| `status` | C | cover-slide, kpi-tile, data-table, timeline, callout-panel, stat-panel, highlight-panel | Show where things stand at a glance | [cover, status, risks, next] | `max_slides: 12`, `max_words_per_view: 40`, tone [factual, brief] |
| `approach` | C | cover-slide, section-slide, flow-diagram, process, timeline, hierarchy-diagram, callout-panel, stat-panel, highlight-panel, data-table | Explain how the work will be done | [cover, approach, plan, outcomes] | `max_slides: 18`, `max_words_per_view: 45`, tone [confident, methodical] |

- [ ] **Step 5: Enrich `purposes/pitch.yml`** — add `assets:` (keep existing content):

```yaml
assets: [cover-slide, section-slide, kpi-tile, flow-diagram, timeline, process,
         hierarchy-diagram, organigram, data-viz, asset-embed, pullquote,
         stat-panel, callout-panel, data-table, highlight-panel]
```

(Insert this `assets:` block near the top of `pitch.yml`, after `description:`.)

- [ ] **Step 6: Enrich `purposes/proposal.yml`** — add `assets:`:

```yaml
assets: [cover, section-interstitial, contents, highlight-panel, callout-panel,
         general-panel, data-table, figure-caption, source-reference, anchor-link,
         cta, author-bio, header-footer, pullquote, stat-panel, precis]
```

- [ ] **Step 7: Verify purposes parse**

Run: `design/.venv/bin/python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('design/formats/purposes/*.yml')]; print('all purposes parse')"`
Expected: `all purposes parse`

- [ ] **Step 8: Commit**

```bash
git add design/formats/purposes/
git commit -m "Author 8 new purposes + enrich pitch/proposal with asset lists (slice 1)"
```

---

## Task 7: Slug files — author the full matrix

**Files:**
- Create: `design/formats/<slug>.yml` for every combination below not already present.
- Modify: `design/formats/{proposal-html,proposal-pdf,pitch-pptx,pitch-html,pitch-pdf}.yml` only if they need an `assets` override (default: inherit from purpose — leave them).

Slug-file **template** (thin; `assets` inherited from the purpose unless overridden):

```yaml
# Format: <slug> = purposes/<purpose>.yml <- exports/<export>.yml <- overrides
extends: <purpose>
export: <export>
overrides: {}
```

- [ ] **Step 1: Create the new slug files.** One per cell (skip those that already exist):

| Bucket | New slug files |
|---|---|
| A | `post-html`, `article-html` |
| B | `whitepaper-html`, `whitepaper-pdf`, `sow-html`, `sow-pdf` |
| C | `pitch-gslide`; `presentation-pptx`, `presentation-gslide`, `presentation-html`, `presentation-pdf`; `report-pptx`, `report-gslide`, `report-html`, `report-pdf`; `status-pptx`, `status-gslide`, `status-html`, `status-pdf`; `approach-pptx`, `approach-gslide`, `approach-html`, `approach-pdf` |

Example — `design/formats/whitepaper-pdf.yml`:

```yaml
# Format: whitepaper-pdf = purposes/whitepaper.yml <- exports/pdf.yml <- overrides
extends: whitepaper
export: pdf
overrides: {}
```

Example — `design/formats/post-html.yml`:

```yaml
# Format: post-html = purposes/post.yml <- exports/html.yml <- overrides
extends: post
export: html
overrides:
  ruleset:
    max_scroll_screens: 3
```

- [ ] **Step 2: Verify every slug resolves**

Run: `design/.venv/bin/studio formats list`
Expected: all new slugs appear; gslide rows show `(not renderable yet)`; no tracebacks.

- [ ] **Step 3: Commit**

```bash
git add design/formats/*.yml
git commit -m "Author the full format slug matrix across all three buckets (slice 1)"
```

---

## Task 8: CLI — `studio formats assets` + asset validation in `studio formats validate`

**Files:**
- Modify: `design/scripts/studio/cli.py`, `design/scripts/studio/formats.py`
- Test: `tests/test_formats.py` (extend)

- [ ] **Step 1: Write the failing test** (append before final `if failures:`)

```python
# 4. formats.py surfaces assets + reference validation.
formats_mod = importlib.import_module("studio.formats")
resolved = formats_mod.resolve("post-html")
check("resolved has assets list", isinstance(resolved.get("assets"), list) and resolved["assets"])
# every referenced asset exists and supports the format's export
ref_errs = formats_mod.validate_asset_refs(resolved)
check("post-html asset refs valid", ref_errs == [], str(ref_errs))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: FAIL — `module 'studio.formats' has no attribute 'validate_asset_refs'`.

- [ ] **Step 3: Add `validate_asset_refs` to `formats.py`** (after `validate`)

```python
def validate_asset_refs(resolved: dict[str, Any]) -> list[str]:
    """Each asset a format references must exist and support the format's export."""
    from . import assets as assets_mod

    export = resolved.get("export")
    known = set(assets_mod.list_assets())
    errors: list[str] = []
    for slug in resolved.get("assets", []) or []:
        if slug not in known:
            errors.append(f"unknown asset '{slug}'")
            continue
        asset = assets_mod.load_asset(None, slug)
        if export and not assets_mod.supports_export(asset, export):
            errors.append(f"asset '{slug}' does not support export '{export}'")
    return errors
```

- [ ] **Step 4: Add CLI commands in `cli.py`** (inside the `formats` group, after `formats_validate`)

```python
@formats.command("assets")
def formats_assets() -> None:
    """List the asset library (design/formats/assets/)."""
    from . import assets as assets_mod

    for slug in assets_mod.list_assets():
        a = assets_mod.load_asset(None, slug)
        buckets = ",".join(a.get("buckets", []))
        exports = ",".join(a.get("exports", []))
        click.echo(f"{slug:<22} {buckets:<28} {exports}")
```

And extend `formats_validate` to also check asset refs — replace its body with:

```python
def formats_validate(slug: str) -> None:
    errors = formats_mod.validate(slug)
    try:
        errors = errors + formats_mod.validate_asset_refs(formats_mod.resolve(slug))
    except (FileNotFoundError, ValueError):
        pass
    if errors:
        for e in errors:
            click.echo(f"  ✗ {e}", err=True)
        sys.exit(1)
    click.echo(f"✓ {slug} is valid")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS — asset-ref checks pass.

- [ ] **Step 6: Manual CLI smoke**

Run: `design/.venv/bin/studio formats assets | head` then `design/.venv/bin/studio formats validate --format whitepaper-pdf`
Expected: asset list prints; `✓ whitepaper-pdf is valid`.

- [ ] **Step 7: Commit**

```bash
git add design/scripts/studio/cli.py design/scripts/studio/formats.py tests/test_formats.py
git commit -m "CLI: studio formats assets + asset-ref validation in formats validate (slice 1)"
```

---

## Task 9: Aggregate validation + README

**Files:**
- Modify: `tests/test_formats.py` (final aggregate block), `design/formats/README.md`

- [ ] **Step 1: Add the aggregate test** (append before final `if failures:`)

```python
# 5. AGGREGATE: every slug resolves, validates, and its asset refs hold.
for slug in formats_mod.list_formats():
    try:
        r = formats_mod.resolve(slug)
    except Exception as e:  # noqa: BLE001
        check(f"resolve {slug}", False, str(e)); continue
    check(f"schema {slug}", formats_mod.validate(slug) == [], str(formats_mod.validate(slug)))
    check(f"asset-refs {slug}", formats_mod.validate_asset_refs(r) == [],
          str(formats_mod.validate_asset_refs(r)))
# every asset validates
for a in assets.list_assets():
    check(f"asset {a}", assets.validate_asset(None, a) == [], str(assets.validate_asset(None, a)))
```

- [ ] **Step 2: Run the full test**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: `PASS: test_formats (schemas)` with zero failures across all slugs and assets.

- [ ] **Step 3: Run the existing suites (no regressions)**

Run: `design/.venv/bin/python tests/test_storage_root.py && design/.venv/bin/python tests/test_docket.py`
Expected: both PASS.

- [ ] **Step 4: Update `design/formats/README.md`** — add a "Buckets", "Asset library", and "Output-folder convention" section. Document: the three buckets + their exports; that assets live in `assets/<slug>.yml`, are token-referenced, authored as `::: <class>` fenced divs, and referenced via a format's `assets:` list; and the convention that docket render outputs flatten to `outputs/<primary>/<file>` (no redundant `<format>/` dir — format is in the filename). Keep it concise (≤40 added lines).

- [ ] **Step 5: Commit**

```bash
git add tests/test_formats.py design/formats/README.md
git commit -m "Aggregate format/asset validation test + README (buckets, asset library, output convention) (slice 1)"
```

---

## Task 10: Open PR

- [ ] **Step 1: Push and open the PR**

```bash
git push -u origin feat/formats-buildout
gh pr create --title "Formats build-out (slice 1): buckets, asset library, version-fix" \
  --body "Implements docs/superpowers/specs/2026-05-31-formats-buildout-design.md (slice 1 of the format/design program). Contracts only — 3-bucket taxonomy, 27-asset tokenized library, full slug matrix incl. gslide (planned), filename version-compounding fix. Rendering is slices 2-4."
```

- [ ] **Step 2: Confirm CI/validation locally one more time**

Run: `design/.venv/bin/python tests/test_formats.py`
Expected: PASS.

---

## Self-Review (completed by plan author)

- **Spec coverage:** §A matrix → Tasks 4,6,7. §B purposes → Task 6. §C exports → Task 4. §D asset library → Tasks 1,2,5. §E slug files → Task 7. §F schema/formats.py/CLI → Tasks 1,2,8. §G.1 filename fix → Task 3. §G.2 folder convention → Task 9 (README, doc-only as specified). Testing → Tasks 1–3,8,9. ✔ no gaps.
- **Placeholders:** none — every code step shows complete code; data files specified by template + authoritative table; the validating test is the data correctness gate.
- **Type consistency:** `assets.list_assets/load_asset/validate_asset/supports_export`, `formats.validate_asset_refs`, `render._strip_version_label` — names used consistently across Tasks 2,3,8,9.
