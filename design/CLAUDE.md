# Design Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the studios
model and the three invocation modes). The studios invariant applies here: **this
studio's skills are the single source of processing behavior** — the same skills
run whether the studio is invoked as a local plugin, via CLI from a server, or
programmatically server-side. Only the trigger and LLM host change.

Packaged as the Claude Code plugin **`design-studio`** (`v0.1.0`; manifest at
`.claude-plugin/plugin.json`). `./install.sh` symlinks this directory to
`~/.claude/plugins/design-studio`, creates the workspace root, checks runtime
deps, and installs the `studio` Python package (editable).

## What it does

Turns Markdown into branded, versioned **PDF / PPTX / HTML (+ RevealJS)**. One
`_brand.yml` (Posit brand.yml standard) drives every format via **Quarto +
Typst**. LLM-driven where judgment matters (brand ingestion, content, visual
critique); deterministic Python where it matters (file ops, versioning,
subprocess orchestration, rasterization).

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/studio/`, the `studio` CLI) — no judgment.

Each skill drives its matching `studio` command; the `/design-studio` command
(`commands/design-studio.md`) orchestrates all five end-to-end.

| Skill | Drives | Does |
|-------|--------|------|
| `brand-pick`   | `studio brand list`              | choose the active brand for the session |
| `brand-ingest` | `studio ingest …` / `brand validate` | build a canonical brand spec from source material |
| `session-init` | `studio session init …`          | create the per-session workspace + `version.json` |
| `render`       | `studio render …`                | render Markdown → formats, versioned |
| `visual-qa`    | `studio qa capture …`            | rasterize outputs + critique against the brand rubric |

Slash entry points: `/design-studio` (orchestrator), or skills individually,
e.g. `/design-studio:brand-ingest`, `/design-studio:render`,
`/design-studio:visual-qa`.

## Formats (canonical entity)

A **format** is a *purpose* × *export*, named `<purpose>-<export>` (e.g.
`pitch-pdf`). The purpose (`pitch`, `proposal`) centralises intent — style guide,
execution brief, ruleset — and the export (`pdf`, `html`, `pptx`, `revealjs`,
`glide`) layers on asset-type specifics. Contracts live in `formats/` and resolve
by deep-merge: `purposes/<purpose>.yml` ← `exports/<export>.yml` ← the slug
file's `overrides`. See [`formats/README.md`](formats/README.md).

**Each session locks exactly one format slug** at `session-init` (stored in
`version.json`). `render` derives the single export from it and enforces the
count ruleset (`max_pages`/`max_slides`); `visual-qa` critiques against the full
resolved contract (required sections, tone, purpose/export fit). One session =
one format = one asset; the same content in two exports is two sessions.
Resolution, validation, and checks live in `scripts/studio/formats.py`, validated
against `scripts/studio/schemas/format.schema.json`.

## Resources (canonical design assets)

`resources/` is the **canonical location for template assets used to create
designs** — it must represent *100% of the design choices the studio can make*,
so any design is fully replicable. See [`resources/README.md`](resources/README.md).
Categories (extensible — add files or whole folders as policy grows):

- `design-systems/` — visual systems (color/type/spacing/radius/components) as
  `<slug>.md` (YAML token front-matter + prose). Index + canonical schema:
  `resources/design-systems/design.md`.
- `iconography/` — interchangeable SVG icon sets; a design picks one. Catalog +
  vendoring convention: `resources/iconography/icons.md`.
- `brand-voice/` — tone-of-voice / writing principles; `brand-voice-default.md`
  is the brand-agnostic default.

**Formats vs resources:** a *format* decides what the asset is and its ruleset;
*resources* decide how it looks and sounds. A *brand* (`_brand.yml`) is a specific
instantiation that should be consistent with a chosen design-system, icon set,
and voice. Aim: design choices stay **normalised, interchangeable, extensible,
consistent** — referenced by slug, never hard-coded.

> Not yet wired into the glue/skills: selecting a design-system / icon set per
> session (parallel to format lock-in). Today resources are the canonical
> catalog; the brand spec and skills consume them by convention.

## CLI

```
studio brand list | validate --brand SLUG | show --brand SLUG
studio formats list | show --format SLUG | validate --format SLUG
studio ingest --brand SLUG --sources PATH [PATH ...]   # files OR folders (walked recursively)
studio ingest synthesize-pptx --brand SLUG
studio session init --brand SLUG --name NAME --format SLUG --source PATH
studio render --session PATH --bump patch|minor|major
studio qa capture --session PATH [--version X.Y.Z]
```

- Entry point: `studio = studio.cli:main` (`pyproject.toml [project.scripts]`).
- `ingest` does **deterministic** extraction only (color quantization, font
  lists, PPTX master → `reference.pptx`) and writes a *draft* `_brand.yml` +
  `_ingest-report.md`; the `brand-ingest` skill refines them.
- `session init` **locks in a format slug** (validated against the contracts) and
  records it in `version.json`. The export to render is fixed by that slug, so
  `render` takes no `--formats` — it maps the locked export (`pdf → typst`
  engine; `revealjs` emits HTML), builds a Quarto project in `<session>/_render/`
  from `templates/quarto/quarto.yml.j2`, renders, moves the output to `outputs/`
  with a versioned filename, records to `version.json`, **enforces the count
  ruleset** (`max_pages`/`max_slides`), and cleans up.

## Data root (outside the repo)

Brand is a **studios-level** entity, shared with the messaging studio
(`BRAND_ROOT = ~/context/studios/brand/<slug>/`). Render sessions stay
design-owned (`CONTEXT_ROOT = ~/context/studios/design/<slug>/`). Brands created
before this elevation still live at the legacy `CONTEXT_ROOT/<slug>/brand/` and
are read transparently by `brand.brand_root()`.

```
~/context/studios/brand/<slug>/          # shared brand store (was design/<slug>/brand/)
  _brand.yml            # single source of truth — Posit brand.yml standard
  reference.pptx        # PPTX master slides (Quarto reference-doc)
  typst-overrides.typ   # optional Typst overrides
  css/overrides.css     # optional HTML/RevealJS overrides
  assets/               # logo.svg, logo-dark.svg, fonts/
  tone-of-voice.md      # injected into composition context; not rendered
  style-guide.md        # writing mechanics; not rendered
  ingest-sources/       # originals, preserved for re-ingestion
  _ingest-report.md     # what ingest extracted (regenerated each ingest)

