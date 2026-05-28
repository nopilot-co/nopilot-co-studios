# design-studio

A Claude Code plugin that turns Markdown into branded, versioned PDF, PPTX, and HTML deliverables — with an LLM-driven brand-ingestion flow, deterministic rendering via Quarto + Typst, and visual QA against the brand spec.

## Why this exists

You write knowledge work in Markdown with Claude Code. You want it rendered to PDF, PPTX, and HTML against a specific brand — colors, typography, logos, voice — without leaving the terminal, and without reinventing the brand abstraction for each format. This plugin does that:

- **One brand spec** (`_brand.yml` per [Posit's brand.yml standard](https://posit-dev.github.io/brand-yml/)) drives all three formats via [Quarto](https://quarto.org/) + [Typst](https://typst.app/).
- **Per-brand workspaces** at `~/context/studios/design/<brand-slug>/` keep brand assets, reference decks, tone-of-voice, and outputs cleanly separated.
- **Versioned outputs** (semver-style `name.v1.0.0.pdf`) in auto-created session folders.
- **Visual QA** rasterizes each output, screenshots HTML, and critiques against the brand rubric.

## Architecture

```
Claude Code session
  │
  ▼
/design-studio  ──►  pick brand  ──►  init session folder
                                            │
            ┌───────────────────────────────┴────────────────────────┐
            ▼                                                        ▼
   render (Quarto + Typst)                                  visual-qa (screenshots + critique)
            │                                                        │
            ▼                                                        ▼
  ~/context/studios/design/<brand>/outputs/<session>/outputs/    .../qa/<version>/
```

Pure-Python where determinism matters (file ops, versioning, subprocess orchestration, rasterization). LLM-driven where judgment matters (brand ingestion, visual critique, content composition).

## Install

```bash
cd /Users/ted/Projects/studios/design
./install.sh
```

This:
1. Creates the symlink `~/.claude/plugins/design-studio` → this directory.
2. Creates `~/context/studios/design/` (your per-brand workspace root).
3. Checks for runtime dependencies (`quarto`, `libreoffice`, Python deps) and prints `brew install` / `pip install` commands for anything missing.
4. Installs the local `studio` Python package (editable).

## Runtime dependencies

| Tool | Purpose | Install |
|---|---|---|
| `quarto` ≥ 1.6 | Primary renderer (MD → PDF/PPTX/HTML/RevealJS) | `brew install --cask quarto` |
| `typst` | PDF engine (Quarto auto-fetches, but having it locally helps) | `brew install typst` |
| `libreoffice` | PPTX → PDF for QA rasterization | `brew install --cask libreoffice` |
| Python ≥ 3.10 | Orchestrator | `brew install python@3.12` |

Python packages (installed by `install.sh`): `pypdfium2`, `python-pptx`, `pyyaml`, `jinja2`, `jsonschema`, `pillow`, `playwright` (optional, for headless HTML screenshots if not using Claude_Preview MCP).

## Usage

```
/design-studio
```

Walks you through:
1. **Pick brand** — or **ingest a new brand** from existing PDFs / decks / website / logo files.
2. **Pick format** — a `<purpose>-<export>` slug (e.g. `pitch-pdf`). See [Formats](#formats).
3. **Init session** — creates `~/context/studios/design/<brand>/outputs/<session>/` with the format locked in.
4. **Render** — your current Markdown to the format's single export, versioned, with the ruleset enforced.
5. **QA** — screenshots + critique against the brand *and* the format contract, written to `qa/v<version>/findings.md`.

Or invoke skills individually:
- `/design-studio:brand-ingest <source-paths-or-urls>`
- `/design-studio:render <session-folder>` (export comes from the session's locked format)
- `/design-studio:visual-qa <session-folder> [--version 1.0.0]`

## Formats

A **format** is what you're making: a *purpose* (`pitch`, `proposal`) crossed with
an *export* (`pdf`, `html`, `pptx`, `revealjs`, `glide`), named `<purpose>-<export>`
— e.g. `pitch-pdf`. The purpose owns the style guide, execution brief, and ruleset
once; each export layers on only what differs. Contracts live in [`formats/`](formats/)
and resolve by deep-merge (`purposes/<purpose>.yml` ← `exports/<export>.yml` ← the
slug's `overrides`).

Every session **locks in one format slug**. `render` produces that single export
and enforces the count ruleset (`max_pages`/`max_slides`); `visual-qa` critiques
against the resolved contract. The same content in two exports is two sessions.

```bash
studio formats list                      # available slugs + their export
studio formats show --format pitch-pdf   # the resolved contract
studio formats validate --format pitch-pdf
```

Add purposes, exports, or slugs by dropping YAML into `formats/`. Renderable
exports today: `pdf`, `html`, `pptx`, `revealjs`. `glide` is a contract only
(no render pipeline yet). Full details: [`formats/README.md`](formats/README.md).

## Brand folder layout

```
~/context/studios/design/<brand-slug>/
├── brand/
│   ├── _brand.yml              ← single source of truth (colors, fonts, logo)
│   ├── reference.pptx          ← PPTX master slides (Quarto reference-doc)
│   ├── typst-overrides.typ     ← optional Typst overrides beyond _brand.yml
│   ├── css/overrides.css       ← optional HTML/RevealJS overrides
│   ├── assets/
│   │   ├── logo.svg
│   │   ├── logo-dark.svg
│   │   └── fonts/
│   ├── tone-of-voice.md        ← prompt-injected during composition (not rendered)
│   ├── style-guide.md          ← writing rules (not rendered)
│   └── ingest-sources/         ← original brand materials kept for re-ingestion
└── outputs/
    └── <session-folder>/       ← YYYY-MM-DD-<slug> or named
        ├── inputs/source.md
        ├── outputs/
        │   ├── doc.v1.0.0.pdf
        │   ├── doc.v1.0.0.pptx
        │   └── doc.v1.0.0.html
        ├── qa/
        │   └── v1.0.0/
        │       ├── page-01.png
        │       ├── slide-01.png
        │       └── findings.md
        └── version.json
```

## Development

The plugin is symlinked, so edits to `/Users/ted/Projects/studios/design/` take effect immediately in any Claude Code session.

Python orchestrator is callable directly:
```bash
studio formats list
studio ingest --brand new-co --sources ~/Downloads/brand-guidelines.pdf
studio session init --brand acme --name 2026-05-25-pitch --format pitch-pdf --source pitch.md
studio render --session ~/context/studios/design/acme/outputs/2026-05-25-pitch --bump patch
studio qa capture --session ~/context/studios/design/acme/outputs/2026-05-25-pitch --version 1.0.0
```
