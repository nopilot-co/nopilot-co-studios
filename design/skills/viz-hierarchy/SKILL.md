---
name: viz-hierarchy
description: How to execute hierarchy & org-chart visualisations in the design studio — the nested `{root, children}` syntax, the tree engine that renders them, and the normalised nodes/edges CSV they ship into the docket for data editors like nopilot.co. Use when composing source.md with a hierarchy or org chart.
---

# viz-hierarchy — hierarchy · org

Top-down trees: strategy breakdowns, org charts, taxonomies.

## When to use which
- **hierarchy** — any parent/child breakdown (pillars → initiatives).
- **org** — people / teams reporting lines (same engine, org semantics).

## Authoring syntax
```markdown
::: hierarchy
root: Strategy
children:
  - root: Pillar A
    children: [Initiative 1, Initiative 2]
  - Pillar B
:::
```
A node is either a leaf string or a `{root, children}` mapping — mix freely.

## Engine & tool
`studio.diagrams` (`_flatten_tree`) → Mermaid `flowchart TD` (HTML) / Typst
`fletcher` tree (PDF); PPTX native shapes. Brand-tokenised. **Status: live.**

## Normalised CSV (shipped to the docket)
Writes `<viz-id>.nodes.csv` + `<viz-id>.edges.csv` under `outputs/<session>/data/`,
recorded in `version.json`'s `data[]`:
```
# nodes
viz_id,node_id,label,depth,parent
06-hierarchy,n0,Strategy,0,
06-hierarchy,n1,Pillar A,1,n0
# edges
viz_id,source,target
06-hierarchy,n0,n1
```
`parent` is derived from the edges for editor convenience. **nopilot.co** edits
these directly. `hierarchy` and `org` share the schema.

## Cross-studio sources
**architecture** (system breakdowns), **delivery** (workstream trees). Author
here so the structure ships as editable CSV.

## Status
Live. CSV sidecar: always (nodes + edges).
