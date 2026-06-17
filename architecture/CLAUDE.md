# Architecture Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the
studios model). The studios invariant applies: **this studio's skills are
the single source of processing behavior** across all invocation modes.

Packaged as the Claude Code plugin **`architecture-studio`**
(`.claude-plugin/plugin.json`). `./install.sh` creates `.venv` and installs
the `arch` CLI. Pure-Python; the only optional integration is the design
studio's `studio render-asset` (for diagram render), reported by
`arch doctor`.

## What it does

Produces the *how-it-fits-together* truth for an engagement. One capability
today:

- **`design-architecture`** — a structured architecture spec:
  - **systems** (role, owner, technology, status, criticality),
  - **data flows** (between systems, direction, frequency, payload, SLA),
  - **integrations** (technology, contract, auth, error handling),
  - **ADR-style decision records** for load-bearing choices,
  - optional **diagrams** rendered from the spec via the design studio.

Caller-supplied-JSON materialiser pattern: the model produces the spec; the
CLI validates the schema, runs invariant checks (every flow's endpoints
must exist as systems; every integration must reference an existing flow),
stamps provenance.

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment / contract.
- **Deterministic glue** (`scripts/architecture/`, the `arch` CLI) — no
  judgment.

| Skill | Drives | Does |
|-------|--------|------|
| `design-architecture` | `arch spec new` → `arch spec materialise` → `arch adr add` → `arch render` | scaffold store, materialise spec, run invariants, maintain ADRs, optional render via design |

## Data root (outside the repo)

`ARCH_ROOT = ~/context/studios/architecture/`. Same override chain as
the other studios (`$STUDIOS_DOCKET_ROOT`, etc.).

```
~/context/studios/architecture/<engagement>/
  _architecture.yml   # systems + data_flows + integrations (with rollups + provenance)
  adrs/
    001-<slug>.md     # ADR-style: status / context / decision / consequences / alternatives
    002-<slug>.md
  brief.md            # optional copy of the shaped engagement brief
  version.json        # { engagement, status, created, current, history[] }
  render/v<ver>/      # rendered diagrams (when --render runs the design studio)
```

`_architecture.yml` is validated against
`scripts/architecture/schemas/architecture.schema.json`; ADRs against
`adr.schema.json`. Slugs and ADR ids are kebab-case.

## CLI

```
arch doctor

arch spec new          --engagement SLUG [--brief PATH]
arch spec materialise  --engagement SLUG --spec-json PATH [--bump patch|minor|major]
arch spec show         --engagement SLUG
arch spec validate     --engagement SLUG   # re-run schema + invariants

arch adr add           --engagement SLUG --title TXT [--status proposed|accepted|deprecated|superseded] [--context TXT] [--decision TXT] [--consequences TXT]
arch adr show          --engagement SLUG [--id ADR-NNN]
arch adr list          --engagement SLUG

arch render            --engagement SLUG [--format pdf|html|svg]    # via design studio (degrades cleanly)

arch status            --engagement SLUG [--set draft|reviewing|approved|implemented]
```

- Entry point: `arch = architecture.cli:main` (`pyproject.toml`).
- `spec materialise` validates against the schema then runs the invariants
  in `architecture.invariants` (every flow's `from`/`to` matches a system
  id; every integration's `flow` matches a flow id; system ids and flow ids
  are unique).
- `render` shells out to `studio render-asset` over the CLI boundary
  (`scripts/architecture/design_bridge.py`); the design studio renders one
  diagram per cohesive subsystem from the spec.

## Code map (`scripts/architecture/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `arch <command>` |
| `store.py` | Scaffold + read/write/validate the per-engagement store |
| `spec.py` | Materialise the caller-supplied spec; run invariant checks |
| `invariants.py` | Deterministic invariant rules (referential integrity) |
| `adr.py` | First-class CRUD on ADR records |
| `design_bridge.py` | Render diagrams via `studio render-asset` (CLI boundary) |
| `deps.py` | `arch doctor` — design-CLI reachability |
| `schemas/{architecture,adr}.schema.json` | JSON Schemas |

## Conventions

- Judgment lives in the skill; mechanics in `scripts/architecture/`.
- Specs are caller-supplied JSON. No model calls live in this package.
- ADRs are first-class. Don't bury decisions in the spec — they live in
  `adrs/NNN-<slug>.md`.
- The studio **specifies and surfaces**; it never deploys. Implementation
  is the cast's job, downstream.
- Diagrams render from the spec; never hand-edited.
- Data flows and system hierarchies render via the design studio's visualisation
  catalogue (`design/skills/viz-process-flow`, `viz-hierarchy`), which also ships
  their underlying data as a **normalised CSV** in the docket for editors like
  nopilot.co (see design `formats/README.md` → *Data export*).
