---
name: persona-intake
description: Take a user-supplied OR inferred-and-user-validated persona for "the reader" — the person a piece of work must satisfy — and scaffold the shared reader-model store. Locks the audience slug and the persona block of _audience.yml via `audience persona new`. Use first, before research and profiling.
---

# persona-intake

Establish **who the reader is** — the single person whose satisfaction the work
is judged by. A reader model is a reusable, studios-level resource (like a brand),
referenced by slug. You either take a persona the user gives you, or infer one and
**get the user to validate it** before treating it as real.

## Steps

1. **Get or infer the persona.** If the user supplied a persona (a description, a
   role, a named individual), use it. If not, infer one from the brief and any
   context to hand — role, seniority, org context, and a one-line "who they are +
   what they own".

2. **Validate an inferred persona with the user.** If you inferred it (rather than
   being given it), **show it back and ask the user to confirm or correct** before
   going further. An unconfirmed persona stays `status: inferred`; only a
   user-confirmed one earns `validated` (set later at `profile build`). Never
   silently treat an inferred reader as validated — the whole critique hangs on
   getting the reader right.

3. **Pick a slug** (kebab-case, e.g. `vp-eng-scaleup`) and scaffold the store:
   ```bash
   audience persona new --audience <slug> [--persona <path>]
   ```
   `--persona` may point at a YAML file with `name` / `persona` keys to seed it;
   otherwise a stub is scaffolded. This creates
   `~/context/studios/audience/<slug>/` with `_audience.yml` (persona block) and a
   `research/` folder.

4. **Fill the persona block** of `_audience.yml` (role, seniority, org_context,
   one_line) if it was stubbed. Leave the `need_state` for the profile step — but
   note the obvious needs you already see, to steer research.

5. Hand the slug to `audience-research` (gather context) → `psychographic-profile`
   (synthesize) → `scoring-rubric` (derive) → `audience-critique` (assess work).

## Conventions

- One reader per slug. The model is reusable across studios and runs — don't
  rebuild it per artifact; critique sessions live under the slug.
- Judgment here, mechanics in the `audience` CLI. The CLI only scaffolds/validates;
  the persona's substance is yours.
- An inferred persona must be **user-validated** before delivery decisions lean on
  it. Be explicit about which it is.
