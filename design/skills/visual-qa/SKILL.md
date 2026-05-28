---
name: visual-qa
description: Visual QA pass over a rendered version. Rasterises PDF pages, screenshots HTML, converts PPTX→PDF→images, and writes a brand-rubric critique to qa/v<version>/findings.md. Use after render.
---

# visual-qa

Visual QA against the brand spec. Deterministic capture, LLM critique.

## Steps

1. Identify the version to QA. Default: latest in `version.json`. User can override with `--version 1.0.0`.

2. Capture screenshots:
   ```bash
   studio qa capture --session <path> --version <ver>
   ```
   This writes:
   - `qa/v<ver>/pdf-page-NN.png` — one per PDF page (via pypdfium2)
   - `qa/v<ver>/pptx-slide-NN.png` — PPTX → PDF (libreoffice headless) → PNG
   - `qa/v<ver>/html-fullpage.png` — full-page HTML screenshot
     - Prefer the `Claude_Preview` MCP if available (start it on the HTML file, then `preview_screenshot`)
     - Fall back to `playwright` if installed
     - Fall back to `wkhtmltoimage` if not

3. Load both contracts for the critique:
   - **Brand:** read `~/context/studios/brand/<brand>/_brand.yml` for
     colors/fonts/logo expectations, plus `tone-of-voice.md` and
     `style-guide.md` in the same folder for voice expectations. (Legacy brands
     live at `~/context/studios/design/<brand>/brand/`.)
   - **Format:** read the session's locked format from `version.json` and resolve
     it:
     ```bash
     studio formats show --format <slug>   # slug = version.json "format"
     ```
     This gives the `style_guide`, `execution_brief` (including
     `required_sections`), and `ruleset` you must judge against.

4. Critique each screenshot against the **rubric**:

   **Format fidelity** (contract)
   - Are all `execution_brief.required_sections` present and recognizable?
   - Does it honor the `ruleset` (within `max_pages`/`max_slides`, `must_include_cta`,
     `must_include_pricing_table`, tone, etc.)? Count-based limits are already
     enforced by `render`; confirm the *qualitative* ones here.
   - Does it read as the intended purpose (a pitch should persuade and end on the
     ask; a proposal should be precise and complete) and suit the export
     (a deck is speaker-led one-idea-per-slide; an HTML page is a responsive scroll)?

   **Brand fidelity** (visual)
   - Are the brand's primary/secondary colors used? Where they shouldn't be?
   - Is the heading typeface correct? Body typeface correct? Any unexpected fallbacks (Times New Roman, Arial, system-ui appearing where a brand font should be)?
   - Is the logo present, correct variant for the background, correctly sized and positioned?
   - Are brand colors used semantically (e.g. primary for links/CTAs, not body text)?

   **Hierarchy & legibility**
   - Heading levels clearly differentiated?
   - Line length 50–90 chars at body size?
   - Sufficient contrast (WCAG AA at minimum)?
   - Whitespace breathing room around sections, headings, lists?

   **Format-specific**
   - PDF: page numbers, margins, orphan/widow lines, table overflow
   - PPTX: per-slide content fits without overflow, master slide layouts respected, no truncated text
   - HTML: responsive layout sane, no horizontal scroll, links visibly styled

   **Voice/tone** (text-level, read from the source.md plus rendered output)
   - Adherence to `tone-of-voice.md` attributes
   - No forbidden words/phrases
   - Style-guide compliance (capitalisation, terminology)

5. Write findings to `qa/v<ver>/findings.md` in this structure:

   ```markdown
   # Visual QA — <brand> · <format-slug> · v<version>

   **Verdict:** <pass | revise | fail>

   ## Critical (must fix)
   - <finding> — <which page/slide> — <suggested fix>

   ## Significant (should fix)
   - ...

   ## Minor (nice to fix)
   - ...

   ## What's working well
   - ...
   ```

6. Report back to the user: the verdict, the critical-count, and the path to `findings.md`. If verdict is `revise` or `fail`, offer to make the suggested fixes and re-render.

## Constraints

- Do not invent findings to look thorough. If the output is clean, say so.
- Severity calibration: **critical** = brand-breaking (wrong logo, wrong color, illegible). **significant** = clearly off but not breaking. **minor** = polish.
- One pass only. If the user wants iterative QA, that's a re-render → re-QA cycle, not a deeper single pass.
