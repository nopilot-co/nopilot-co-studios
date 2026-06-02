# Studio plugin — session context

**Current Task:** Rendering program complete; remaining work is the server-modes epic + a contrast follow-up.

## Key Decisions
- Rendering engine: one `::: ` block source → HTML/PDF (Quarto+Typst) AND native editable PPTX (python-pptx); design-systems layer under the brand (defaults → system → brand).
- Verification bar is eyes-on-pixels (render → rasterize → look), not "it compiled".
- #23 (server modes) is a separate project needing architecture decisions first — not started.

## Done (merged to main, PRs #13–#29)
Dockets/storage-root; slice 1 formats+asset library; slice 2 component engine
(HTML+PDF parity); slice 3 figure/embed; 4a diagrams; data-viz (5 charts, unified
SVG); 4b editable PPTX (native shapes, 4 tiers); design-system selection; visual-qa
component rubric. ~9 standalone test suites green (`design/.venv/bin/python tests/test_*.py`).

## Next Steps
- #23 — server modes 2–3 (headless provider-agnostic skill runner + gatekeeper). Needs spike→spec→plan + user decisions on transport/auth/runner fork.
- #27 — panel-text contrast across brand×design-system (`on_surface` token).
- Board: https://github.com/orgs/nopilot-co/projects/1
