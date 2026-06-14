# Audience Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the studios
model and the three invocation modes). The studios invariant applies: **this
studio's skills are the single source of processing behavior** — the same skills
run whether invoked as a local plugin, via CLI from a server, or programmatically
server-side. Only the trigger and LLM host change.

Packaged as the Claude Code plugin **`audience-studio`** (`.claude-plugin/plugin.json`).
`./install.sh` creates `.venv` and installs the `audience` CLI. Pure-Python; it
reuses the nitpicker engine for scoring (shells out to `nit aggregate`), so the
only real dependency is the `nit` CLI — `audience doctor` reports it.

## What it does

The audience studio models **the reader** — the specific person a piece of work
must satisfy — and critiques work against them. It is a reader-**subjective**
review lens, complementary to the nitpicker's **objective** one (house standards +
brief + brand). The reader model is a reusable, studios-level resource, like a
brand.

1. **persona-intake** — take a supplied, or infer-and-user-validate, persona.
2. **audience-research** — review supplied context (transcripts/docs/URLs) + do
   background research; extract needs, challenges, objectives, attitudes, approach.
3. **psychographic-profile** — synthesize a structured psychographic profile +
   need-state into `_audience.yml`.
4. **scoring-rubric** — derive a weighted rubric from the need-state (one scored
   test per need; critical needs gate), in the nitpicker test format.
5. **audience-critique** — critique an artifact as the reader → reader-fit verdict
   + ranked target strengthening areas.

Judgment lives in the skills; the `audience` CLI does only mechanics (store
scaffolding, source filing + provenance, model/rubric validation, session
versioning, and handing scoring to the nitpicker engine).

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/audience/`, the `audience` CLI) — no judgment.

The `/audience-studio` command (`commands/audience-studio.md`) orchestrates them.

| Skill | Drives | Does |
|-------|--------|------|
| `persona-intake`        | `audience persona new`     | take/infer + user-validate the persona; scaffold the store |
| `audience-research`     | `audience research add`    | file + review supplied context and background research, cited |
| `psychographic-profile` | `audience profile build`   | synthesize the structured profile + need-state into `_audience.yml` |
| `scoring-rubric`        | `audience rubric derive`   | derive the weighted reader-fit rubric (nitpicker test format) |
| `audience-critique`     | `audience review score`    | critique an artifact as the reader → verdict + strengthening areas |

## Reuses the nitpicker scoring engine

Reader-fit scoring is **not** re-implemented. `audience review score` writes the
per-test scores, then shells out to `nit aggregate --scores <scores.yml>
--tests-from <rubric.yml>` (`scripts/audience/nit_bridge.py`), which runs the
nitpicker's single-sourced aggregation (`nit.tests.aggregate`) against the same
`../configs/default/review-policy.yml`. The rubric's critical needs are passed as
gates. So a reader-fit verdict reads identically to a nitpicker verdict, and the
verdict math has exactly one home.

The structured `_audience.yml` can also feed the nitpicker's own `audience-fit`
skill (replacing its freetext `inputs/icp.md`) so both lenses share one reader
model.

## Data root (outside the repo)

The reader model is a **studios-level** entity, shared and reusable like a brand
(`AUDIENCE_ROOT = ~/context/studios/audience/<slug>/`). Critique sessions live
under the model. Same override chain as the other studios (`$STUDIOS_DOCKET_ROOT`,
`$STUDIOS_PROJECT_ROOT`, `.wip/config.yml`, else the default).

```
~/context/studios/audience/<slug>/          # reusable reader model (like a brand)
  _audience.yml        # structured psychographic profile + need-state (source of truth)
  rubric.yml           # derived weighted reader-fit rubric (nitpicker test shape)
  research/
    <source>.md        # cited reviews of transcripts/docs (skill-written)
    sources/           # the raw filed sources
  sessions/<name>/     # one critique session per artifact
    inputs/{target/, brief.md}
    review/v<ver>/
      scores.yml             # per-rubric-test + reader-fit scores (skill-written)
      findings.md            # reader-perspective narrative (skill-written)
      scorecard.json         # weighted verdict (written by `audience review score`)
      strengthening-areas.md # ranked target strengthening areas
    version.json       # { session, audience, target, target_kind, status, created, current, history[] }
```

`_audience.yml` is validated against `scripts/audience/schemas/audience.schema.json`;
`rubric.yml` against `scripts/audience/schemas/rubric.schema.json`. Slugs and
session names are kebab-case.

## Code map (`scripts/audience/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `audience <command>`; subcommands mirror the skills |
| `store.py` | The shared reader-model store: scaffold / read / write / validate `_audience.yml`; list / show |
| `research.py` | File a source into `research/` + record provenance |
| `rubric.py` | Derive the rubric from the need-state; validate it |
| `session.py` | Critique sessions + versioning; the score tie-in (writes scorecard + strengthening areas) |
| `nit_bridge.py` | Reuse the nitpicker engine via `nit aggregate` (CLI boundary) |
| `deps.py` | `audience doctor` — is `nit` reachable? list models |
| `schemas/*.json` | JSON Schemas for the reader model + rubric |

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/audience/` — this is
  what makes the studio behave identically across invocation modes.
- The audience studio **critiques; it never edits the work.** Strengthening areas
  + a verdict are the output; fixes are the producing studio's job, then a
  re-critique.
- An **inferred** persona must be user-validated before delivery decisions lean on
  it (`status: validated`). Be explicit about which it is.
- Scoring is single-sourced in the nitpicker engine. Don't re-implement the
  verdict math here — if the number feels wrong, the scores or the rubric are.
- The reader model is reusable and studios-level (like a brand). Don't rebuild it
  per artifact; reference it by slug.
