# UDS application-UI — hydration layer (Layer C)

The **screen realisation** of the UDS UI archetypes. The contracts live in the
canonical register [`../archetypes.yml`](../archetypes.yml) (tiers
*infrastructures → views → components → elements*, sealed per ADR-005); this folder
is the HTML/CSS that *hydrates* them — greyscale by default, branded by an
opinionated token set (npt). It does **not** redefine the register; it binds to it.

> Slice C0 of the UDS epic ([#125](https://github.com/nopilot-co/nopilot-co-studios/issues/125),
> under [#123](https://github.com/nopilot-co/nopilot-co-studios/issues/123) / ADR-006).
> Built *on top of* Slice 0's grammar + token resolver (`studio.uds`).

## The idea — one contract, two skins

An archetype is a **strict contract** (anatomy, sealed slots, behaviour). It carries
**no colour or size**. Everything visual is a CSS custom property:

```
.uds-button--primary { background: var(--uds-color-primary); color: var(--uds-color-on-primary); }
```

A **theme** defines those `--uds-*` properties on `:root`. Swap the theme link and
the *same markup* re-skins:

- `themes/theme-greyscale.css` — the **default contract**. Neutral graphite; the two
  signals are drained (crimson → graphite, yellow → a neutral highlight). Quiet.
- `themes/theme-nopilot.css` — **hydrated** with the npt brand. Crimson primary,
  signal yellow, Newsreader / Inter / Geist Mono.

Both themes are **generated** by `studio.hydrate` from one source of truth — the
brand's `tokens.yaml` (`~/context/studios/brand/<brand>/tokens.yaml`) via
`studio.uds.resolve_uds`. No value is authored twice; "one source reaches six
formats" holds on the screen surface too.

## The two load-bearing rules (design.md)

- **Two signals, never swapped.** `--uds-color-primary` (crimson) = **action**
  (CTA, brand mark, links, accent edge). `--uds-color-active` (yellow) =
  **attention** (focus ring, selected, live point). Yellow is a **fill, never a text
  colour** — text on yellow is `--uds-color-on-active` (ink). The test pins this.
- **One source, every format.** Change `tokens.yaml`, regenerate, everything moves.

## Files

| File | What |
|------|------|
| `base.css` | The greyscale archetype stylesheet. Every rule references only `var(--uds-*)`. Structured by tier; each block names the contract tokens and the sealed terms it honours. |
| `themes/theme-greyscale.css` | Generated default theme (the contract, unbranded). |
| `themes/theme-<brand>.css` | Generated hydrated theme (e.g. `theme-nopilot.css`). |
| `app.js` | Progressive enhancement for the sealed *behaviours*: shelf toggle, modal focus-trap + dismissal, accordion, nav-group disclosure, and the login → gateway submit. |
| `icons.svg` | Shared icon sprite, built from the **vendored Lucide set** (`resources/iconography/lucide`, ISC, v0.469.0, locked 1.5px). Examples reference `../icons.svg#i-<name>`; `.uds-icon` governs stroke/size/colour. |
| `examples/login.html` | The brief — a login form (gateway → TwentyCRM auth contract). |
| `examples/dashboard.html` | The brief — sidebar-first: full-height shelves (logo · collapsible nav · account controls), thin glyph-rail collapsed state, central grid-of-cards. |
| `examples/detail.html` | A record `detail` (the card → detail destination): normalised hierarchy + `graphic` (dataviz) + sticky aside + related strip. |
| `examples/board.html` | The Pipeline `board` (kanban) — columns of cards, each linking to a detail. |

## Class convention (the binding)

The register declares contracts, not selectors. This layer binds each to a class:

```
.uds-<slug>             an archetype           (slug ∈ ../archetypes.yml)
.uds-<slug>__<part>     a named part / slot    (sealed slots are never styled away)
.uds-<slug>--<variant>  a sanctioned variant   (an `extends` axis, e.g. shelf side)
.is-<state>             an interaction/data state
```

A few composition **helpers** that are not archetypes (the frame + shared atoms):
`.uds-shell`, `.uds-stack`, `.uds-cluster`, `.uds-spacer`, `.uds-field`,
`.uds-eyebrow`, `.uds-muted`, `.uds-badge`, `.uds-avatar`, `.uds-brand`.

## CLI

```bash
# regenerate the greyscale + brand themes from tokens.yaml
PYTHONPATH=design/scripts python -m studio.hydrate themes --brand nopilot

# validate: register (studio.uds) + theme closure + selector coverage
PYTHONPATH=design/scripts python -m studio.hydrate validate
```

`validate` fails closed (ADR-005 precedent) on: an invalid register, a `var(--uds-*)`
in `base.css` that **no theme emits** (closure), or a `.uds-<slug>` class that maps to
**no archetype or helper** (coverage). Run the examples with any static server:
`python -m http.server --directory design/uds/ui` → `/examples/dashboard.html`.

## The brief's auth boundary (login → gateway → TwentyCRM)

`examples/login.html` posts to a **gateway** that authenticates the user *and*
confirms they are an **authorised member in TwentyCRM**:

```
POST <data-gateway>   { email, password }
  200 { ok, token, redirect }   gateway verified creds AND TwentyCRM authorisation
  401                            invalid credentials
  403 { error }                 authenticated, but not an authorised TwentyCRM user  ← the brief's gate
```

The live gateway / TwentyCRM wiring is a **separate backend task** (out of scope for
this slice). For the offline proof, the form carries `data-mock`: `demo@nopilot.co`
+ an 8-character password is "authorised"; anything else returns the 403 path. Swap
`data-mock` for the real `data-gateway` endpoint to wire it up.

## Governance (ADR-005 / ADR-006) — implemented, not decorative

The register *declares* governance (`../archetypes.yml`: the `seal_rule`, each
archetype's `sealed:` terms, and the brand-store `tokens.provenance.json` `locks`).
This layer **enforces** it, reusing the canonical sealing engine (`studio.formats`)
— it does not invent a parallel one. Four obligations, all in the fail-closed
`studio.hydrate validate` gate (ADR-005 precedent: a violation is a non-zero exit):

1. **Closure** — `base.css` may reference only `--uds-*` tokens a theme emits.
2. **Coverage** — every `.uds-<slug>` is a canonical archetype or a documented helper.
3. **Seals realised** — a *built* archetype must implement each `sealed:` term it
   declares (e.g. `central-body` → `__title` + `__byline` slots; `modal` →
   focus-trap + scrim + dismissal in `app.js`; `button` → the crimson/yellow
   colour-split; `icon` → `stroke-1.5px`). A sealed term left unrealised fails the gate.
4. **Naming** — tokens are `--uds-<group>-<name>`; slugs are kebab-case.

**Brands skin, never alter.** `studio.hydrate hydrate <slug>` merges the archetype
contract ← the brand token surface ← any overrides through `formats._merge_layers`.
A brand may set token *values* (the open surface) freely; an override that writes a
**sealed** path (`tier`, `selector`, `sealed_terms`) raises `SealedKeyConflict` — the
same hard-fail as a format contract. To change a sealed term you **fork** (local-frozen
or global-PR), per ADR-005; it never drifts silently.

**Provenance.** `studio.hydrate themes` also writes `themes/uds-ui.lock.json` — the
ADR-005 `built_against` model: the register hash, the exact `tokens.yaml` hash (verified
against the brand store's `tokens.provenance.json` `content_hash`), the sealed token
surface, and the carried-forward `locks` (`icon:lucide@1.5px`). Each example asset cites
it via `<meta name="uds-built-against">`. There is structurally one version of the truth.

## Status & next

Slice C0 ships the hydration layer + four screens (login · dashboard · detail · board),
proven across the greyscale ↔ npt swap and validated (closure + coverage + seals +
naming). `board`, `detail` and `graphic` are now built (the dataviz ramp graduated to
the token surface as `--uds-dataviz-1…6`, so charts read from `tokens.yaml` like
everything else); the sidebar collapses to a glyph-rail with tooltips + a hover-peek
flyout for nav groups. The **Lucide set is vendored** (`resources/iconography/lucide`,
ISC v0.469.0) into `icons.svg`, honouring the brand's `icon:lucide@1.5px` lock — the
`set-lucide` seal now checks the sprite and the lock records the set + sprite hash.
Next: drag-reorder on the board; and — per ADR-006 §5 — the `nopilot-co-www` save
fan-out driving these from the docket.
