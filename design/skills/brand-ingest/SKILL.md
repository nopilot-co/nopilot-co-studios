---
name: brand-ingest
description: Build a canonical studios-level brand spec from existing source materials (PDFs of brand guidelines, decks, websites, logo files, style tokens). Produces a normalised ~/context/studios/brand/<brand-slug>/ folder with _brand.yml, reference.pptx, assets, tone-of-voice.md, and style-guide.md. Use whenever the user wants to onboard a new brand or refresh an existing one from updated source materials.
---

# brand-ingest

You are normalising messy brand source materials into the **canonical design-studio brand spec**. The Python orchestrator handles deterministic extraction (color quantization, font detection, PPTX master extraction). You handle synthesis: writing the brand.yml, tone-of-voice, style-guide, and choosing canonical values from noisy inputs.

## Output: canonical brand folder

```
~/context/studios/brand/<brand-slug>/      ← shared studios-level brand store
├── _brand.yml              ← Posit brand.yml standard (drives Quarto rendering)
├── reference.pptx          ← PPTX master slides (Quarto reference-doc)
├── typst-overrides.typ     ← optional, only if _brand.yml is insufficient
├── css/overrides.css       ← optional HTML/RevealJS overrides
├── assets/
│   ├── logo.svg            (or .png if SVG unavailable)
│   ├── logo-dark.svg
│   └── fonts/              ← any custom font files supplied by the brand
├── tone-of-voice.md        ← prompt-injected during composition
├── style-guide.md          ← writing rules, terminology, capitalisation
└── ingest-sources/         ← copies of the originals, for re-ingestion later
```

## Workflow

1. **Confirm the brand-slug** with the user (kebab-case, e.g. `acme`, `northstar-finance`). Reject if a folder of that name already exists unless the user explicitly says "refresh".

2. **Gather sources.** Ask the user for paths/URLs to any of:
   - Brand guidelines PDF (the holy grail — usually contains colors, type, logo usage, voice)
   - Existing decks (.pptx, .key) — extract master slides + colors
   - Existing docs (.docx, .pdf) — extract typography in use
   - Website URL — scrape primary colors, typography, logo
   - Bare logo file(s) — extract palette, infer pairing
   - Design tokens JSON (Figma export, Style Dictionary)

3. **Run deterministic extraction.** Invoke:
   ```bash
   studio ingest --brand <slug> --sources <path1> <path2> ...
   ```
   `--sources` accepts files **or folders**. Folders are walked recursively;
   every supported file (`.pdf .pptx .png .jpg .jpeg .svg`) inside is extracted
   from. Hidden files and `__pycache__` / `node_modules` / `.git` are skipped.
   So if the user hands you a brand-assets folder, point at it directly:
   ```bash
   studio ingest --brand acme --sources ~/Dropbox/Acme-Brand-Pack/
   ```

   This:
   - Copies each source (file or whole folder tree) into `brand/ingest-sources/`
   - Extracts dominant colors from logos (k-means quantization)
   - Lists fonts found in PDFs/decks
   - Extracts PPTX master slides from any `.pptx` it finds (first one wins as `reference.pptx`)
   - Scaffolds a draft `_brand.yml` with extracted values pre-filled
   - Writes an `_ingest-report.md` listing what was found, per source, with relative paths inside folders

4. **Read the ingest report** and the source materials directly (use Read for PDFs and any text files; describe images you can see). For each value that needs judgment, decide:
   - **Primary brand color** — usually the one used for headings, links, accents
   - **Secondary/accent colors** — for callouts, dataviz, highlights
   - **Foreground/background pair** — body text on page
   - **Heading typeface** — often distinct from body
   - **Body typeface** — readability-first
   - **Monospace** — for code blocks; fall back to system mono if not specified
   - **Logo variants** — light/dark, horizontal/stacked

5. **Write `_brand.yml`** to the canonical schema. Use `templates/_brand.example.yml` in the plugin as a starting point. Keep it minimal — Quarto will fill defaults sensibly.

6. **Write `tone-of-voice.md`** by reading the voice/tone sections of the source guidelines and distilling them into:
   - 3–5 voice attributes (e.g. "direct, warm, never glib")
   - Forbidden words/phrases
   - Preferred constructions
   - A 2–3 sentence example passage demonstrating the voice
   This file is NOT rendered — it's injected into Claude's context during composition.

7. **Write `style-guide.md`** with:
   - Capitalisation rules (title case? sentence case? brand-name casing?)
   - Numbers, dates, currency formatting
   - Oxford comma policy
   - Preferred terminology / glossary
   - Anything in the source guidelines about writing mechanics

8. **Handle the reference.pptx.** If the brand provided a deck:
   - The ingest script extracts it to `brand/reference.pptx`.
   If not:
   - Generate one from a Quarto template applying `_brand.yml`:
     ```bash
     studio ingest synthesize-pptx --brand <slug>
     ```
   - This renders an empty 5-slide deck (title, section, content, two-column, closing) using brand tokens and saves it as the reference.

9. **Validate.** Run:
   ```bash
   studio brand validate --brand <slug>
   ```
   Fixes any schema issues, then prints a confirmation.

10. **Show the user a summary**: brand-slug, folder path, key choices made, anything ambiguous that they should review. Offer to do a smoke-test render of a sample document so they can see the brand in action.

## What to push back on

- If sources are thin (no guidelines, no deck, just a logo), say so plainly. Offer to use sensible defaults + the logo's palette, and recommend revisiting after the brand is documented properly.
- If the user supplies conflicting colors across sources (deck uses #1A2B3C, guidelines say #1B2C3D), flag the discrepancy and ask which is authoritative.
- Do not invent voice/tone from thin air. If no voice guidance exists in sources, leave `tone-of-voice.md` as a 2-line stub: "No voice guidance was provided. Defaults to neutral professional. Update this file when voice work is done."
