# Growth/BD Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). The
studios invariant applies.

Packaged as the Claude Code plugin **`growth-studio`**
(`.claude-plugin/plugin.json`). `./install.sh` creates `.venv` and installs
the `growth` CLI. Pure-Python; no native deps.

## What it does

Two capabilities:

- **`generate-leads`** — produce a structured lead list from a
  caller-supplied ICP + criteria. Each lead has company, signals
  (matched + missing), fit (low/medium/high), owner, source.
- **`map-market`** — produce a structured market map (segments +
  competitors + positioning) from caller-supplied research.

Caller-supplied-JSON materialiser pattern. The CLI validates the
schemas, stamps provenance, and derives rollups (leads by fit / source
/ owner; segment + competitor counts; positioning quadrant
distribution).

## Data root

`GROWTH_ROOT = ~/context/studios/growth/<engagement>/`

```
~/context/studios/growth/<engagement>/
  _leads.yml       # structured lead list + rollups + provenance
  _market.yml      # structured market map + rollups + provenance
  version.json
```

## CLI

```
growth doctor

growth leads new          --engagement SLUG
growth leads materialise  --engagement SLUG --leads-json PATH [--bump …]
growth leads show         --engagement SLUG

growth market new         --engagement SLUG
growth market materialise --engagement SLUG --market-json PATH [--bump …]
growth market show        --engagement SLUG

growth status             --engagement SLUG [--set draft|approved|archived]
```

## Code map (`scripts/growth/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point |
| `store.py` | Scaffold + per-engagement store + schemas |
| `leads.py` | Materialise + lead rollups |
| `market.py` | Materialise + market rollups |
| `deps.py` | `growth doctor` |
| `schemas/{leads,market}.schema.json` | JSON Schemas |

## Conventions

- Generate + map; never outreach. Outreach is messaging + L3
  authorisation.
- ICP is the join key with audience; use the slug when present.
- Cite signals. No bare fit scores.
- Caller-supplied JSON is the contract.
