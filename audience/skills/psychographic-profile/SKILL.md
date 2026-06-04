---
name: psychographic-profile
description: Synthesize the research into a structured psychographic profile and need-state for the reader — values, attitudes, motivations, approach, plus needs (with priorities), challenges, objectives, pains, objections, and decision factors — written to _audience.yml. Locks + validates it via `audience profile build`. Use after audience-research, before scoring-rubric.
---

# psychographic-profile

Turn the research into the **reader model** — the structured `_audience.yml` that
every downstream studio can read. This is the heart of the studio: a faithful,
cited picture of what the reader values and needs, and how they decide.

## Steps

1. **Write the psychographics.** From the research, fill `psychographics`:
   `values`, `attitudes` (each with a strength), `motivations`, and `approach`
   (how they evaluate and decide). Keep it specific to *this* reader, not a generic
   role.

2. **Write the need-state.** Fill `need_state`:
   - `stage` — where they are (unaware → … → deciding).
   - `needs[]` — each a `{id, statement, priority, evidence}`. The `statement` is
     in the reader's terms; `priority` is `critical | high | medium | low`
     (this drives the rubric weight, and `critical` needs become gates);
     `evidence` cites `research/` sources. **Get the priorities right** — they
     decide what the critique weighs most.
   - `challenges`, `objectives`, `pains`, `objections` (each with the counter the
     reader needs), `decision_factors`.

3. **Write communication preferences.** `register`, `reading_level`,
   `preferred_evidence`, `avoid`, `channels` — how to speak so it lands.

4. **Cite provenance.** Ensure `provenance.sources` lists each research source.
   Every asserted need/attitude should trace to one.

5. **Build + validate:**
   ```bash
   audience profile validate --audience <slug>     # schema check
   audience profile build --audience <slug> [--status validated]
   ```
   `build` validates the whole model and stamps `provenance.built`. Set
   `--status validated` **only** once the user has confirmed the persona
   (see persona-intake) — otherwise leave it `inferred`.

6. Hand the slug to `scoring-rubric` to derive the weighted critique rubric.

## Conventions

- The model is the single source of truth for the reader, reused across studios —
  make it complete and honest, not flattering.
- `priority` is load-bearing: `critical` needs gate the verdict. Reserve it for
  needs that, unmet, make the work fail for this reader regardless of polish.
- Mark inferences as inferences. Don't assert what the research doesn't support.
- Judgment here; the CLI only validates + stamps. Never hand-edit a model to pass
  validation — fix the substance.
