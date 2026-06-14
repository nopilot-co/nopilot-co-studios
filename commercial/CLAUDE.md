# Commercial Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the studios
model and the three invocation modes). The studios invariant applies: **this
studio's skills are the single source of processing behavior** — the same skills
run whether invoked as a local plugin, via CLI from a server, or programmatically
server-side. Only the trigger and LLM host change.

Packaged as the Claude Code plugin **`commercial-studio`** (`.claude-plugin/plugin.json`).
`./install.sh` creates `.venv` and installs the `commercial` CLI. Pure-Python;
it reuses the nitpicker engine for scoring (shells out to `nit aggregate`), so
the only real dependency is the `nit` CLI — `commercial doctor` reports it.

## What it does

The commercial studio supplies the *commercial truth* the Principal needs to
shape an engagement and the Producer needs to gate a deal before commitment.
Two capabilities, separable but related:

1. **`check-commercials`** (review-class — beancounter). Deterministic
   validation of a deal against the org's **rate cards**, **margin floor**, and
   **skill-set ratios**. Reuses the nitpicker engine for the verdict so a
   commercial verdict reads identically to any other gate (objective review or
   reader-fit). A `critical` failure on a rate-card or margin floor gate blocks
   L2 sign-off (Bible §6).
2. **`assess-commercial-value`** (research + judgment — commercial officer).
   Synthesise a value-based opportunity sizing from cited client financial
   research, declared spend capacity, and addressable market. The Principal
   uses this output for value-based scoping. Caller-supplied-JSON
   materialiser: the model produces the structured analysis, the CLI
   materialises it with provenance.

Judgment lives in the skills; the `commercial` CLI does only mechanics (store
scaffolding, schema validation, deterministic check evaluation, session
versioning, and handing scoring to the nitpicker engine).

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/commercial/`, the `commercial` CLI) — no
  judgment.

The `/commercial-studio` command (`commands/commercial-studio.md`) orchestrates
them.

| Skill | Drives | Does |
|-------|--------|------|
| `check-commercials`         | `commercial check new` → `commercial check score` | scaffold a per-deal session, evaluate the deterministic checks, hand to `nit aggregate` for the verdict |
| `assess-commercial-value`   | `commercial value assess`                         | materialise a caller-supplied structured assessment (financial profile + spend capacity + addressable market + value sizing) into the client store |

## Reuses the nitpicker scoring engine

Check-commercials scoring is **not** re-implemented. The CLI evaluates each
deterministic check (rate-card compliance, margin floor, skill-set ratios) into
a score, writes `scores.yml`, then shells out to
`nit aggregate --scores <scores.yml> --tests-from <checks.yml>`
(`scripts/commercial/nit_bridge.py`), which runs the nitpicker's single-sourced
aggregation (`nit.tests.aggregate`) against the same
`../configs/default/review-policy.yml`. Critical checks are passed as gates.
So a commercial verdict reads identically to a nitpicker verdict, and the
verdict math has exactly one home (the nitpicker engine).

## Data root (outside the repo)

The commercial store is **studios-level** and shared. Org policy is one source
of truth; client research is reusable across deals. Same override chain as the
other studios (`$STUDIOS_DOCKET_ROOT`, `$STUDIOS_PROJECT_ROOT`,
`.wip/config.yml`, else the default).

`COMMERCIAL_ROOT = ~/context/studios/commercial/`

```
~/context/studios/commercial/
  rate-card.yml          # org-wide skill → $/hr or $/day rate card
  pricing-policy.yml     # margin floor, skill-set ratios, markup defaults
  configs/
    checks/              # extensible scored battery (rate-card / margin / ratios)
  clients/<slug>/
    _client.yml          # financials, spend capacity, addressable market, segment
    research/
      <source>.md        # cited reviews of supplied sources (skill-written)
      sources/           # raw filed sources
    assessment.yml       # the materialised value-based opportunity sizing
  sessions/<deal-slug>/  # per-deal check-commercials sessions
    inputs/
      deal.yml           # the deal: roles + rates + days + total
      brief.md           # what the deal is for (a sentence)
    review/v<ver>/
      scores.yml         # per-check scores (written by the skill / CLI)
      findings.md        # narrative critique (written by the skill)
      scorecard.json     # weighted aggregate + verdict (written by `commercial check score`)
      strengthening-areas.md
    version.json         # { deal, status, created, current, history[] }
```

`rate-card.yml` / `pricing-policy.yml` / `_client.yml` are validated against
schemas in `scripts/commercial/schemas/`. Slugs and session names are
kebab-case.

## Configs (the deterministic check rubric)

Checks live as a small, extensible YAML set in `configs/checks/`, in the same
shape the nitpicker uses for its tests:

| Check | Gate? | Question |
|---|---|---|
| `rate-card-compliance` | yes | Are all role rates ≥ rate-card floor? |
| `margin-floor`         | yes | Does the deal clear the org's margin floor? |
| `ratio-mix`            | no  | Are skill-mix ratios within policy bands (e.g. ≤30% leadership of total days)? |

A check is one scored test with a 1–5 scale and labelled anchors. Add a YAML
file to `configs/checks/` → it's discoverable
(`commercial checks list`). Same shape as the nitpicker's
`../configs/tests/`. Brand-agnostic and org-wide.

## CLI

```
commercial doctor

commercial policy init [--from <template>]
commercial policy show
commercial rate-card show
commercial rate-card validate

commercial client new --client SLUG [--name NAME]
commercial client show --client SLUG
commercial client list

commercial research add --client SLUG --source PATH_OR_URL --kind transcript|doc|url

commercial checks list | show --check SLUG

commercial check new   --deal-slug SLUG --deal-file PATH [--brief PATH]
commercial check score --deal-slug SLUG [--version X.Y.Z]
commercial check status --deal-slug SLUG [--set draft|reviewing|reviewed|blocked|signed-off]

commercial value assess --client SLUG --assessment-json PATH
```

- Entry point: `commercial = commercial.cli:main` (`pyproject.toml`).
- `check score` evaluates each deterministic check from the deal + rate card +
  policy, writes per-check scores, then runs `nit aggregate` to produce the
  weighted verdict.
- `value assess` materialises the caller-supplied assessment JSON (mirror of
  `theme-entity`/`source-summarise` materialiser pattern in the tools tier).

## Code map (`scripts/commercial/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `commercial <command>`; subcommands mirror the skills |
| `store.py` | Scaffold/read/write/validate the shared store (rate card, pricing policy, client model) |
| `checks.py` | Deterministic evaluation of each check (rate-card compliance, margin floor, ratio mix); converts to per-test scores |
| `value.py` | Materialise the caller-supplied assessment JSON into `<client>/assessment.yml` + provenance |
| `session.py` | Per-deal check sessions + versioning + status |
| `nit_bridge.py` | Reuse the nitpicker engine via `nit aggregate` (CLI boundary) |
| `deps.py` | `commercial doctor` — is `nit` reachable? |
| `schemas/*.json` | JSON Schemas for rate card / pricing policy / client / deal |

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/commercial/` — this
  is what makes the studio behave identically across invocation modes.
- The studio **validates + assesses; it never agrees prices externally** —
  that's L3 (Principal → user → external).
- Scoring is single-sourced in the nitpicker engine. Don't re-implement the
  verdict math.
- The Commercial store is studios-level and shared. Anything brand- or
  client-specific lives under `clients/<slug>/`; org-wide truth (rate card,
  pricing policy) lives at the root.
- An assessment is **caller-supplied**: the CLI materialises structured JSON.
  No model calls live in this package.
