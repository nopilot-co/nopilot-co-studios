# Nitpicker Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). Same invariant:
its **skills are the single source of processing behavior** across all invocation
modes. The nitpicker **reviews an asset** — visual/format QA, brief fulfilment,
audience/ICP fit, standardised tone-of-voice, and a configurable scored test
battery — and returns a **weighted verdict**. It reviews; it does not produce or
edit. Full design notes: [`CLAUDE.md`](CLAUDE.md).

Packaged as the Claude Code plugin **`nitpicker-studio`**. `./install.sh` creates
`.venv` and installs the `nit` CLI. Review-only and mostly pure-Python; the
optional `[capture]` extra (pypdfium2 / pillow / playwright) rasterises a target
for visual QA. `nit doctor` reports capture-tool status.

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the review judgment, the contract:
  `review-intake` → `visual-qa` → `brief-fulfilment` → `audience-fit` →
  `tone-of-voice` → `apply-tests` → `verdict`.
- **Deterministic glue** (`scripts/nit/`, the `nit` CLI) — capture, config
  loading/validation, score aggregation. No judgment.

## What it reviews against

The standards are **global and brand-agnostic**, single-sourced at the studios
repo root (so other studios' QA can agree with the nitpicker's):

- `../configs/default/` — baselines: `tone-of-voice.yml`, `design-principles.yml`,
  `review-policy.yml`. A brand's own `tone-of-voice.md` overlays the ToV baseline.
- `../configs/tests/` — the extensible scored battery:
  - `the-so-what-test` — relevant, exciting, impactful? Will it change the
    reader's mind?
  - `the-yawn-test` — interesting, readable, engaging?
  - `the-sniff-test` — credible, authoritative, believable? *(a gate — failing
    it fails the asset)*

  Add a `<name>.yaml` to extend the battery; the nitpicker discovers it
  (`nit tests list`).

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

## Workflow

1. `review-intake` → `nit new` records the target + brief + brand + ICP.
2. `nit capture` rasterises the target (PDF/PPTX/HTML/URL/image).
3. The critique skills score visual QA, brief fulfilment, audience fit, and tone
   of voice; `apply-tests` scores the test battery.
4. `verdict` writes `review/v<ver>/scores.yml` + `findings.md`; `nit score`
   aggregates them into `scorecard.json` with a `pass | revise | fail` verdict.

## Data root (outside the repo)

`~/context/studios/nitpicker/<name>/` — `inputs/` (target + brief + icp),
`capture/v<ver>/`, `review/v<ver>/` (`scores.yml`, `findings.md`,
`scorecard.json`), `version.json`. One target × one review per session;
re-review a revised asset as a new version.
