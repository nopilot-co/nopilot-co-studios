---
name: render
description: Render the session's source Markdown to its locked format's export (PDF, PPTX, HTML, or RevealJS) using Quarto + Typst with the active brand's _brand.yml. The export is fixed by the session's format slug. Outputs are versioned (semver). Use after session-init.
---

# render

Renders the source Markdown via Quarto, applying the brand spec **and the
session's locked format contract**.

## Steps

1. The export is **not a choice here** — it is fixed by the format slug locked at
   `session-init` (`version.json` → `format`). `studio render` reads it and
   produces exactly that one asset type. Before rendering, read the contract so
   you compose to its execution brief:
   ```bash
   studio formats show --format <slug>   # slug = version.json "format"
   ```
   Make sure the source Markdown satisfies the brief's `required_sections` and
   stays within the ruleset (e.g. `max_pages`, `max_slides`). If it can't, fix
   the content *before* rendering — `studio render` enforces the count rules and
   will fail the render if they're exceeded.

   If the format's export is not renderable (e.g. `glide`), `studio render`
   refuses it; tell the user and stop.

2. Determine the version bump:
   - First render in this session: `1.0.0`
   - Re-render after small changes: bump patch (`1.0.1`)
   - Re-render after content revision: bump minor (`1.1.0`)
   - Brand change mid-session: bump major (`2.0.0`) — but usually push back and suggest a new session

3. Run:
   ```bash
   studio render --session <session-path> --bump patch
   ```

   Under the hood this:
   - Reads the locked `format` from `version.json` and resolves it to a single
     export (e.g. `pitch-pdf` → `pdf`)
   - Materializes a Quarto project in a `.tmp/` subfolder of the session
   - Generates `quarto.yml` from `templates/quarto/quarto.yml.j2` with the brand's `_brand.yml` referenced
   - Copies brand assets (logo, fonts) into the Quarto project
   - Runs `quarto render` for that one format
   - Moves the output into `outputs/` with the versioned filename (e.g. `source.v1.0.0.pdf`)
   - Appends to `version.json`'s history
   - Cleans `.tmp/`
   - **Enforces the count ruleset** (`max_pages`, `max_slides`): if the rendered
     artifact exceeds it, the command exits non-zero and lists the violation.
     The file is still produced — trim the content and re-render.

4. Report back: the output path and size, the format slug, and any ruleset
   violations or Quarto warnings (e.g. font fallbacks, missing logo variants).

## Failure handling

- **`quarto` not found** — point the user at `install.sh` and the brew command in the README.
- **Typst font not found** — Quarto will warn; suggest adding the font file to `brand/assets/fonts/` and re-rendering.
- **PPTX reference deck missing** — fall back to Quarto's default PPTX template and warn the user; suggest running `brand-ingest synthesize-pptx`.
- **Render succeeds but output looks wrong** — that's `visual-qa`'s job, not render's. Don't try to judge the output here.