~/context/studios/design/<slug>/outputs/  # design-owned render sessions
  <session>/            # YYYY-MM-DD-<slug> or named; immutable record
    inputs/source.md
    outputs/            # <stem>.v1.0.0.pdf / .pptx / .html  (semver filenames)
    qa/v<version>/      # pdf-page-NN.png, pptx-slide-NN.png, <fmt>-fullpage.png, findings.md
    version.json        # { brand, session, format, source_filename, created, current, history[] }
```

`_brand.yml` is validated against `scripts/studio/schemas/brand.schema.json`.
Slugs and session names are kebab-case. Version `0.0.0` jumps to `1.0.0` on first
render; then patch / minor / major bumps.

## Code map (`scripts/studio/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `studio <command>`; subcommands mirror the skills |
| `brand.py` | Load / validate / list / show brands |
| `formats.py` | Resolve / validate format slugs (purpose × export merge); deterministic ruleset checks |
| `ingest.py` | Deterministic extraction from sources; draft `_brand.yml` + report; `synthesize-pptx` |
| `session.py` | Session folders + semver versioning; locks the format into `version.json` |
| `render.py` | Quarto subprocess wrapper: derive export from locked format → `_render/` project → versioned move |
| `qa.py` | Capture: PDF→PNG (pypdfium2), PPTX→PDF→PNG (libreoffice), HTML screenshot |
| `schemas/brand.schema.json` | JSON Schema for `_brand.yml` |
| `schemas/format.schema.json` | JSON Schema for a resolved format contract |

`__init__.py` defines `CONTEXT_ROOT` (design render sessions), `BRAND_ROOT`
(shared studios-level brand store), `PLUGIN_ROOT` (this `design/` dir),
`TEMPLATES` (`templates/`), `SCHEMAS`. Templates:
`_brand.example.yml`, `quarto/quarto.yml.j2`, `typst/default.typ`,
`css/default.css`, `pptx/`.

## Dependencies

Native render tools can't be pip-installed or vendored, so the studio **declares,
detects, and degrades** rather than bundling them:

- **Declared** per export: `formats/exports/<export>.yml → requires: {render, qa}`.
  Quarto bundles typst, so PDF needs only `quarto` (no separate typst).
- **Detected** by `studio doctor` — reports tool presence and per-format
  readiness; `studio formats list` shows `(needs: …)` inline. `render`/`qa` fail
  at point of use with the exact install command.
- **Provisioned** via `Brewfile` (`brew bundle --file=design/Brewfile`) locally;
  the same manifest is the contract for a server image in modes 2–3.

Tools on `PATH`: **Quarto** (render; bundles typst for PDF), **LibreOffice**
(PPTX→PDF for QA only), **Python ≥ 3.10**. Python deps: `click`, `pyyaml`,
`jinja2`, `jsonschema`, `python-pptx`, `pypdfium2`, `pillow`; optional
`playwright` (HTML screenshots — else `wkhtmltoimage`, else `Claude_Preview` MCP).

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/studio/` — this is
  what makes the studio behave identically across invocation modes.
- `_brand.yml` is the only source of truth for brand identity; everything renders
  from it. Never hand-edit generated outputs.
- Write outputs only under `~/context/studios/design/<slug>/outputs/<session>/`.
  Session folders are immutable historical record — start a new session rather
  than rewriting one.
- One brand × one format slug per session, locked at `session-init`. To change
  the format or render another export, create a new session.
- Version bumps: patch on small re-render, minor on revision, major on
  mid-session brand change (usually start a new session instead).
