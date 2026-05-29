---
name: visual-qa
description: Document visual & format QA of the asset under review. Captures the target (PDF/PPTX/HTML/URL/image) and critiques it against the design baselines and, with a brand, the brand spec — using the browser MCP / chrome-devtools / playwright for live or HTML targets. Writes the visual section of the review. Use after review-intake.
---

# visual-qa

Visual and format QA of the asset. Deterministic capture, LLM critique. Score the
result 1–5 and record findings; the numeric score feeds the final verdict.

## Steps

1. **Capture the target:**
   ```bash
   nit capture --session <path>            # advances version; rasterises target
   ```
   Writes to `capture/v<ver>/`:
   - `pdf-page-NN.png` — one per PDF page (pypdfium2)
   - `pptx` → PDF (LibreOffice headless) → `pdf-page-NN.png`
   - `url-fullpage.png` / `html-fullpage.png` — full-page screenshot
   - `image.<ext>` — image targets copied as-is
   - text-only targets (`.md`/`.txt`) capture nothing — critique the source.

   **For URLs and HTML, prefer live inspection** over the static screenshot when a
   browser tool is available — it catches what a single screenshot can't
   (responsive behaviour, interaction, console/network errors, contrast in situ):
   - **chrome-devtools MCP** — `new_page`/`navigate_page`, `take_screenshot`,
     `take_snapshot` (a11y tree), `list_console_messages`, `resize_page` to test
     breakpoints, `lighthouse_audit` for an objective a11y/perf read.
   - **playwright MCP** — `browser_navigate`, `browser_snapshot`,
     `browser_take_screenshot`, `browser_resize`.
   Use these to verify the captured screenshot reflects reality, then critique.

2. **Load the standards:**
   - **Design baseline:** `../configs/default/design-principles.yml` (contrast,
     line length, hierarchy, whitespace, typography, colour use, alignment;
     creative: concept clarity, originality, craft, cohesion).
   - **Brand** (if `version.json` has one): `~/context/studios/brand/<brand>/_brand.yml`
     for colours/fonts/logo, plus its `style-guide.md`. (Legacy brands live at
     `~/context/studios/design/<brand>/brand/`.)

3. **Critique each captured view** against the rubric:

   **Format fidelity** — does it suit its medium? (a deck is one-idea-per-slide
   and speaker-led; a page is a responsive scroll; a PDF is print-clean.) Any
   truncation, overflow, broken layout, horizontal scroll, missing assets?

   **Visual baseline** — contrast (WCAG AA), line length 50–90ch, clear heading
   hierarchy, whitespace, no unintended fallback fonts, semantic colour use,
   consistent alignment.

   **Brand fidelity** (if a brand) — correct primary/secondary colours, correct
   heading + body typefaces (flag fallbacks like Times New Roman / Arial /
   system-ui), logo present + correct variant/size/position.

   **Creative** — single clear concept, no template-default look, finished
   details (no orphans/widows), the piece reads as one designed thing.

4. **Score and record.** Assign a 1–5 for the `visual-qa` dimension and write your
   findings (with the specific page/slide/view and a suggested fix) into the
   review notes the `verdict` skill will consolidate. Severities: **critical** =
   brand-breaking or illegible; **significant** = clearly off; **minor** = polish.

## Constraints

- Don't invent findings to look thorough. If it's clean, say so.
- Don't re-flag count limits a producing studio's lint already enforces
  (`max_pages`/`max_slides`); confirm the *qualitative* result here.
- One pass. Iterative QA is a re-capture → re-review cycle, not a deeper pass.
