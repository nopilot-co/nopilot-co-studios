---
name: audience-critique
description: Critique an artifact as the reader — score it against the reader-fit rubric, judge whether their needs are met, and produce a ranked list of target strengthening areas. Writes review/v<ver>/scores.yml + findings.md, runs `audience review score` (reuses the nitpicker engine), and fills strengthening-areas.md. Use after scoring-rubric, on real work.
---

# audience-critique

Assess a real piece of work **from the reader's chair**: would *this* reader feel
their needs are met? The output is a weighted reader-fit verdict plus the concrete
areas to strengthen so the work lands. You read as the reader; the nitpicker engine
computes the verdict from your scores.

## Steps

1. **Open the critique session:**
   ```bash
   audience review new --name <kebab-name> --audience <slug> --target <path-or-url> [--brief <path>]
   ```
   This copies the target and creates `review/v1.0.0/`. The artifact can come from
   any studio (a design deck, a messaging email, a planner document).

2. **Read as the reader.** Hold the reader model in mind — their needs, objections,
   decision factors, and what they `avoid`. Go through the rubric test by test:
   does the artifact meet that need, judged against the test's criteria? Score each
   1–5, honestly. Note *why* — the specific gap or strength.

3. **Write `review/v<ver>/scores.yml`** (`<ver>` = the session's `current`, e.g.
   `1.0.0`):
   ```yaml
   dimensions:
     reader-fit: { score: 3, note: "overall how well it serves this reader" }
   tests:
     <need-id-1>: { score: 2, note: "no proof at the scale they care about" }
     <need-id-2>: { score: 4, note: "addresses the toil objection well" }
   ```
   Score every rubric test plus the rolled-up `reader-fit` dimension.

4. **Compute the verdict + strengthening areas:**
   ```bash
   audience review score --session <path>
   ```
   This hands your scores + the slug's rubric to the nitpicker engine
   (`nit aggregate`) using the shared review policy — same gates/weights/bands as a
   nitpicker verdict — and writes `scorecard.json` and a ranked
   `strengthening-areas.md` (lowest-scoring, highest-priority needs first). Don't
   hand-compute the verdict.

5. **Write `review/v<ver>/findings.md`** — the reader-perspective narrative:
   ```markdown
   # Reader-fit critique — <reader> · <session> · v<version>

   **Reader-fit:** <pass | revise | fail>   **Overall:** <NN>/100
   <unmet must-haves, if any>

   ## Where it meets the reader
   - <need> — why it lands

   ## Target strengthening areas (ranked)
   - <need> (<score>/5) — the concrete gap, in the reader's terms — how to strengthen it
   ```
   Then flesh out the `<!-- … -->` placeholders in `strengthening-areas.md` with the
   concrete gap + fix for each weak area.

6. **Report back:** the reader-fit verdict, overall score, any unmet must-haves,
   and the top strengthening areas. If the artifact came from another studio, offer
   to route those areas back (design → re-render, messaging → re-compose, planner →
   re-draft a section) for a re-critique. **The audience studio never edits the
   work** — it critiques.

## Conventions

- Score as the reader, not as a generalist. "Excellent but wrong for this reader"
  is exactly what this lens exists to catch.
- `audience review score` owns the verdict math (single-sourced in the nitpicker
  engine). Your job is honest scores against the criteria + concrete strengthening
  areas. If the number feels wrong, the scores or the rubric are wrong — fix those.
- A reader-fit `fail` is advisory unless a **must-have (gate) need** is unmet —
  then it's a hard miss. Every strengthening area names a specific gap and a fix.
- Don't invent weaknesses to look thorough. If the work serves the reader, say so.
