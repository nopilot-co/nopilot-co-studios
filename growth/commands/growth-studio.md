---
description: Generate qualified leads (with fit scores from ICP + criteria) and map the market (segments + competitors + positioning) for an engagement. Caller-supplied JSON; deterministic rollups.
argument-hint: <engagement slug> [leads from <path>] [market from <path>]
---

# /growth-studio

Orchestrate the growth studio: produce a structured lead list and / or a
structured market map for an engagement. The studio **generates and
maps**; it does not outreach (that's the messaging studio's job, with
explicit user authorisation per Bible §6 L3).

## Pipelines

### `generate-leads`

1. `growth leads new --engagement <slug>`
2. Produce a JSON payload conforming to `leads.schema.json`:
   `{ engagement, icp, criteria, leads: [{company, signals: {matched, missing}, fit: low|medium|high, owner, source, notes?}] }`
3. `growth leads materialise --engagement <slug> --leads-json <path>` —
   validates schema, stamps provenance, derives rollups (count by fit,
   count by source, count by owner).

### `map-market`

1. `growth market new --engagement <slug>`
2. Produce a JSON payload conforming to `market.schema.json`:
   `{ engagement, segments: [{id, name, size, characteristics}], competitors: [{id, name, segment, positioning_quadrant}], positioning: {axes, our_position} }`
3. `growth market materialise --engagement <slug> --market-json <path>` —
   validates schema, stamps provenance, derives rollups (segment count,
   competitor count, positioning quadrant distribution).

## Conventions

- **You generate / map; you don't outreach.** Sending is L3 (messaging
  studio, user authorised).
- **ICP is the link to audience.** When an audience slug exists, use it
  for fit scoring so the cast shares one reader model.
- **Cite signals.** Every fit assessment names matched + missing
  signals from the criteria — never a bare score.
