# Architecture Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). Same
invariant: its **skills are the single source of processing behavior** across
all invocation modes.

The architecture studio produces the *how-it-fits-together* truth for an
engagement. One capability today:

- **`design-architecture`** — turn an engagement brief + system context into
  a structured spec: systems, data flows, integration points, and ADR-style
  decision records. Optional diagram render via the design studio.

Caller-supplied-JSON materialiser pattern: the model produces the spec; the
CLI validates the schema, runs invariant checks, stamps provenance.

Packaged as the Claude Code plugin **`architecture-studio`**
(`.claude-plugin/plugin.json`). Install with `./install.sh` — pure-Python; no
hard deps. Rendering diagrams optionally uses the design studio (`arch
render`) and degrades cleanly when design isn't installed.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry:
`/architecture-studio`. Registered in the root
[`studios.yml`](../studios.yml).

## Quickstart

```bash
./install.sh
.venv/bin/arch doctor

.venv/bin/arch spec new --engagement demo
$EDITOR  # write the structured spec JSON to /tmp/spec.json
.venv/bin/arch spec materialise --engagement demo --spec-json /tmp/spec.json

.venv/bin/arch adr add --engagement demo \
  --title "event bus over REST between API and worker" --status accepted \
  --context "..." --decision "..." --consequences "..."
.venv/bin/arch adr list --engagement demo

# (optional, if the design studio is installed)
.venv/bin/arch render --engagement demo
```

## Pairs with

- **Delivery** — the spec's systems / integrations shape the delivery plan's
  swimlanes + dependencies; integration risks flow into the RAID register.
- **Design** — chained for diagram render via `studio render-asset`.
- **Principal / Producer** — the spec is part of the engagement's
  evidence base; ADRs link from the Bible §7 decision-record convention.
