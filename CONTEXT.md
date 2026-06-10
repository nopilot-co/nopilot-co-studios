# Studio plugin — session context

**Current Task:** Epic #98 — format-contract architecture (ADR-005). Driving use case: complete the **360 proposition showcase** (regressed on 2026-06-06: `showcase-html` silently dropped two-axis frame → single-axis scroll; sections stubbed but passed gates; runs non-deterministic).

## Key Decisions
- Four orthogonal layers: **purpose ← layout ← export ← brand ← session**; `seals:` honoured by `_deep_merge`; diverging session must fork (rejected / local-frozen / global-PR), never silent.
- ADR-005 merged (PR #106). Spine = #99 layouts, #100 data-driven render, #101 fail-closed validation. Dependents = #102 nitpicker gates, #103 long-form composer, #104 doctor preflight, #105 fast path.
- Server modes (#23) and `on_surface` contrast (#27) deprioritised behind the contract fix.

## Next Steps
1. **#99** — split `showcase` purpose into `showcase` (intent) + `frame` (layout); add `layouts/` tier; default existing slugs to `layout: linear`.
2. **#101** — fail-closed validation at render (`built_against` stamp in `version.json`; halt on sealed-key conflict).
3. **#100** — data-driven render (md/csv/yaml → template fill) so 360 sections can't be stubbed.
4. Then: ingest 360 brand into `~/context/studios/design/360/` (none exists yet) → re-render showcase against the now-enforced contract → nitpicker (#102) before handoff to `nopilot-co-www` magic-link flow.

Board: https://github.com/orgs/nopilot-co/projects/1
