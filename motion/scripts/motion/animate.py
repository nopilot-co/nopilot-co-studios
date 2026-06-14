"""Declarative animation — a storyboard played as self-contained, branded HTML.

The no-Node render path (ADR-002): scenes are sequenced with CSS animations timed
by their durations, layers enter with their motion, everything painted in the
brand tokens. The result is the **embeddable preview** *and* the source the video
capture records to MP4 (see capture.html_to_video). Remotion is the optional
high-fidelity path for the same storyboard.
"""

from __future__ import annotations

import html
from typing import Any

from .board import _REGIONS, _rgba

# Stage pixel size by aspect (long edge = 1280) — fixed so video output is
# deterministic.
_ASPECT_WH = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (1080, 1080),
    "4:5": (1024, 1280),
}

_ROLE_COLOR = {"primary": "primary", "secondary": "secondary", "accent": "tertiary", "surface": "surface"}


def stage_size(spec: dict[str, Any]) -> tuple[int, int]:
    return _ASPECT_WH.get(spec.get("global", {}).get("aspect", "16:9"), (1280, 720))


def _motion_keyframe(enter: str | None) -> str:
    e = (enter or "").lower()
    if "wipe" in e:
        return "mWipe"
    if "up" in e:
        return "mUp"
    return "mFade"


def _layer(layer: dict[str, Any], color: dict[str, str], scene_start: float) -> str:
    t, r, b, l = _REGIONS.get(layer.get("region", "center"), _REGIONS["center"])
    pos = f"top:{t}%;right:{r}%;bottom:{b}%;left:{l}%;"
    role = layer.get("role")
    paint = color.get(_ROLE_COLOR.get(role, ""), color.get("foreground", "#1A2433"))
    anim = f"animation:{_motion_keyframe(layer.get('enter'))} .6s {scene_start + 0.2:g}s both;"
    typ = layer.get("type")
    content = html.escape(str(layer.get("content", "")))
    region = layer.get("region", "center")
    big = region in ("center", "top", "full")
    size = "2.6rem" if big else "1.6rem"

    if typ == "text":
        return (
            f'<div class="layer text" style="{pos}{anim}color:{paint};font-size:{size};">'
            f"{content}</div>"
        )
    if typ == "shape":
        # accent-rule → a thin bar; otherwise a filled rounded block.
        is_rule = "rule" in content.lower()
        h_css = "height:6px;top:auto;" if is_rule else ""
        return (
            f'<div class="layer shape" style="{pos}{anim}background:{paint};{h_css}"></div>'
        )
    # chart (S4): real animated bar / KPI count-up.
    if typ == "chart" and layer.get("chart"):
        return _chart(layer, color, scene_start, pos, paint)

    # image / icon / remaining chart refs — labelled placeholder (real rendering
    # lands with the embed/figure slice).
    surface = color.get("surface", "#F1F3F6")
    sec = color.get("secondary", "#6B7280")
    return (
        f'<div class="layer ph" style="{pos}{anim}'
        f"background:{_rgba(surface, 0.9)};border:2px dashed {_rgba(sec, 0.6)};color:{sec};\">"
        f'<span class="phtype">{html.escape(str(typ).upper())}</span>{content}</div>'
    )


def _chart(layer: dict[str, Any], color: dict[str, str], scene_start: float, pos: str, paint: str) -> str:
    """Animated infographic layer: a growing bar chart or a counting-up KPI."""
    sec = color.get("secondary", "#6B7280")
    fg = color.get("foreground", "#1A2433")
    base = scene_start + 0.3

    if layer.get("chart") == "kpi":
        target = layer.get("data", layer.get("content", 0))
        try:
            target_int = int(float(target))
        except (TypeError, ValueError):
            target_int = 0
        anim = f"--target:{target_int};animation:kpiCount 1.1s {base:g}s both;"
        return (
            f'<div class="layer kpi" style="{pos}">'
            f'<span class="num" style="color:{paint};{anim}"></span></div>'
        )

    # bar chart
    data = layer.get("data") or []
    vals = [float(d.get("value", 0)) for d in data] or [1.0]
    maxv = max(vals) or 1.0
    cols = []
    for i, d in enumerate(data):
        v = float(d.get("value", 0))
        ht = max(2.0, v / maxv * 100.0)
        delay = base + i * 0.12
        cols.append(
            f'<div class="col">'
            f'<span class="val" style="color:{fg}">{v:g}</span>'
            f'<div class="barwrap"><div class="bar" style="height:{ht:g}%;background:{paint};'
            f"animation:barGrow .7s {delay:g}s both;\"></div></div>"
            f'<span class="cat" style="color:{sec}">{html.escape(str(d.get("label", "")))}</span>'
            f"</div>"
        )
    return f'<div class="layer chart-bar" style="{pos}">{"".join(cols)}</div>'


