# Delivery Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). Same
invariant: its **skills are the single source of processing behavior** across
all invocation modes.

The delivery studio produces the *how-it-ships* truth the Producer needs to
sequence work and the Principal needs to commit to a timeline. One
capability today:

- **`plan-delivery`** — turn a shaped engagement brief into a structured
  plan: swimlanes keyed to the cast, sequenced phases with entry/exit
  criteria, per-phase resourcing + contingency, and a first-class RAID
  register (Risks / Assumptions / Issues / Dependencies).

Caller-supplied-JSON materialiser pattern: the model produces the structured
plan; the CLI validates the schema, stamps provenance, and derives rollups.

Packaged as the Claude Code plugin **`delivery-studio`**
(`.claude-plugin/plugin.json`). Install with `./install.sh` — pure-Python; no
native deps. Costing the resourcing optionally uses the commercial studio's
rate-card (`delivery plan cost`), but degrades cleanly if commercial isn't
installed.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry:
`/delivery-studio`. Registered in the root [`studios.yml`](../studios.yml).

## Quickstart

```bash
./install.sh
.venv/bin/delivery doctor

.venv/bin/delivery plan new --engagement demo
$EDITOR  # write the structured plan JSON to /tmp/plan.json
.venv/bin/delivery plan materialise --engagement demo --plan-json /tmp/plan.json
.venv/bin/delivery plan show --engagement demo

.venv/bin/delivery raid add --engagement demo --kind risk \
  --title "vendor outage during cutover week" --severity high --owner principal
.venv/bin/delivery raid show --engagement demo
```

## Pairs with

- **Principal** — for L2 commitment sign-off (dates / resources / milestones).
- **Producer** — sequences jobs against the swimlanes / phases.
- **Commercial** — optional cost rollups via the rate-card.
