# Analytics Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). The
studios invariant applies: skills are the single source of processing
behavior across invocation modes.

Packaged as the Claude Code plugin **`analytics-studio`**
(`.claude-plugin/plugin.json`). `./install.sh` creates `.venv` and installs
the `analytics` CLI. Pure-Python; no native deps.

## What it does

One capability today:

- **`analyse-data`** — given a supplied dataset (path or URL) + an
  analytical brief, produce a structured analysis: descriptive
  statistics, identified patterns, named insights (severity +
  confidence), recommendations.

Caller-supplied-JSON materialiser pattern: the model produces the
structured analysis; the CLI validates the schema, stamps provenance,
and derives **rollups** (insight count by severity, insight count by
confidence, recommendation count, pattern count, sample size).

## Data root (outside the repo)

`ANALYTICS_ROOT = ~/context/studios/analytics/<engagement>/`. Same
override chain as the other studios.

```
~/context/studios/analytics/<engagement>/
  _analysis.yml      # structured analysis + rollups + provenance
  brief.md           # optional copy of the analytical brief
  viz/               # optional viz specs handed to design via the planner
  version.json       # { engagement, status, created, current, history[] }
```

`_analysis.yml` is validated against
`scripts/analytics/schemas/analysis.schema.json`. Slugs are kebab-case.

## CLI

```
analytics doctor

analytics analysis new          --engagement SLUG [--brief PATH]
analytics analysis materialise  --engagement SLUG --analysis-json PATH [--bump patch|minor|major]
analytics analysis show         --engagement SLUG
analytics analysis list

analytics status                --engagement SLUG [--set draft|drafting|reviewing|approved]
```

- Entry point: `analytics = analytics.cli:main`.

## Code map (`scripts/analytics/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point |
| `store.py` | Scaffold + read/write/validate the per-engagement store |
| `analysis.py` | Materialise the caller-supplied analysis; derive insight + pattern rollups |
| `deps.py` | `analytics doctor` |
| `schemas/analysis.schema.json` | JSON Schema for the analysis |

## Conventions

- Judgment lives in the skill; mechanics in `scripts/analytics/`.
- Caller-supplied JSON is the contract — no model calls live in this
  package.
- Cite evidence. Each pattern names the dataset slice; each insight
  names the supporting patterns; each recommendation names an owner.
- Confidence is per-item, not aggregated. The rollup surfaces the
  distribution.
- Viz specs, not pixels — hand structured intent (chart type + fields
  + caption) to design via the planner.
