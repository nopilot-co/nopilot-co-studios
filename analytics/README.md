# Analytics Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)).

One capability today:

- **`analyse-data`** — turn a supplied dataset + brief into a structured
  analysis (descriptive statistics, patterns, insights, recommendations)
  with deterministic rollups.

Caller-supplied-JSON materialiser pattern. Pure-Python; no native deps.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry: `/analytics-studio`.
Registered in the root [`studios.yml`](../studios.yml).

## Quickstart

```bash
./install.sh
.venv/bin/analytics doctor

.venv/bin/analytics analysis new --engagement demo
# model produces analysis JSON to /tmp/analysis.json
.venv/bin/analytics analysis materialise --engagement demo --analysis-json /tmp/analysis.json
.venv/bin/analytics analysis show --engagement demo
```

## Pairs with

- **Principal** — grounds value claims with cited insights.
- **delivery** — references recommendations for follow-up phases.
- **design** (via planner) — renders viz specs from the analysis.
