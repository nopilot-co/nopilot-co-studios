# Studio plugin — session context

**Current Task:** Epic #98 — format-contract architecture (ADR-005). Three PRs open and stacked deliver the full epic acceptance; #100 + nitpicker gate (#102) remain before the 360 showcase ships visually.

## Key Decisions
- Four orthogonal layers: **purpose ← layout ← export ← brand ← session**; `seals:` honoured by `_merge_layers`; diverging session must fork (rejected / local-frozen / global-PR), never silent.
- Engine selection is layout-keyed (`_ENGINES` registry in `render.py`); PPTX overrides layout because a native deck has its own engine.
- Provenance: every render stamps `built_against: {id, hash, scope, derived_from}` on `version.json`; render is fail-closed against the resolved contract.

## Open PRs (stacked, satisfy #98 in full)
- **#107** — `feat/format-contract-layouts-tier` — layouts/ tier + sealed-key merge
- **#108** — `feat/render-engine-dispatch` — engine registry + dispatch (#99)
- **#109** — `feat/contract-provenance-stamp` — `built_against` + fail-closed (#101)

## Verified 2026-06-10 (smoke render)
- 360 brand ingested deterministically from `Coherence360_Business_Plan_20260424.pptx` → `~/context/studios/brand/360/`.
- `studio render` of `showcase-html` against `360` produced a real 58KB HTML stamped with provenance — proves engine dispatch + fail-closed + `built_against` work end-to-end on a real brand. The HTML still uses the template's hardcoded nopilot tokens (BRAND TOKENS substitution = #100).

## Next Steps
1. **Merge PR stack** (#107 → #108 → #109) once reviewed.
2. **#100** — data-driven render: substitute the template's BRAND TOKENS block from `_brand.yml`, parse `source.md` into topics (H2) + detail panels (H3), fill the CONTENT SLOT. Needs design call on the source.md schema.
3. **360 source content** — author the showcase `source.md` from coh.360 proposition materials (`~/context/.smart-env/multi/context-message-360_*` ajson files); refine the 360 `_brand.yml` via the brand-ingest skill (logo + accent confirmation).
4. **Re-render + nitpicker (#102)** before handoff to the `nopilot-co-www` magic-link flow.

Board: https://github.com/orgs/nopilot-co/projects/1
