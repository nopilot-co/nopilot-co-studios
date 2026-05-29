---
description: Rigorously review an asset (file or URL) — visual/format QA, brief fulfilment, audience/ICP fit, standardised tone-of-voice, and the scored test battery (so-what / yawn / sniff) — and return a weighted verdict with findings.
argument-hint: <target file-or-URL> [against <brief>] [for <brand>]
---

# /nitpicker-studio

Orchestrate a full nitpicker review of one asset, end to end. The nitpicker
**reviews; it never edits the asset** — the output is findings + a scored
verdict. Run the skills in order, each driving its `nit` subcommand.

`$ARGUMENTS` names the **target** (a rendered file or a live URL), optionally the
**brief** it must fulfil and the **brand** whose voice applies.

## Pipeline

1. **review-intake** — establish the session.
   - Identify the target, the brief (ask for or draft one if absent), the brand
     (optional, for the voice overlay), and the ICP / target audience.
   - `nit new --name <kebab> --target <path-or-url> [--brief <path>] [--brand <slug>] [--icp <path>]`
   - Fill `inputs/brief.md` and `inputs/icp.md` if they were scaffolded as stubs.

2. **visual-qa** — capture + critique the look.
   - `nit capture --session <path>` (rasterises the target; text-only targets
     skip capture). For URLs/HTML prefer the browser MCP / chrome-devtools /
     playwright to inspect the live thing.
   - Critique each captured view against `../configs/default/design-principles.yml`
     and, with a brand, the brand spec.

3. **brief-fulfilment** — judge the asset as a fulfilment of `inputs/brief.md`.

4. **audience-fit** — judge it from the `inputs/icp.md` perspective
   (linguistic / communication / content / solution / offering).

5. **tone-of-voice** — apply `../configs/default/tone-of-voice.yml` rigorously,
   overlaid by the brand's `tone-of-voice.md` if any (`nit config show --brand …`).

6. **apply-tests** — score the asset through every test in `../configs/tests/`
   (`nit tests list`).

7. **verdict** — consolidate every dimension + test score into
   `review/v<ver>/scores.yml` and write the narrative `findings.md`, then
   `nit score --session <path>` to compute the weighted verdict + `scorecard.json`.

## Report

Return: the **verdict** (`pass | revise | fail`), the **overall score**, any
**gate failures**, the **critical findings**, and the path to `findings.md` +
`scorecard.json`. If `revise`/`fail`, summarise the top fixes — and, if the asset
came from another studio, offer to route those fixes back there for a re-render →
re-review cycle.
