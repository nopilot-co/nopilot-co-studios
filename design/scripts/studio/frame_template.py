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

import markdown as md_lib
import yaml
from jinja2 import Template

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
    source_body: str | None = None,
) -> str:
    """Brand-substitute and jinja-render the showcase template.

    Order:
      1. Build token map from ``_brand.yml``.
      2. Replace the BRAND TOKENS block (the Tailwind config).
      3. Swap inline hardcoded hexes that bypass Tailwind.
      4. If ``source_body`` carries H2 topics, fill the CONTENT SLOT with them.
      5. Jinja-render ``{{ title }}`` / ``{{ description }}``.

    If ``source_body`` is ``None`` or has no H2 topics, the template's authored
    copy is left intact — useful for brands where the template already carries
    the right content.
    """
    tok = resolve_tokens(brand_yml)
    block = build_brand_tokens_block(tok)
    html = _substitute_tokens_block(template_html, block)
    html = _substitute_inline_hexes(html, tok)

    if source_body:
        topics = parse_topics(source_body)
        if topics:
            topics_html = "\n".join(
                render_topic_html(t, i) for i, t in enumerate(topics)
            )
            html = _substitute_content_slot(html, topics_html)

    html = Template(html).render(title=title, description=description)
    return html


# ----------------------------------------------------------- topic parsing


def _slugify(text: str) -> str:
    s = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return s or "topic"


# Match a leading H2 (## ...) or H3 (### ...) at the start of a line, capturing
# the level and the heading text. Optional Quarto-style `{#explicit-id}` suffix.
_HEADING_RE = re.compile(
    r"^(##{1,2})\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$",
    re.MULTILINE,
)


def parse_topics(body: str) -> list[dict[str, Any]]:
    """Split a Markdown body into topics (H2) and detail panels (H3).

    Returns a list of dicts:
        ``{id, title, master_md, details: [{title, id, md}]}``

    Content layout:
      ``## Topic`` starts a new topic; the markdown until the next ``##`` is
      the master panel. ``### Detail`` within a topic starts a detail panel;
      its markdown runs until the next ``###`` or ``##``. The topic's master
      panel is whatever comes before the first ``###`` (the "zoom-out" view).
    """
    matches = list(_HEADING_RE.finditer(body))
    h2s = [m for m in matches if len(m.group(1)) == 2]
    if not h2s:
        return []

    topics: list[dict[str, Any]] = []
    for tidx, h2 in enumerate(h2s):
        title = h2.group(2).strip()
        topic_id = h2.group(3) or _slugify(title)
        topic_end = h2s[tidx + 1].start() if tidx + 1 < len(h2s) else len(body)
        within = [
            m for m in matches
            if h2.end() <= m.start() < topic_end and len(m.group(1)) == 3
        ]
        if within:
            master_md = body[h2.end():within[0].start()].strip()
        else:
            master_md = body[h2.end():topic_end].strip()
        details: list[dict[str, str]] = []
        for didx, h3 in enumerate(within):
            d_title = h3.group(2).strip()
            d_id = h3.group(3) or _slugify(d_title)
            d_end = within[didx + 1].start() if didx + 1 < len(within) else topic_end
            d_md = body[h3.end():d_end].strip()
            details.append({"title": d_title, "id": d_id, "md": d_md})
        topics.append({
            "id": topic_id,
            "title": title,
            "master_md": master_md,
            "details": details,
        })
    return topics


def _md_to_html(md: str) -> str:
    """Markdown → HTML using the ``markdown`` library (with sane extensions)."""
    if not md.strip():
        return ""
    return md_lib.markdown(
        md,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )


def render_topic_html(topic: dict[str, Any], index: int) -> str:
    """Render one topic as a ``<section class="topic">`` block.

    Adheres to the template's viewer contract: every commentable panel carries
    ``data-page-key="<topicId>:<panelIndex>"`` (master=0, details start at 1).
    """
    tid = topic["id"]
    title = topic["title"]
    master_html = _md_to_html(topic["master_md"])
    panels: list[str] = [
        f"""\
      <div class="panel master py-20" data-page-key="{tid}:0">
        <div class="reveal max-w-4xl mx-auto">
          <div class="text-xs font-mont font-semibold tracking-[0.2em] uppercase text-amber-d mb-4">Topic {index + 1:02d}</div>
          <h2 class="text-4xl md:text-6xl tracking-tight leading-tight mb-8">{title}</h2>
          {master_html}
          <div class="mt-10 detailcue nudge"><span>scroll right for detail</span><iconify-icon icon="solar:arrow-right-linear" width="14"></iconify-icon></div>
        </div>
      </div>"""
    ]
    for di, d in enumerate(topic["details"], start=1):
        d_html = _md_to_html(d["md"])
        panels.append(f"""\
      <div class="panel detail py-20" data-page-key="{tid}:{di}">
        <div class="reveal max-w-3xl mx-auto">
          <div class="text-xs font-mont font-semibold tracking-[0.2em] uppercase text-teal mb-4">{title} · {di:02d}</div>
          <h3 class="text-3xl md:text-4xl tracking-tight leading-tight mb-6">{d["title"]}</h3>
          {d_html}
        </div>
      </div>""")
    panels_html = "\n".join(panels)
    return f"""\
  <section id="{tid}" class="topic">
    <div class="track" data-topic="{tid}" data-title="{title}">
{panels_html}
    </div>
  </section>"""


_CONTENT_SLOT_RE = re.compile(
    r"(<!-- ={5,} CONTENT SLOT ={5,}.*?-->)(.*?)(<!-- /CONTENT SLOT)",
    re.DOTALL,
)


def _substitute_content_slot(html: str, topics_html: str) -> str:
    """Replace the CONTENT SLOT region with rendered topics.

    Preserves the opening + closing sentinel markers so a re-render finds the
    same boundaries. Raises if the markers are absent — the contract.
    """
    if not _CONTENT_SLOT_RE.search(html):
        raise RuntimeError(
            "frame_template: CONTENT SLOT markers not found in template. "
            "Expected `<!-- ===== CONTENT SLOT ===== ... -->` opener and "
            "`<!-- /CONTENT SLOT` closer. Don't remove them."
        )
    replacement = f"\\1\n\n{topics_html}\n\n  \\3"
    return _CONTENT_SLOT_RE.sub(replacement, html, count=1)
