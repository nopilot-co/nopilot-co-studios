#!/usr/bin/env python3
"""UDS Slice 0 — W3C tokens + grammar (ADR-006, #123/#124). Standalone; run:
    design/.venv/bin/python tests/test_uds.py

Validates the brand-agnostic grammar (format set, px→pt rule, aspect classes,
register), the W3C token resolver (references + light/dark), and the real nopilot
tokens graduated to the brand store (the locked palette + type rules).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import uds  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. The grammar manifest is schema-valid + cross-referentially consistent.
doc = uds.load_uds()
check("uds grammar validates", uds.validate_uds(doc) == [], "; ".join(uds.validate_uds(doc)))

# 2. Format set: HTML composition; html/gslide/pdf critical; the six-format full set.
f = doc["formats"]
check("composition html", f["composition"] == "html", str(f))
check("critical = html/gslide/pdf", set(f["critical"]) == {"html", "gslide", "pdf"}, str(f["critical"]))
check("full = six", set(f["full"]) == {"html", "pdf", "pptx", "docx", "gslide", "gdoc"}, str(f["full"]))

# 3. The cross-format px→pt type rule (design.md anchors).
m = doc["type_px_to_pt"]
check("display 64px→40pt", m.get("display") == "40pt", str(m))
check("body 16px→11pt", m.get("body") == "11pt", str(m))

# 4. Aspect classes span landscape↔portrait and partition the full set.
ac = uds.aspect_classes(doc)
check("orientations span", {ac[k]["orientation"] for k in ac} >= {"fluid", "landscape", "portrait"}, str(list(ac)))

# 5. Register: four sealed tiers + the lister→card→detail spine.
arch = uds.archetypes(doc)
tiers = {a["tier"] for a in arch.values()}
check("four tiers", tiers == {"infrastructure", "view", "component", "element"}, str(tiers))
check("seal rule (extend, not alter)", "extended" in doc.get("seal_rule", "") and "never altered" in doc.get("seal_rule", ""), doc.get("seal_rule"))
check("infrastructure is html", all("html" in a["formats"] for a in arch.values() if a["tier"] == "infrastructure"))
check("lister item = card", arch["lister"].get("item") == "card", str(arch.get("lister")))
check("lister links_to detail", arch["lister"].get("links_to") == "detail")
check("card links_to detail", arch["card"].get("links_to") == "detail")
check("icon set sealed", "set-lucide" in arch["icon"].get("sealed", []) and "stroke-1.5px" in arch["icon"].get("sealed", []), str(arch["icon"].get("sealed")))
check("markdown spine H1", any(str(x["md"]).startswith("# H1") for x in doc["markdown_mapping"]))

# 6. W3C resolver (hermetic fixture): references + light set resolve; family list kept.
FIX = {
    "$description": "fixture",
    "color": {
        "crimson": {"600": {"$type": "color", "$value": "#C3094A"}},
        "neutral": {"900": {"$type": "color", "$value": "#1C2022"}},
    },
    "semantic": {"light": {
        "primary": {"$type": "color", "$value": "{color.crimson.600}"},
        "on-active": {"$type": "color", "$value": "{color.neutral.900}"},
    }},
    "font": {
        "family": {"display": {"$type": "fontFamily", "$value": ["Newsreader", "Georgia", "serif"]}},
        "size": {"body": {"$type": "dimension", "$value": "16px"}},
    },
}
r = uds.resolve_tokens(FIX)
check("ref resolves", r["semantic"]["light"]["primary"] == "#C3094A", str(r["semantic"]["light"]))
check("ink-on-active resolves", r["semantic"]["light"]["on-active"] == "#1C2022", str(r["semantic"]["light"]))
check("family list kept", r["font"]["family"]["display"] == ["Newsreader", "Georgia", "serif"], str(r["font"]["family"]))

# 7. The real nopilot tokens (graduated to the brand store) resolve as specified.
try:
    u = uds.resolve_uds("nopilot")
except FileNotFoundError as e:
    check("nopilot tokens graduated", False, str(e))
else:
    light, dark = u["semantic"]["light"], u["semantic"]["dark"]
    check("primary = crimson.600", light.get("primary") == "#C3094A", light.get("primary"))
    check("active = signal yellow", light.get("active") == "#FFC10E", light.get("active"))
    check("yellow rule: ink on active", light.get("on-active") == "#1C2022", light.get("on-active"))
    check("dark primary = crimson.500", dark.get("primary") == "#E11A57", dark.get("primary"))
    check("body face = Inter", u["type"]["body"]["family"].split(",")[0] == "Inter", u["type"]["body"]["family"])
    check("display face = Newsreader", u["type"]["display"]["family"].split(",")[0] == "Newsreader", u["type"]["display"]["family"])
    # the cross-format type rule: web px paired with document pt on the same role.
    check("body px", u["type"]["body"]["px"] == "16px", str(u["type"]["body"]))
    check("body pt", u["type"]["body"]["pt"] == "11pt", str(u["type"]["body"]))
    check("dataviz leads crimson", u["dataviz"][:1] == ["#E11A57"], str(u["dataviz"][:2]))
    # The icon set is canonically locked to Lucide @ 1.5px.
    check("icon set = lucide", u["icon"].get("set") == "lucide", str(u.get("icon")))
    check("icon stroke = 1.5px", u["icon"].get("stroke") == "1.5px", str(u.get("icon")))
    check("icon md size", u["icon"].get("size", {}).get("md") == "20px", str(u["icon"].get("size")))

if failures:
    print(f"FAIL ({len(failures)})")
    for x in failures:
        print("  -", x)
    sys.exit(1)
print("PASS: UDS Slice 0 (W3C tokens + grammar)")
