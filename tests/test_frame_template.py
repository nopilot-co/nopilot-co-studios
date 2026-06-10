#!/usr/bin/env python3
"""Frame-engine brand-token substitution (#100, slice 1).

Verifies the deterministic frame_template module: token resolution from
_brand.yml, BRAND TOKENS block generation, inline-hex substitution, and the
end-to-end fill_template flow.

Run: design/.venv/bin/python tests/test_frame_template.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

ft = importlib.import_module("studio.frame_template")

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. Hex helpers
check("hex_to_rgb basic", ft._hex_to_rgb("#FF8000") == (255, 128, 0))
check("hex_to_rgb 3-char", ft._hex_to_rgb("#fff") == (255, 255, 255))
check("darken halves", ft._darken("#FFFFFF", 0.5) == "#7F7F7F")
check("lighten on black gives gray midway", ft._lighten("#000000", 0.5) == "#7F7F7F")

# 2. Token resolution from a minimal brand.
brand = {
    "color": {
        "primary": "#3A4340",
        "secondary": "#1F2A28",
        "foreground": "#1A1A1A",
        "background": "#FFFFFF",
        "palette": {"brand-3": "#7A8A5C", "brand-6": "#5F6F45"},
    },
    "typography": {
        "headings": {"family": "Calibri"},
        "base": {"family": "Cambria"},
        "monospace": {"family": "JetBrains Mono"},
    },
}
tok = ft.resolve_tokens(brand)
check("primary from brand", tok["primary"] == "#3A4340")
check("ink from foreground", tok["ink"] == "#1A1A1A")
check("paper from background", tok["paper"] == "#FFFFFF")
check("accent picked from palette when color.accent absent",
      tok["accent"] in ("#7A8A5C", "#5F6F45"), tok["accent"])
check("primary_d is darker than primary",
      ft._hex_to_rgb(tok["primary_d"]) < ft._hex_to_rgb(tok["primary"]))
check("font serif from brand", tok["serif"] == "Calibri")
check("font sans from brand", tok["sans"] == "Cambria")

# 3. Explicit color.accent wins over palette.
brand_w_accent = {"color": {"primary": "#000", "accent": "#FF0000",
                            "palette": {"brand-3": "#00FF00"}}}
check("explicit color.accent wins",
      ft.resolve_tokens(brand_w_accent)["accent"] == "#FF0000")

# 4. BRAND TOKENS block round-trips through substitution.
mini_html = """
<head>
  /* ===== BRAND TOKENS — bind these from the active brand's _brand.yml ===== */
  tailwind.config = { theme: { extend: { colors: { ink:'#0E1726' } } } }
  /* ===== /BRAND TOKENS ===== */
</head>
"""
block = ft.build_brand_tokens_block(tok)
substituted = ft._substitute_tokens_block(mini_html, block)
check("BRAND TOKENS block replaced", "#3A4340" in substituted)
check("old hex inside the BRAND TOKENS region removed",
      "'#0E1726'" not in substituted)
check("end marker preserved for re-substitution",
      "/BRAND TOKENS =====" in substituted)

# 5. Missing markers -> RuntimeError.
try:
    ft._substitute_tokens_block("<head>no markers here</head>", block)
    failures.append("missing markers should raise RuntimeError")
except RuntimeError as e:
    check("markers-missing error explains", "markers not found" in str(e))

# 6. Inline-hex substitution swaps the known nopilot hexes.
sample = ".dot360::after{background:#167C6B;color:#0E1726;border:1px solid #E2DCCF}"
swapped = ft._substitute_inline_hexes(sample, tok)
check("inline #167C6B -> primary", tok["primary"] in swapped)
check("inline #0E1726 -> ink", tok["ink"] in swapped)
check("inline #E2DCCF -> line", tok["line"] in swapped)
check("no nopilot teal left", "#167C6B" not in swapped.upper().replace("#167C6B","#167C6B"))
# case-insensitive
mixed = "#167c6b color:#167C6B"
swapped_mixed = ft._substitute_inline_hexes(mixed, tok)
check("inline-hex sub is case-insensitive",
      "#167C6B" not in swapped_mixed.upper())

# 7. End-to-end fill_template against the real showcase template.
tpl_path = REPO / "design" / "templates" / "showcase" / "showcase.html"
template_html = tpl_path.read_text(encoding="utf-8")
filled = ft.fill_template(template_html, brand, title="360 Test", description="d")
check("title substituted", "360 Test" in filled)
check("description substituted", "<meta name=\"description\" content=\"d\">" in filled)
check("brand primary present in output", "#3A4340" in filled)
check("template's nopilot teal removed from output",
      "#167C6B" not in filled and "#167c6b" not in filled)
check("template's nopilot ink removed from output",
      "#0E1726" not in filled and "#0e1726" not in filled)
check("BRAND TOKENS region still bounded",
      "/BRAND TOKENS =====" in filled)

if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("OK — frame_template token substitution + brand fill verified")
