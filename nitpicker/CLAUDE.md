# Nitpicker Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the studios
model and the three invocation modes). The studios invariant applies: **this
studio's skills are the single source of processing behavior** — the same skills
run whether invoked as a local plugin, via CLI from a server, or programmatically
server-side. Only the trigger and LLM host change.

Packaged as the Claude Code plugin **`nitpicker-studio`** (`.claude-plugin/plugin.json`).
`./install.sh` creates `.venv` and installs the `nit` CLI. Review-only and mostly
pure-Python; the optional `[capture]` extra (pypdfium2 / pillow / playwright)
rasterises a target for visual QA. `nit doctor` reports capture-tool status.

## What it does

The nitpicker **reviews** an asset — it does not produce or edit one. Given a
target (a rendered file or a live URL) plus the brief it should fulfil, it judges:

1. **Visual & format QA** — capture the asset and critique it against the design
   baselines (and, with a brand, the brand spec). Uses the browser MCP /
   playwright / chrome-devtools for live or HTML targets.
2. **Brief fulfilment** — does the asset actually deliver what the brief asked?
3. **Audience / ICP fit** — does it land for the target audience
   (linguistically, in content, in the solution/offering it presents)?
4. **Tone of voice** — rigorous application of the standardised ToV principles in
   `../configs/default/tone-of-voice.yml`, overlaid by the brand's voice if any.
5. **The scored test battery** — runs the asset through the configurable,
   extensible tests in `../configs/tests/` (so-what / yawn / sniff, …) and
   aggregates a weighted verdict.

Judgment lives in the skills; the `nit` CLI does only mechanics (capture, config
loading/validation, score aggregation).

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/nit/`, the `nit` CLI) — no judgment.

The `/nitpicker-studio` command (`commands/nitpicker-studio.md`) orchestrates them
end to end.

| Skill | Drives | Does |
|-------|--------|------|
| `review-intake`     | `nit new …`            | set up the review session: target + brief + brand + ICP, locked into `version.json` |
| `visual-qa`         | `nit capture …`        | rasterise the target + critique against the design baselines / brand |
| `brief-fulfilment`  | (reads `inputs/brief.md`) | judge the asset as a fulfilment of the brief |
| `audience-fit`      | (reads `inputs/icp.md`)   | judge from the target audience / ICP perspective |
| `tone-of-voice`     | `nit config show`      | apply the standardised ToV baseline (+ brand overlay) rigorously |
| `apply-tests`       | `nit tests show …`     | score the asset through each configurable test |
| `verdict`           | `nit score …`          | consolidate scores → weighted verdict + `findings.md` |

## Configs (global, brand-agnostic)

The standards the nitpicker reviews against live at the **studios repo root**,
shared across studios (see [`../configs/README.md`](../configs/README.md)):

- `../configs/default/` — baselines: `tone-of-voice.yml`, `design-principles.yml`,
  `review-policy.yml` (verdict bands + weights). Brand-agnostic; a brand's own
  `tone-of-voice.md` overlays the ToV baseline.
- `../configs/tests/` — the extensible scored battery. Each `<name>.yaml` poses a
  question, defines a 1–5 scale with labelled anchors, lists scoring criteria, and
  declares weight + thresholds. Add a file → the nitpicker discovers it
  (`nit tests list`). Validated against `scripts/nit/schemas/test.schema.json`.

The configs are root-level (not studio-owned) on purpose: the standard is
**single-sourced and shared** so other studios' own QA can agree with the
nitpicker's.

## CLI

```
nit tests list | show --test SLUG | validate --test SLUG
nit config show [--brand SLUG]
nit new --name NAME --target PATH_OR_URL [--brief PATH] [--brand SLUG] [--icp PATH]
nit capture --session PATH [--bump patch|minor|major]
nit score --session PATH [--version X.Y.Z]
nit status --session PATH [--set draft|reviewing|reviewed|signed-off|rejected]
nit doctor
```

- Entry point: `nit = nit.cli:main` (`pyproject.toml [project.scripts]`).
- `capture` advances the version and rasterises the target into
  `capture/v<ver>/` (PDF→PNG via pypdfium2; URL/HTML via playwright→else
  wkhtmltoimage; PPTX→PDF→PNG via LibreOffice; images copied; text targets need
  no capture).
- `score` reads `review/v<ver>/scores.yml` (written by the apply-tests/verdict
  skills), normalises + weights every test and dimension per
  `configs/default/review-policy.yml`, enforces gate items (e.g. the sniff test),
  and writes `review/v<ver>/scorecard.json` with the verdict.

## Data root (outside the repo)

`CONTEXT_ROOT = ~/context/studios/nitpicker/<name>/` (the same override chain as
the other studios: `$STUDIOS_PROJECT_ROOT`, else a walk-up `.wip/config.yml`,
else this default).

```
~/context/studios/nitpicker/<name>/
  inputs/
    target/          # the asset under review (file copied in, or url.txt)
    brief.md         # the brief it must fulfil
    icp.md           # the target audience / ICP profile
  capture/v<ver>/    # rasterised pages / screenshots of the target
  review/v<ver>/
    scores.yml       # per-test + per-dimension scores (written by the skills)
    findings.md      # the narrative critique (written by the skills)
    scorecard.json   # computed weighted aggregate + verdict (written by `nit score`)
  version.json       # { session, target, target_kind, brand, status, created, current, history[] }
```

One target × one review per session. Re-reviewing a revised asset is a new
version (`nit capture --bump`) in the same session.

## Code map (`scripts/nit/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `nit <command>`; subcommands mirror the skills |
| `config.py` | Resolve the global baselines + review policy; brand voice overlay |
| `tests.py` | Load/validate test definitions; deterministic score aggregation → verdict |
| `session.py` | Review sessions + semver versioning + status; records target/brief/brand/ICP |
| `capture.py` | Rasterise the target (PDF/PPTX/HTML/URL/image) for visual QA |
| `deps.py` | Detect capture backends; backs `nit doctor` + capture skip-hints |
| `schemas/test.schema.json` | JSON Schema for a scored-test definition |

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/nit/` — this is what
  makes the review behave identically across invocation modes.
- The nitpicker **reviews; it never edits the asset.** Findings + a verdict are
  the output. Fixes are the producing studio's job (design / messaging), then a
  re-review.
- Don't re-flag what a producing studio's deterministic lint already enforces
  (counts/limits); focus on judgment.
- Don't invent findings to look thorough. If it's clean, say so. Verdict
  severities: **critical** (must fix) / **significant** / **minor**.
- Configs are global and brand-agnostic. Anything brand-specific belongs in the
  shared brand store, not in `../configs/`.
