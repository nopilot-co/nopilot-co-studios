---
description: Brand-aware design studio — render the current Markdown to a chosen format (purpose × export, e.g. pitch-pdf) against a chosen brand, with versioned outputs and visual QA enforced against the format contract.
---

You are entering the **design-studio** workflow. Coordinate the following skills in order, asking the user concise questions only when a decision is needed.

## Steps

1. **Pick the brand.** Invoke the `brand-pick` skill. If no brands exist yet, or the user wants a new one, invoke `brand-ingest` first to create the canonical brand spec.

2. **Lock in the format.** Decide the format slug (`<purpose>-<export>`, e.g. `pitch-pdf`) — run `studio formats list` to see the options. Derive it from what the user wants ("a pitch as a PDF" → `pitch-pdf`); ask only if purpose or export is genuinely ambiguous. If the user wants the same content in **several exports** (e.g. PDF *and* HTML), that is **one session per format slug** — run steps 3–5 once per format. Read the chosen contract with `studio formats show --format <slug>` so you compose to its execution brief.

3. **Initialise the session.** Invoke the `session-init` skill, passing the locked format slug. It creates the per-session folder under `~/context/studios/design/<brand-slug>/outputs/<session-folder>/`, validates and stores the format in `version.json`, and copies the source Markdown into `inputs/`.

4. **Render.** Invoke the `render` skill. The export is fixed by the session's format slug (no format choice here); outputs are versioned (semver) in the session's `outputs/` folder, and the count ruleset (`max_pages`/`max_slides`) is enforced.

5. **Visual QA.** Invoke the `visual-qa` skill against the rendered version. It rasterises PDF, screenshots HTML, converts PPTX → PDF → image, and writes `qa/v<version>/findings.md` critiquing the result against **both** the brand spec and the locked format contract (required sections, ruleset, purpose/export fit).

6. **Report.** Summarise to the user: brand, **format slug**, session folder, output path, version, and the top QA findings (severity-ranked). Offer to bump the version and re-render with adjustments.

## Inputs the user may pass

- `$ARGUMENTS` — if non-empty, treat as the path to the source Markdown file. Otherwise, ask the user which file to render or use the most recent `.md` in the cwd.

## Conventions

- Never write outputs anywhere except under `~/context/studios/design/<brand-slug>/outputs/<session>/`.
- Always bump the patch version on re-render within the same session; bump minor when the user explicitly asks for a "revision"; bump major when the user changes the brand mid-session (rare — usually start a new session instead).
- If the user pivots brands mid-session, ask whether to start a fresh session or continue under the current one (renders will live alongside the prior brand's outputs, which is usually wrong).
