"""Frame-engine template fill (#100).

Substitutes the canonical ``templates/showcase/showcase.html`` template against a
brand: rewrites the BRAND TOKENS Tailwind config block from ``_brand.yml`` and
swaps the highest-impact hardcoded hex colors so the rendered asset actually
reflects the brand, not the template's nopilot defaults.

Pure-Python, deterministic. No judgment lives here.

Scope notes:
- This PR fills BRAND TOKENS + a small set of inline hardcoded hexes. CONTENT
  SLOT replacement (parsing source.md into topics) is a follow-up; the
  template's authored copy is kept as-is because it's already showcase-shaped.
- Fonts are passed through as family names; if the brand's font isn't on the
  template's Google Fonts URL the browser will fall back to the family chain.
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from jinja2 import Template

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(source_text: str) -> tuple[dict[str, Any], str]:
    """Split a YAML-frontmatter Markdown doc into (frontmatter, body).

    Returns an empty dict if no frontmatter block is present.
    """
    m = _FRONTMATTER_RE.match(source_text)
    if not m:
        return {}, source_text
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        return {}, source_text
    return data, source_text[m.end() :]

# Hex colors hardcoded in the template that we override (case-insensitive).
# Mapped to the token they MEAN, so brand-token values flow through.
_HARDCODED_HEX_MAP: dict[str, str] = {
    "#167C6B": "primary",       # teal default — main brand accent
    "#0F5A4D": "primary_d",     # darker primary
    "#D99A4E": "accent",        # amber default — secondary highlight
    "#B97C30": "accent_d",      # darker accent
    "#0E1726": "ink",           # foreground
    "#1B2738": "ink2",          # slightly lighter ink
    "#F7F5F0": "paper",         # background
    "#EFEBE2": "paper2",        # secondary surface
    "#E2DCCF": "line",          # hairlines
    "#5C6678": "muted",         # secondary text
}

# The template's CSS class .dot360 visual brandmark uses inline colors;
# we also substitute those even though the class name stays the same.


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_color: str, frac: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        max(0, int(r * (1 - frac))),
        max(0, int(g * (1 - frac))),
        max(0, int(b * (1 - frac))),
    )


def _lighten(hex_color: str, frac: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        min(255, int(r + (255 - r) * frac)),
        min(255, int(g + (255 - g) * frac)),
        min(255, int(b + (255 - b) * frac)),
    )


def _pick_accent(color: dict[str, Any]) -> str:
    """Choose an accent: explicit color.accent, else best palette member.

    Preference order:
      1. ``color.accent``
      2. The first palette entry that isn't the primary / secondary / fg / bg
      3. Fallback amber
    """
    if color.get("accent"):
        return color["accent"]
    palette = color.get("palette") or {}
    if isinstance(palette, dict):
        avoid = {
            (color.get("primary") or "").upper(),
            (color.get("secondary") or "").upper(),
            (color.get("foreground") or "").upper(),
            (color.get("background") or "").upper(),
            "#FFFFFF",
            "#000000",
        }
        for _, v in palette.items():
            if isinstance(v, str) and v.upper() not in avoid:
                return v
    return "#D99A4E"


def resolve_tokens(brand_yml: dict[str, Any]) -> dict[str, str]:
    """Compute the concrete token map a template substitution uses.

    All keys returned as hex strings (colors) or font-family stacks (fonts).
    Stable for the same input brand.
    """
    color = brand_yml.get("color") or {}
    typography = brand_yml.get("typography") or {}

    ink = color.get("foreground") or "#0E1726"
    paper = color.get("background") or "#F7F5F0"
    primary = color.get("primary") or "#167C6B"
    accent = _pick_accent(color)

    headings = ((typography.get("headings") or {}).get("family")) or "Instrument Serif"
    base = ((typography.get("base") or {}).get("family")) or "Inter"
    mono = ((typography.get("monospace") or {}).get("family")) or "JetBrains Mono"
    # Labels/eyebrows: a brand may or may not declare one; default to base.
    labels = ((typography.get("labels") or {}).get("family")) or base

    return {
        # colors
        "ink": ink,
        "ink2": _lighten(ink, 0.10),
        "paper": paper,
        "paper2": _darken(paper, 0.04),
        "line": _darken(paper, 0.10),
        "muted": "#5C6678",
        "primary": primary,
        "primary_d": _darken(primary, 0.15),
        "accent": accent,
        "accent_d": _darken(accent, 0.15),
        # fonts (family names — quoted at use site)
        "serif": headings,
        "sans": base,
        "mont": labels,
        "mono": mono,
    }


def build_brand_tokens_block(tok: dict[str, str]) -> str:
    """Generate the replacement BRAND TOKENS Tailwind config block.

    Drop-in replacement for the bordered region in the template. Keeps the
    sentinel markers so a future re-substitution finds the same boundaries.
    """
    return f"""\
  /* ===== BRAND TOKENS — bind these from the active brand's _brand.yml ===== */
  tailwind.config = {{ theme: {{ extend: {{
    colors: {{
      ink:'{tok["ink"]}',          /* _brand.color.foreground  — body / display text   */
      ink2:'{tok["ink2"]}',         /* derived: lightened ink                          */
      paper:'{tok["paper"]}',        /* _brand.color.background   — page canvas          */
      paper2:'{tok["paper2"]}',       /* derived: darkened paper                         */
      line:'{tok["line"]}',         /* hairlines / borders                             */
      muted:'{tok["muted"]}',        /* secondary text                                  */
      teal:{{DEFAULT:'{tok["primary"]}', d:'{tok["primary_d"]}'}},   /* _brand.color.primary  — accent/CTA */
      amber:{{DEFAULT:'{tok["accent"]}', d:'{tok["accent_d"]}'}}   /* derived: brand accent — highlight  */
    }},
    fontFamily: {{
      serif:['{tok["serif"]}','Georgia','serif'],   /* _brand.typography.headings  */
      sans:['{tok["sans"]}','system-ui','sans-serif'],        /* _brand.typography.base      */
      mont:['{tok["mont"]}','sans-serif'],               /* labels / eyebrows           */
      mono:['{tok["mono"]}','monospace']             /* _brand.typography.monospace */
    }}
  }}}}}}
  /* ===== /BRAND TOKENS ===== */"""


_TOKENS_RE = re.compile(
    r"/\* ===== BRAND TOKENS.*?===== /BRAND TOKENS ===== \*/",
    re.DOTALL,
)


def _substitute_tokens_block(html: str, block: str) -> str:
    """Replace the BRAND TOKENS region in-place. Raises if markers are missing."""
    if not _TOKENS_RE.search(html):
        raise RuntimeError(
            "frame_template: BRAND TOKENS markers not found in template — "
            "the sentinel comments are the contract; do not remove them."
        )
    return _TOKENS_RE.sub(block, html, count=1)


def _substitute_inline_hexes(html: str, tok: dict[str, str]) -> str:
    """Swap the highest-impact hardcoded hexes in inline CSS/JS.

    The Tailwind config swap above flows through class-based styling; this pass
    catches inline ``style=`` and ``<style>`` blocks that hard-code the
    template's authored hex codes (which are nopilot defaults).
    """
    # Build a single regex with all keys, case-insensitive, longest first
    # to avoid prefix collisions (none here but defensive).
    keys = sorted(_HARDCODED_HEX_MAP.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys), re.IGNORECASE)

    def _repl(m: re.Match[str]) -> str:
        token_name = _HARDCODED_HEX_MAP[m.group(0).upper()]
        return tok[token_name]

    return pattern.sub(_repl, html)


def fill_template(
    template_html: str,
    brand_yml: dict[str, Any],
    title: str,
    description: str,
) -> str:
    """Brand-substitute and jinja-render the showcase template.

    Order:
      1. Build token map from ``_brand.yml``.
      2. Replace the BRAND TOKENS block (the Tailwind config).
      3. Swap inline hardcoded hexes that bypass Tailwind.
      4. Jinja-render ``{{ title }}`` / ``{{ description }}``.
    """
    tok = resolve_tokens(brand_yml)
    block = build_brand_tokens_block(tok)
    html = _substitute_tokens_block(template_html, block)
    html = _substitute_inline_hexes(html, tok)
    html = Template(html).render(title=title, description=description)
    return html
