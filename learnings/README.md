# Learnings

Append-only, in-repo record of **how the Studios plugin itself could be
improved** — captured at the close of each run by the
[`reflect`](../skills/reflect/SKILL.md) skill via the `learnings` CLI. This is
the plugin improving the plugin; client deliverables are judged elsewhere
(nitpicker / audience / visual-qa).

It ships with the clone (unlike `.claude/`, which is git-ignored), so learnings
are PR-reviewable and travel with the plugin. High-signal items are **promoted**
to a GitHub issue or an ADR (`docs/architecture/DECISIONS.md`); this directory is
the cheap capture net, the issue/ADR is the deliberate follow-up.

## Layout

```
learnings/
  README.md                               # this file
  <YYYY>/<YYYY-MM-DD>-<studio>-<slug>.md   # one file per learning, append-only
```

One file per learning. The filename is date-prefixed so the directory sorts
chronologically and never collides. Don't hand-edit — use the CLI.

## Frontmatter schema

Validated against `../scripts/learnings/schemas/learning.schema.json`.

```yaml
---
id: 2026-06-17-design-render-needed-a-manual   # == filename stem
date: 2026-06-17
studio: design            # studio slug · "cross" for orchestration · "none" for a no-learning record
engagement: acme-pitch    # engagement/session slug, or "" if standalone
category: cli             # skill | cli | format | asset | orchestration | docs | none
severity: medium          # low | medium | high
title: render needed a manual outputs/ mkdir
proposed-change: have `studio render` create the data dir before emitting
status: open              # open | triaged | promoted | wontfix | fixed
ref: ''                   # set on promotion → "#123" or "ADR-006"
---
```

Body sections: **What happened** / **Why it matters (tool, not deliverable)** /
**Proposed change** / **Promotion** (filled on promotion).

## Lifecycle

`open` → `triaged` → `promoted` | `wontfix` | `fixed`.

Only `status` (and the `ref` / Promotion section on promotion) may change after
a learning is written — everything else is immutable. A `category: none` record
is a real, committed file: the auditable "we reflected and there was nothing
this run" satisfier.

## CLI

```
learnings add     --studio S --category C --severity SEV --title "…" --proposed-change "…" [--engagement E] [--body "…"]
learnings none    --engagement E --reason "…"
learnings list    [--status open] [--studio S] [--category C]
learnings show    <id>
learnings status  <id> --set triaged|promoted|wontfix|fixed [--ref "#123"]
learnings promote <id> --issue          # builds a `gh issue create` command (dry-run; outward action stays manual)
learnings doctor
```

Install: `pip install -e .` from the repo root (the `studios-orchestrators`
package ships `learnings` alongside `planner` and `engagement`).

## Enforcement

A soft Stop hook (`../hooks/reflect-gate.sh`, shipped via `../hooks/hooks.json`)
nudges once per session if a studio run logged no learning. It is non-blocking
and satisfied by either `learnings add` or `learnings none`.
