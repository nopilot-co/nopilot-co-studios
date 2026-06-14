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

# 8. Topic parser: H2 = master, H3 = detail.
sample_md = """\
# Document title — ignored by parse_topics

Hook paragraph (no topic yet).

## The first thing

This is the zoom-out idea — one strong line.

A second paragraph.

### A detail of the first

Detail content here.

### Another detail

More detail.

## The second thing {#second}

Just a master, no details.
"""

topics = ft.parse_topics(sample_md)
check("two topics parsed", len(topics) == 2, str(len(topics)))
check("first topic id slugged from title",
      topics[0]["id"] == "the-first-thing", topics[0]["id"])
check("explicit {#id} respected", topics[1]["id"] == "second")
check("first topic has 2 details", len(topics[0]["details"]) == 2)
check("second topic has 0 details", len(topics[1]["details"]) == 0)
check("master_md excludes detail headings",
      "Detail content" not in topics[0]["master_md"])
check("detail captured", topics[0]["details"][0]["title"] == "A detail of the first")
check("no H2 → empty list", ft.parse_topics("plain prose, no headings") == [])
check("only H1 → empty list", ft.parse_topics("# Just a title\nprose") == [])

# 9. Topic HTML rendering carries the viewer contract data-page-key.
topic_html = ft.render_topic_html(topics[0], 0)
check("master gets data-page-key :0",
      'data-page-key="the-first-thing:0"' in topic_html)
check("detail 1 gets data-page-key :1",
      'data-page-key="the-first-thing:1"' in topic_html)
check("detail 2 gets data-page-key :2",
      'data-page-key="the-first-thing:2"' in topic_html)
check("topic id on section", 'id="the-first-thing"' in topic_html)
check("track data attrs",
      'data-topic="the-first-thing"' in topic_html
      and 'data-title="The first thing"' in topic_html)
check("master title becomes <h2>", "<h2" in topic_html)
check("detail title becomes <h3>", "<h3" in topic_html)

# 10. CONTENT SLOT substitution end-to-end (real template).
filled_with_topics = ft.fill_template(
    template_html, brand, title="t", description="d", source_body=sample_md,
)
check("CONTENT SLOT: section ID present in output",
      'id="the-first-thing"' in filled_with_topics)
check("CONTENT SLOT: viewer-contract data-page-key present",
      'data-page-key="the-first-thing:0"' in filled_with_topics)
check("CONTENT SLOT: end marker preserved",
      "/CONTENT SLOT" in filled_with_topics)
check("CONTENT SLOT: opener marker preserved",
      "============================ CONTENT SLOT ============================"
      in filled_with_topics)
# Template's authored 360 copy should be gone now (replaced by our topics).
check("CONTENT SLOT: authored hero copy removed when topics provided",
      "EU AI ACT · HIGH-RISK OBLIGATIONS" not in filled_with_topics)

# 11. No source body / no topics: template's authored copy stays.
filled_no_body = ft.fill_template(template_html, brand, title="t", description="d")
check("no source_body: authored copy retained",
      "Vertical topics, horizontal depth" in filled_no_body)
filled_empty_body = ft.fill_template(
    template_html, brand, title="t", description="d",
    source_body="just prose, no H2s here",
)
check("no H2 source: authored copy retained",
      "Vertical topics, horizontal depth" in filled_empty_body)

# 12. Missing CONTENT SLOT markers raise (the contract).
broken = template_html.replace("CONTENT SLOT", "REMOVED-MARKER")
try:
    ft._substitute_content_slot(broken, "<section>x</section>")
    failures.append("missing CONTENT SLOT markers should raise")
except RuntimeError as e:
    check("CONTENT SLOT markers-missing error explains",
          "markers not found" in str(e))

if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("OK — frame_template token substitution + content-slot fill verified")
