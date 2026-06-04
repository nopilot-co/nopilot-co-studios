"""Pictorial storyboard board — see the plan before anything is rendered (#42).

Turns a (validated, normalized) ``storyboard.json`` into a self-contained HTML
**board**: one panel per scene, each a mini-frame in the target aspect ratio with
the layers drawn as positioned, role-coloured blocks, plus narration, the motion
notes (enter/emphasis/exit), duration and transition. Token-driven, so the board
already reads in the brand's colours.

This is the cheap, no-engine preview (the design studio's eyes-on-pixels bar,
applied before the expensive Remotion/provider render). A later, optional
"concept-frame" provider can replace each mini-frame's wireframe with an AI-
generated still — see ``board_providers`` note in CLAUDE.md / docs ADR-002.
"""

from __future__ import annotations

import html
from typing import Any

# region -> inset (top, right, bottom, left) as % of the frame.
_REGIONS = {
    "full": (6, 6, 6, 6),
    "center": (38, 18, 38, 18),
    "top": (8, 12, 72, 12),
    "bottom": (72, 12, 8, 12),
    "upper-third": (6, 8, 66, 8),
    "lower-third": (66, 8, 6, 8),
    "left": (20, 52, 20, 8),
    "right": (20, 8, 20, 52),
}

# layer role -> token colour key.
_ROLE_COLOR = {
    "primary": "primary",
    "secondary": "secondary",
    "accent": "tertiary",
    "surface": "surface",
}

_ASPECT = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = (107, 114, 128)
    return f"rgba({r},{g},{b},{alpha})"


def _motion_chips(layer: dict[str, Any]) -> str:
    bits = []
    for kind, arrow in (("enter", "▸"), ("emphasis", "✦"), ("exit", "◂")):
        if layer.get(kind):
            bits.append(
                f'<span class="chip"><b>{arrow}</b> {html.escape(str(layer[kind]))}</span>'
            )
    return "".join(bits)


def _layer_box(layer: dict[str, Any], color: dict[str, str]) -> str:
    t, r, b, l = _REGIONS.get(layer.get("region", "center"), _REGIONS["center"])
    role = layer.get("role")
    paint = color.get(_ROLE_COLOR.get(role, ""), color.get("secondary", "#6B7280"))
    style = (
        f"top:{t}%;right:{r}%;bottom:{b}%;left:{l}%;"
        f"border-color:{paint};background:{_rgba(paint, 0.12)};"
    )
    typ = html.escape(str(layer.get("type", "")).upper())
    content = html.escape(str(layer.get("content", "")))
    return (
        f'<div class="layer" style="{style}">'
        f'<span class="ltype" style="color:{paint}">{typ}</span>'
        f'<span class="ltext">{content}</span>'
        f"</div>"
    )


def _panel(i: int, scene: dict[str, Any], color: dict[str, str], ratio: float) -> str:
    layers = "".join(_layer_box(lr, color) for lr in scene.get("layers", []))
    chips = "".join(_motion_chips(lr) for lr in scene.get("layers", []))
    dur = scene.get("duration", 0)
    trans = scene.get("transition", "cut")
    narration = scene.get("narration", "")
    narration_html = (
        f'<p class="narration">{html.escape(narration)}</p>' if narration else ""
    )
    return f"""
    <figure class="panel">
      <figcaption class="pmeta">
        <span class="pnum">{i}</span>
        <span class="pid">{html.escape(str(scene.get('id','')))}</span>
        <span class="ptime">{dur}s &middot; {html.escape(trans)} &rarr;</span>
      </figcaption>
      <div class="frame" style="aspect-ratio:{ratio};">{layers}</div>
      {narration_html}
      <div class="chips">{chips}</div>
    </figure>"""


def render_html(spec: dict[str, Any], tokens: dict[str, Any]) -> str:
    """Self-contained HTML board for a normalized storyboard spec."""
    color = tokens.get("color", {})
    g = spec.get("global", {})
    ratio = _ASPECT.get(g.get("aspect", "16:9"), 16 / 9)
    title = g.get("title") or g.get("brand", "storyboard")
    total = sum(float(s.get("duration", 0)) for s in spec.get("scenes", []))
    meta = (
        f"brand: {html.escape(str(g.get('brand','—')))} &middot; "
        f"{html.escape(str(g.get('aspect','16:9')))} &middot; "
        f"{html.escape(str(g.get('fps','30')))}fps &middot; "
        f"motion: {html.escape(str(g.get('motion_system','default')))} &middot; "
        f"{len(spec.get('scenes', []))} scenes &middot; {total:g}s total"
    )
    panels = "".join(
        _panel(i + 1, s, color, ratio) for i, s in enumerate(spec.get("scenes", []))
    )
    fg = color.get("foreground", "#1A2433")
    bg = color.get("background", "#FFFFFF")
    surface = color.get("surface", "#F1F3F6")
    accent = color.get("tertiary", "#C0392B")
    secondary = color.get("secondary", "#6B7280")
    frame_bg = color.get("background", "#FFFFFF")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Storyboard &mdash; {html.escape(str(title))}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; background:{surface}; color:{fg};
    font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  .board {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
  .head {{ border-top: 10px solid {accent}; padding-top: 16px; margin-bottom: 24px; }}
  .head h1 {{ margin:0 0 4px; font-size: 1.7rem; color:{color.get('primary', fg)}; }}
  .head .meta {{ color:{secondary}; font-size:.8rem; letter-spacing:.02em; }}
  .head .label {{ display:inline-block; font-size:.66rem; letter-spacing:.18em;
    text-transform:uppercase; color:{accent}; margin-bottom:6px; font-weight:700; }}
  .grid {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 22px; }}
  .panel {{ margin:0; background:{bg}; border:0.5px solid {_rgba(secondary,0.4)};
    border-radius:8px; padding:14px; }}
  .pmeta {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:.78rem; }}
  .pnum {{ background:{accent}; color:#fff; width:20px; height:20px; border-radius:4px;
    display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:.72rem; }}
  .pid {{ font-weight:600; color:{color.get('primary', fg)}; }}
  .ptime {{ margin-left:auto; color:{secondary}; }}
  .frame {{ position:relative; width:100%; background:{frame_bg};
    border:1px solid {_rgba(secondary,0.35)}; border-radius:4px; overflow:hidden; }}
  .layer {{ position:absolute; border:2px solid; border-radius:3px;
    padding:6px 8px; display:flex; flex-direction:column; gap:2px; overflow:hidden; }}
  .ltype {{ font-size:.56rem; letter-spacing:.14em; font-weight:700; }}
  .ltext {{ font-size:.74rem; color:{fg}; line-height:1.2; }}
  .narration {{ margin:10px 0 6px; font-size:.86rem; color:{fg}; }}
  .narration::before {{ content:"“"; color:{secondary}; }}
  .narration::after {{ content:"”"; color:{secondary}; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .chip {{ font-size:.68rem; color:{secondary}; background:{surface};
    border:0.5px solid {_rgba(secondary,0.4)}; border-radius:99px; padding:2px 8px; }}
  .chip b {{ color:{accent}; }}
</style></head>
<body><div class="board">
  <header class="head">
    <div class="label">Storyboard preview &middot; not yet rendered</div>
    <h1>{html.escape(str(title))}</h1>
    <div class="meta">{meta}</div>
  </header>
  <div class="grid">{panels}</div>
</div></body></html>"""
