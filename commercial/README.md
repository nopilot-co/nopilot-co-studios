# Commercial Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)). Same
invariant: its **skills are the single source of processing behavior** across
all invocation modes.

The commercial studio supplies the commercial truth the Principal needs to
shape an engagement and the Producer needs to gate a deal before commitment.
Two capabilities:

- **`check-commercials`** (review-class — beancounter). Deterministic
  validation of a deal against rate cards, margin floor, and skill-set ratios.
  Reuses the nitpicker engine for the verdict — so a commercial verdict reads
  identically to any other gate.
- **`assess-commercial-value`** (research + judgment — commercial officer).
  Value-based opportunity sizing from cited client research, spend capacity,
  and addressable market. Caller-supplied-JSON materialiser pattern.

Packaged as the Claude Code plugin **`commercial-studio`**
(`.claude-plugin/plugin.json`). Install with `./install.sh` — pure-Python;
the only hard dependency is the nitpicker `nit` CLI (verdict aggregation),
reported by `commercial doctor`.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry:
`/commercial-studio`. Registered in the root [`studios.yml`](../studios.yml).

## Quickstart

```bash
./install.sh
.venv/bin/commercial doctor

# org-wide policy + rate card (idempotent; copies a template you then edit)
.venv/bin/commercial policy init
.venv/bin/commercial policy show

# a client
.venv/bin/commercial client new --client acme
.venv/bin/commercial research add --client acme --source path/to/earnings.pdf --kind doc

# size the value (caller produces the JSON; CLI materialises it)
.venv/bin/commercial value assess --client acme --assessment-json path/to/assessment.json

# gate a deal
.venv/bin/commercial check new --deal-slug acme-q3 --deal-file path/to/deal.yml
.venv/bin/commercial check score --deal-slug acme-q3
```

## Pairs with

- **Principal** — for value-based scoping (L2 decisions, Bible §6) and for
  walking the verdict back to the user.
- **Producer** — for gating any deal-tied artefact (proposal, SoW) before
  external delivery (L3).
- **Nitpicker** — verdict aggregation reuse (`nit aggregate`).
