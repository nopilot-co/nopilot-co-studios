---
name: viz-process-flow
description: How to execute process & flow visualisations in the design studio — flow, process, timeline, swimlane, and decision-tree — their `::: ` authoring syntax, which engine renders them (and which are not-yet-built), and the normalised nodes/edges CSV each ships into the docket for data editors like nopilot.co. Use when composing source.md with a process, flow, timeline, swimlane, or decision tree.
---

# viz-process-flow — flow · process · timeline · swimlane · decision-tree

Sequence, hand-offs, and branching. Authored as structured YAML fenced divs.

## When to use which
- **flow** — a simple ordered chain of steps.
- **process** — a flow whose steps are numbered phases.
- **timeline** — events against a time axis.
- **swimlane** — a flow whose steps are grouped into lanes (roles / teams) — the
  delivery studio's plan view.
- **decision-tree** — branching decisions with labelled conditions and outcomes.

## Authoring syntax
```markdown
::: flow
nodes: [Brief, Plan, Render, Review]
:::

::: timeline
events:
  - {at: Q1, label: Kickoff}
  - {at: Q2, label: Beta}
:::

::: swimlane
lanes:
  - {lane: Customer, nodes: [Request, Approve]}
  - {lane: Ops, nodes: [Fulfil, Ship]}
edges:                       # optional; default = sequential
  - {from: Request, to: Fulfil, label: handoff}
:::

::: decision-tree
root: Lead qualified?
children:
  - {condition: "yes", root: Send proposal}
  - {condition: "no", root: Nurture}
:::
```

## Engine & tool
- **flow / process / timeline** — `studio.diagrams` → Mermaid (HTML) / Typst
  `fletcher` (PDF), brand-tokenised; PPTX native shapes. **Live.**
- **swimlane / decision-tree** — `studio.frameworks` → brand-styled matplotlib
  SVG (HTML inline / PDF via Typst `#image()`): swimlane draws lanes as bands
  with sequential arrows; decision-tree draws decision/outcome boxes with
  condition-labelled edges. **Live (HTML + PDF; PPTX-native is a follow-up).**

## Normalised CSV (shipped to the docket)
Each diagram writes two files — `<viz-id>.nodes.csv` + `<viz-id>.edges.csv` —
under `outputs/<session>/data/`, recorded in `version.json`'s `data[]`:

| type | nodes columns | edges columns |
|------|---------------|---------------|
| flow / process | `viz_id, node_id, label, order` | `viz_id, source, target, label` |
| timeline | `viz_id, node_id, label, order, at` | `viz_id, source, target, label` |
| swimlane | `viz_id, node_id, label, order, lane` | `viz_id, source, target, label` |
| decision-tree | `viz_id, node_id, label, depth, kind` | `viz_id, source, target, condition` |

A data editor (**nopilot.co**) edits nodes/edges directly. The CSV is emitted
from the authored YAML on every export, including the not-yet-built types.

## Cross-studio sources
The **delivery** studio plans swimlanes (cast-keyed phases); **architecture**
uses flows for data flows. Author them here so the data round-trips as CSV.

## Gotchas
- `swimlane` / `decision-tree` render via the **frameworks** engine (matplotlib),
  not Mermaid/fletcher — HTML + PDF today (no PPTX-native shapes yet).
- `decision-tree` is a `{root, children}` tree; each child's `condition` labels
  the edge into it. Leaves are `kind: outcome`, internal nodes `kind: decision`.

## Status
flow / process / timeline: live (diagrams engine). swimlane / decision-tree:
live (frameworks engine, HTML + PDF). CSV sidecar: always.
