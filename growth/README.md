# Growth/BD Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)).

Two capabilities:

- **`generate-leads`** — qualified lead list (fit scores from
  caller-supplied ICP + criteria).
- **`map-market`** — segments + competitors + positioning from supplied
  research.

Caller-supplied-JSON materialiser pattern. Pure-Python; no native deps.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry: `/growth-studio`.

## Quickstart

```bash
./install.sh
.venv/bin/growth doctor

.venv/bin/growth leads new --engagement demo
.venv/bin/growth leads materialise --engagement demo --leads-json /tmp/leads.json

.venv/bin/growth market new --engagement demo
.venv/bin/growth market materialise --engagement demo --market-json /tmp/market.json
```

## Pairs with

- **Principal** — uses leads + market map for client / market mapping.
- **audience** — share the ICP slug.
- **messaging** — turns approved leads into outreach (L3).
