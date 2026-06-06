---
description: Validate a deal against the org's rate cards / margin floors / skill-set ratios (beancounter, review-class) and size the opportunity from client research + spend capacity + addressable market (commercial officer). Reuses the nitpicker engine for the verdict so a commercial verdict reads identically to any other gate.
argument-hint: <deal-slug or client-slug> [check <deal.yml>] [value from <docs>]
---

# /commercial-studio

Orchestrate the commercial studio end to end: either **check** a deal against
the org's pricing policy (deterministic verdict — go/needs-rework/blocked) or
**assess the value** of an opportunity from client research, spend capacity,
and addressable market. Both write to the shared studios-level commercial
store. The studio **judges and validates; it never agrees prices externally** —
that is L3, the Principal's job (Bible §6).

`$ARGUMENTS` names the **client slug** (an existing one to reuse, or a new one
to scaffold), an **artifact** to analyse (for `assess-commercial-value`), and/or
a **deal file** to check.

## Pipeline — check the deal (`check-commercials`, review-class)

1. **policy** — make sure the org's rate card + pricing policy are in place.
   - `commercial policy init` (idempotent; copies the template)
   - `commercial policy show` to inspect rate card + margin floor + skill ratios
2. **rubric** — the rubric lives in `configs/checks/`. Each check is a single
   scored test in the nitpicker test format. Critical checks gate the verdict.
   - `commercial checks list`
3. **new** — create a per-deal session and copy the deal file in.
   - `commercial check new --deal-slug <slug> --deal-file <path>`
4. **score** — run the deterministic checks; write `scores.yml`; aggregate via
   the nitpicker engine (same review-policy.yml) → `scorecard.json`.
   - `commercial check score --deal-slug <slug>`
5. **findings** — narrate the failures + strengthening areas (skill judgment).
6. **report** — surface the verdict to the Producer (and the Principal, who
   carries it to the user). A `critical` failure on a rate-card or margin floor
   gate blocks L2 sign-off.

## Pipeline — size the opportunity (`assess-commercial-value`)

1. **client** — create or open the client store.
   - `commercial client new --client <slug>`
2. **research** — file + review supplied financial research (earnings calls,
   RFPs, articles, etc.), cited.
   - `commercial research add --client <slug> --source <path-or-url> --kind …`
3. **assess** — caller-supplied-JSON materialiser: the model produces a
   structured `assessment.yml` (financial profile, spend capacity, addressable
   market, value-based opportunity sizing); the CLI materialises it with
   provenance.
   - `commercial value assess --client <slug> --assessment-json <path>`
4. **report** — the Principal walks the assessment back to the user (L2
   decision — confirm scope + investment band).

## Conventions

- Judgment lives in the skills (`check-commercials`, `assess-commercial-value`);
  mechanics live in the `commercial` CLI. Identical behaviour across invocation
  modes.
- The commercial studio **validates + assesses; it never sends a quote or agrees
  a price externally** — that's L3 (Principal → user → external).
- Scoring is single-sourced in the nitpicker engine. Don't re-implement the
  verdict math; if a number feels wrong, the scores or the rubric are.
- The Commercial store is studios-level and shared (org policy is one source of
  truth, client research is reusable across deals).
