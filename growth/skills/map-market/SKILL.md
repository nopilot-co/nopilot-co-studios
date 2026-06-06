---
name: map-market
description: Produce a structured market map (segments + competitors + positioning) from caller-supplied research. Each segment has size + characteristics; each competitor has segment + positioning quadrant; positioning has named axes and our position. Caller-supplied-JSON materialiser. Use when the Principal needs market truth for value-based scoping, when commercial needs addressable market for opportunity sizing, or when messaging needs differentiation framing.
---

# map-market

You are the **market mapper**: synthesise supplied research into a
structured market map. The CLI materialises your structured payload.

## Steps

1. `growth market new --engagement <slug>` — scaffold the store.
2. Read the supplied research (typically filed via the context studio).
3. Produce a structured JSON payload conforming to `market.schema.json`:
   - `segments: [{id, name, size, characteristics}]`
   - `competitors: [{id, name, segment, positioning_quadrant}]`
   - `positioning: { axes: [a, b], our_position: [x, y] }`
4. `growth market materialise --engagement <slug> --market-json <path>`
5. Surface rollups: segment count, competitor count, positioning
   quadrant distribution. Flag where the data is thin.

## Conventions

- **Segments before competitors.** A competitor without a segment is
  positioned against nothing.
- **Positioning is a frame, not a fact.** Name the axes; let the
  Principal challenge them.
- **Cite research.** Every segment claim cites the source filed in the
  context store.
- **Caller-supplied JSON is the contract.**
