---
description: Model the reader (a structured psychographic profile + need-state), derive a weighted rubric, and critique work against it — returning a reader-fit verdict and ranked strengthening areas. Reuses the nitpicker scoring engine.
argument-hint: <reader slug or description> [from <context files>] [critique <artifact>]
---

# /audience-studio

Orchestrate the audience studio end to end: build a reusable reader model, derive a
weighted rubric from it, and critique work **as that reader**. The studio
**critiques; it never edits the work**. Run the skills in order, each driving its
`audience` subcommand. Scoring reuses the nitpicker engine, so the verdict reads
identically to a nitpicker verdict.

`$ARGUMENTS` names the **reader** (a slug to build/reuse, or a description to infer
from), optionally **context** to research and an **artifact** to critique.

## Pipeline — model the reader (`model-audience`)

1. **persona-intake** — take or infer + user-validate the persona; pick a slug.
   - `audience persona new --audience <slug> [--persona <path>]`
2. **audience-research** — review supplied context (transcripts/docs/URLs) + do
   background research; file + cite each source.
   - `audience research add --audience <slug> --source <path-or-url> --kind …`
3. **psychographic-profile** — synthesize the structured `_audience.yml`
   (psychographics + need-state), cited to research.
   - `audience profile validate` → `audience profile build --audience <slug> [--status validated]`
4. **scoring-rubric** — derive the weighted rubric and fill its criteria.
   - `audience rubric derive --audience <slug>` → fill criteria → `audience rubric validate`

## Pipeline — critique the work (`assess-audience-fit`)

5. **audience-critique** — critique an artifact against the reader model.
   - `audience review new --name <kebab> --audience <slug> --target <path-or-url> [--brief <path>]`
   - Score each rubric test 1–5 into `review/v<ver>/scores.yml`, then
     `audience review score --session <path>` (→ scorecard + ranked
     `strengthening-areas.md`), and write the narrative `findings.md`.

## Report

Return: the **reader-fit verdict** (`pass | revise | fail`), the **overall score**,
any **unmet must-haves** (gate needs), and the **ranked strengthening areas** (with
paths to `strengthening-areas.md` + `scorecard.json` + `findings.md`). If
`revise`/`fail` and the artifact came from another studio, offer to route the
strengthening areas back there for a fix → re-critique cycle.