def _scene(i: int, scene: dict[str, Any], start: float, color: dict[str, str]) -> str:
    dur = float(scene.get("duration", 0))
    layers = "".join(_layer(lr, color, start) for lr in scene.get("layers", []))
    style = f"animation:sceneShow {dur:g}s {start:g}s both;"
    return f'<section class="scene" style="{style}">{layers}</section>'


def render_html(spec: dict[str, Any], tokens: dict[str, Any]) -> str:
    """Self-contained, auto-playing HTML for a normalized storyboard."""
    color = tokens.get("color", {})
    w, h = stage_size(spec)
    bg = color.get("background", "#FFFFFF")
    fg = color.get("foreground", "#1A2433")

    starts, t = [], 0.0
    for s in spec.get("scenes", []):
        starts.append(t)
        t += float(s.get("duration", 0))
    total = t
    scenes = "".join(
        _scene(i, s, starts[i], color) for i, s in enumerate(spec.get("scenes", []))
    )

    captions = ""
    if spec.get("global", {}).get("captions"):
        # a simple lower caption track, one cue per scene
        cues = []
        for i, s in enumerate(spec.get("scenes", [])):
            n = s.get("narration")
            if n:
                cues.append(
                    f'<div class="cue" style="animation:sceneShow '
                    f'{float(s["duration"]):g}s {starts[i]:g}s both;">{html.escape(n)}</div>'
                )
        captions = f'<div class="captions">{"".join(cues)}</div>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(str(spec.get('global', {}).get('title', 'motion')))}</title>
<style>
  html,body {{ margin:0; background:#000; }}
  .stage {{ position:relative; width:{w}px; height:{h}px; overflow:hidden;
    background:{bg}; color:{fg}; font-family: ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .scene {{ position:absolute; inset:0; opacity:0; }}
  .layer {{ position:absolute; display:flex; align-items:center; justify-content:center;
    text-align:center; font-weight:700; line-height:1.15; }}
  .layer.text {{ padding:0 4%; }}
  .layer.shape {{ border-radius:6px; }}
  .layer.ph {{ flex-direction:column; gap:6px; border-radius:8px; font-size:1rem; font-weight:600; }}
  .phtype {{ font-size:.7rem; letter-spacing:.16em; opacity:.8; }}
  .captions {{ position:absolute; left:0; right:0; bottom:5%; text-align:center; }}
  .cue {{ position:absolute; left:8%; right:8%; bottom:0; opacity:0;
    font-size:1.15rem; font-weight:600; color:{fg};
    background:{_rgba(bg, 0.0)}; }}
  @keyframes sceneShow {{ 0%{{opacity:0}} 6%{{opacity:1}} 92%{{opacity:1}} 100%{{opacity:0}} }}
  @keyframes mFade {{ from{{opacity:0}} to{{opacity:1}} }}
  @keyframes mUp {{ from{{opacity:0;transform:translateY(28px)}} to{{opacity:1;transform:none}} }}
  @keyframes mWipe {{ from{{opacity:0;transform:translateX(-40px)}} to{{opacity:1;transform:none}} }}
  /* Animated infographics (S4). */
  .chart-bar {{ display:flex; align-items:flex-end; justify-content:center; gap:4%; }}
  .chart-bar .col {{ display:flex; flex-direction:column; align-items:center;
    justify-content:flex-end; height:100%; flex:1; max-width:20%; }}
  .chart-bar .barwrap {{ flex:1; display:flex; align-items:flex-end; width:72%; }}
  .chart-bar .bar {{ width:100%; border-radius:5px 5px 0 0; transform:scaleY(0);
    transform-origin:bottom; }}
  .chart-bar .val {{ font-size:1.4rem; font-weight:700; margin-bottom:8px; }}
  .chart-bar .cat {{ font-size:1rem; font-weight:600; margin-top:10px; }}
  @keyframes barGrow {{ from {{ transform:scaleY(0) }} to {{ transform:scaleY(1) }} }}
  .kpi .num {{ font-size:8rem; font-weight:800; line-height:1; counter-reset: k var(--kpi-num,0); }}
  .kpi .num::after {{ content: counter(k); }}
  @property --kpi-num {{ syntax:"<integer>"; inherits:true; initial-value:0; }}
  @keyframes kpiCount {{ from {{ --kpi-num: 0 }} to {{ --kpi-num: var(--target) }} }}
</style></head>
<body>
  <div class="stage" data-duration="{total:g}">
    {scenes}
    {captions}
  </div>
</body></html>"""
