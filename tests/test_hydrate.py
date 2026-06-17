#!/usr/bin/env python3
"""UDS Slice C0 — application-UI hydration (ADR-006, #125). Standalone; run:
    design/.venv/bin/python tests/test_hydrate.py

Pins the hydration layer that sits on the canonical register (uds/archetypes.yml):
the greyscale → brand theme generation, the theme-contract CLOSURE (base.css only
references tokens a theme emits), selector COVERAGE for the brief's archetypes, and
the two load-bearing colour rules (crimson = action, yellow = attention; greyscale
carries neither).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import hydrate as hyd  # noqa: E402
from studio import uds as uds_mod  # noqa: E402
from studio.formats import SealedKeyConflict  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. The whole hydration layer validates: canonical register + closure + coverage.
errs = hyd.validate()
check("hydration validates", errs == [], "; ".join(errs))

# 2. Hydration projects the real nopilot tokens onto the --uds-* surface.
npt = hyd.vars_for_brand("nopilot")
light, dark = npt["light"], npt["dark"]
check("npt primary = crimson.600", light.get("color-primary") == "#C3094A", str(light.get("color-primary")))
check("npt active = signal yellow", light.get("color-active") == "#FFC10E", str(light.get("color-active")))
check("yellow rule: ink on active", light.get("color-on-active") == "#1C2022", str(light.get("color-on-active")))
check("npt dark primary = crimson.500", dark.get("color-primary") == "#E11A57", str(dark.get("color-primary")))
check("npt body face = Inter", npt["static"].get("font-body", "").split(",")[0] == "Inter", npt["static"].get("font-body"))
check("npt display = Newsreader", npt["static"].get("font-display", "").split(",")[0] == "Newsreader", npt["static"].get("font-display"))

# 3. Greyscale is the QUIET default — neither signal colour appears anywhere.
grey = hyd.vars_greyscale()
grey_values = set(grey["light"].values()) | set(grey["dark"].values())
check("greyscale has no crimson", "#C3094A" not in grey_values and "#E11A57" not in grey_values, str(sorted(grey_values)))
check("greyscale has no signal yellow", "#FFC10E" not in grey_values, str(grey["light"].get("color-active")))
check("greyscale primary is neutral graphite", grey["light"].get("color-primary") == "#353C40", str(grey["light"].get("color-primary")))

# 4. Theme-contract CLOSURE: base.css references only tokens BOTH themes emit.
base = hyd.BASE_CSS.read_text(encoding="utf-8")
referenced = hyd.referenced_var_names(base)
emitted = hyd.emitted_var_names(npt) & hyd.emitted_var_names(grey)
missing = referenced - emitted
check("base.css closes over the theme surface", not missing, f"undefined: {sorted(missing)}")
check("base.css actually uses the surface", len(referenced) > 30, f"only {len(referenced)} vars referenced")

# 5. Selector COVERAGE: the brief's archetypes are all styled in base.css.
styled = hyd.styled_archetypes(base)
brief = {"ui-header", "ui-footer", "shelf", "central-body", "modal", "lister", "grid", "card", "button", "control", "navigation"}
check("brief archetypes are built", brief <= styled, f"missing: {sorted(brief - styled)}")
# and every styled slug is a real archetype (no orphan classes vs the canonical register)
canon = set(uds_mod.archetypes())
check("no orphan archetype classes", styled <= canon, f"orphans: {sorted(styled - canon)}")

# 6. render_document assembles a hydrated document (the programmatic path).
doc = hyd.render_document('<main class="uds-card"></main>', title="Probe", theme="nopilot", mode="light")
check("doc has doctype", doc.lstrip().startswith("<!doctype html>"))
check("doc links the brand theme", "theme-nopilot.css" in doc, doc[:200])
check("doc links base.css", "base.css" in doc)
check("doc carries the body", 'class="uds-card"' in doc)

# 7. The generated theme files on disk match the generator (no stale artifact).
nopilot_css = (hyd.THEMES_DIR / "theme-nopilot.css")
check("nopilot theme written", nopilot_css.exists())
if nopilot_css.exists():
    txt = nopilot_css.read_text(encoding="utf-8")
    check("theme file carries crimson primary", "#C3094A" in txt)
    check("theme file has a dark block", '[data-theme="dark"]' in txt)

# 8. GOVERNANCE (ADR-005/006) — seals enforced, naming holds, provenance stamped.
# 8a. Seals are realised in the UI for every built archetype.
check("seals realised", hyd.seal_violations() == [], "; ".join(hyd.seal_violations()))
check("naming holds", hyd.naming_violations() == [], "; ".join(hyd.naming_violations()))

# 8b. Governed hydration reuses the canonical sealing engine: brands skin (open
#     tokens), but a sealed-term override fails closed.
opened = hyd.hydrate_archetype("button", overrides={"theme": {"color-primary": "#000000"}})
check("open re-skin allowed", opened["theme"]["color-primary"] == "#000000", str(opened.get("theme", {}).get("color-primary")))
check("hydration stamps contract_hash", opened["built_against"]["contract_hash"].startswith("sha256:"))
for bad in ({"sealed_terms": {"colour-split": "off"}}, {"tier": "view"}, {"selector": ".x"}):
    raised = False
    try:
        hyd.hydrate_archetype("button", overrides=bad)
    except SealedKeyConflict:
        raised = True
    check(f"sealed override blocked: {list(bad)[0]}", raised)

# 8c. Provenance lock — built_against the register + the exact tokens snapshot.
prov = hyd.provenance("nopilot")
check("lock scope canonical", prov["scope"] == "canonical")
check("lock cites register hash", prov["built_against"]["register"]["sha256"].startswith("sha256:"))
check("lock cites tokens hash", prov["built_against"]["tokens"]["sha256"].startswith("sha256:"))
check("tokens hash matches brand-store provenance", prov["built_against"]["tokens"]["matches_provenance"] is True,
      str(prov["built_against"]["tokens"]))
check("lock carries the lucide seal", "icon:lucide@1.5px" in prov["locks"], str(prov["locks"]))
check("token surface lists primary + active", {"primary", "active"} <= set(prov["token_surface"]["color"]))

if failures:
    print(f"FAIL ({len(failures)})")
    for x in failures:
        print("  -", x)
    sys.exit(1)
print("PASS: UDS Slice C0 (application-UI hydration)")
