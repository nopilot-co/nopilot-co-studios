# Delivery Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the
studios model and the three invocation modes). The studios invariant applies:
**this studio's skills are the single source of processing behavior** — the
same skills run whether invoked as a local plugin, via CLI from a server, or
programmatically server-side.

Packaged as the Claude Code plugin **`delivery-studio`**
(`.claude-plugin/plugin.json`). `./install.sh` creates `.venv` and installs
the `delivery` CLI. Pure-Python; no native deps; no nitpicker reuse (delivery
**produces** a planning artefact rather than running a review-class gate).

## What it does

The delivery studio produces the *how-it-ships* truth the Producer needs to
sequence work and the Principal needs to commit to a timeline. One
capability today:

- **`plan-delivery`** — given a shaped engagement brief (objective, cast,
  scope, dates, constraints), produce a structured delivery plan:
  - **swimlanes** — parallel workstreams keyed to cast roles or studios.
  - **phasing** — sequenced phases with entry / exit criteria + dependencies.
  - **resourcing** — per-phase day-count by role. Can be costed via the
    commercial studio's rate-card (`delivery plan cost`).
  - **contingency** — per-phase buffer + an explicit contingency pool.
  - **RAID register** — first-class Risks / Assumptions / Issues /
    Dependencies (Bible §8 shape).

Caller-supplied-JSON materialiser pattern: the model produces the structured
plan; the CLI validates the schema, stamps provenance, and derives rollups
(total days, phase durations, contingency %, by-role totals, RAID counts).

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/delivery/`, the `delivery` CLI) — no
  judgment.

The `/delivery-studio` command (`commands/delivery-studio.md`) orchestrates
them.

| Skill | Drives | Does |
|-------|--------|------|
| `plan-delivery` | `delivery plan new` → `delivery plan materialise` | scaffold engagement store; materialise the caller-supplied plan; maintain RAID |

## Data root (outside the repo)

The delivery store is **per-engagement**, mirroring how the commercial /
audience studios scope work. Same override chain as the other studios
(`$STUDIOS_DOCKET_ROOT`, `$STUDIOS_PROJECT_ROOT`, `.wip/config.yml`, else the
default).

`DELIVERY_ROOT = ~/context/studios/delivery/`

```
~/context/studios/delivery/<engagement>/
  _plan.yml          # swimlanes + phases + resourcing + contingency + rollups + provenance
  raid.yml           # the live RAID register (Risks / Assumptions / Issues / Dependencies)
  brief.md           # optional — the shaped engagement brief (filed copy)
  version.json       # { engagement, status, created, current, history[] }
  sessions/<deliverable>/  # optional — per-deliverable carve-outs (a sub-plan focused on one artefact)
```

`_plan.yml` and `raid.yml` are validated against schemas in
`scripts/delivery/schemas/`. Slugs are kebab-case.

## CLI

```
delivery doctor

delivery plan new          --engagement SLUG [--brief PATH]
delivery plan materialise  --engagement SLUG --plan-json PATH [--bump patch|minor|major]
delivery plan show         --engagement SLUG
delivery plan cost         --engagement SLUG   # uses commercial rate-card if installed
delivery plan list

delivery raid add          --engagement SLUG --kind risk|assumption|issue|dependency --title TXT [--severity low|medium|high|critical] [--owner WHO] [--notes TXT]
delivery raid resolve      --engagement SLUG --id RAID-ID --resolution TXT
delivery raid show         --engagement SLUG [--kind risk|...]

delivery status            --engagement SLUG [--set draft|approved|active|delivered]
```

- Entry point: `delivery = delivery.cli:main` (`pyproject.toml`).
- `plan materialise` validates against `plan.schema.json`, stamps
  provenance + skill version, derives rollups (total days, phase durations,
  contingency %, by-role totals).
- `plan cost` walks each phase's `resourcing[]`, fetches the commercial
  rate-card over the CLI boundary (`shutil.which('commercial')`), and
  derives revenue + cost + margin per phase. Degrades cleanly if the
  commercial studio isn't installed.
- `raid add` allocates a stable id (`R-001`, `A-001`, `I-001`, `D-001`,
  …); `raid resolve` closes one with a resolution note. The full register
  is the source of truth.

## Code map (`scripts/delivery/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `delivery <command>` |
| `store.py` | Scaffold/read/write/validate the per-engagement store |
| `plan.py` | Materialise the caller-supplied plan; derive rollups |
| `raid.py` | First-class CRUD on the RAID register |
| `session.py` | Engagement versioning + status |
| `deps.py` | `delivery doctor` — reports commercial reachability (optional) |
| `schemas/{plan,raid}.schema.json` | JSON Schemas |

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/delivery/` —
  this is what makes the studio behave identically across invocation modes.
- The delivery studio **plans + surfaces**; it never commits dates or
  resources externally. Commitments are L3 — the Principal carries them
  to the user.
- RAID is first-class. Don't bury risks in prose. The Bible §8 shape
  applies (`needs: user|client|role`, `status: open|resolved`, etc.).
- Caller-supplied JSON is the contract. No model calls live in this
  package — judgment lives in the `plan-delivery` skill.
- One plan per engagement (v1). Per-deliverable carve-outs are sessions
  under the engagement.
- Swimlanes, phasing, and RAID render via the design studio's visualisation
  catalogue (`design/skills/viz-process-flow`, `viz-heatmap`); design ships their
  underlying data as a **normalised CSV** in the docket for editors like
  nopilot.co (see design `formats/README.md` → *Data export*).
