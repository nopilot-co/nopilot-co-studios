"""Lottie export — a storyboard as a Bodymovin/Lottie JSON animation.

The embeddable vector path (ADR-002): scenes become time windows, layers become
Lottie shape/text layers with opacity keyframes, painted in the brand tokens.
Hand-built (no dependency) so the plugin stays light and the JSON is portable to
any Lottie player (lottie-web, mobile, After Effects).

Layer/region/role/motion semantics are kept in sync with ``animate.py`` (the
declarative renderer) and ``templates/remotion`` (the high-fidelity engine).

Note: text layers render with the named font family in lottie-web; embedding font
glyph data for offline players (AE/mobile) is a later refinement.
"""

from __future__ import annotations

from typing import Any

from .board import _REGIONS  # region → inset (top,right,bottom,left) %
from .animate import _ASPECT_WH, _ROLE_COLOR

_FONT_NAME = "MotionSans"
_ENTER_SECONDS = 0.4
_FADE_OUT_SECONDS = 0.25


def _hex_rgb(value: str) -> list[float]:
    h = value.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    except ValueError:
        return [0.42, 0.45, 0.5]


def _box(region: str, w: int, h: int) -> tuple[float, float, float, float]:
    """region → (center_x, center_y, width, height) in px."""
    t, r, b, l = _REGIONS.get(region, _REGIONS["center"])
    x0, x1 = l / 100 * w, (100 - r) / 100 * w
    y0, y1 = t / 100 * h, (100 - b) / 100 * h
    return ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)


def _opacity(scene_start: int, scene_end: int, fps: int) -> dict[str, Any]:
    """Animated opacity: fade in at scene start, hold, fade out at scene end."""
    enter = max(1, round(_ENTER_SECONDS * fps))
    out = max(1, round(_FADE_OUT_SECONDS * fps))
    ease_i, ease_o = {"x": [0.4], "y": [1]}, {"x": [0.4], "y": [0]}
    return {
        "a": 1,
        "k": [
            {"t": scene_start, "s": [0], "i": ease_i, "o": ease_o},
            {"t": scene_start + enter, "s": [100], "i": ease_i, "o": ease_o},
            {"t": max(scene_start + enter, scene_end - out), "s": [100], "i": ease_i, "o": ease_o},
            {"t": scene_end, "s": [0]},
        ],
    }


def _xform(cx: float, cy: float, opacity: dict[str, Any]) -> dict[str, Any]:
    return {
        "o": opacity,
        "r": {"a": 0, "k": 0},
        "p": {"a": 0, "k": [cx, cy, 0]},
        "a": {"a": 0, "k": [0, 0, 0]},
        "s": {"a": 0, "k": [100, 100, 100]},
    }


def _shape_layer(ind, name, cx, cy, w, h, rgb, ip, op, opacity, radius=6) -> dict[str, Any]:
    group = {
        "ty": "gr",
        "it": [
            {"ty": "rc", "d": 1, "s": {"a": 0, "k": [w, h]}, "p": {"a": 0, "k": [0, 0]}, "r": {"a": 0, "k": radius}},
            {"ty": "fl", "c": {"a": 0, "k": rgb + [1]}, "o": {"a": 0, "k": 100}, "r": 1},
            {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]},
             "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}},
        ],
    }
    return {
        "ddd": 0, "ind": ind, "ty": 4, "nm": name, "sr": 1,
        "ks": _xform(cx, cy, opacity), "ao": 0, "shapes": [group],
        "ip": ip, "op": op, "st": ip, "bm": 0,
    }


def _text_layer(ind, name, cx, cy, text, size, rgb, ip, op, opacity) -> dict[str, Any]:
    doc = {
        "s": size, "f": _FONT_NAME, "t": text, "j": 2, "tr": 0,
        "lh": round(size * 1.2), "ls": 0, "fc": rgb,
    }
    return {
        "ddd": 0, "ind": ind, "ty": 5, "nm": name, "sr": 1,
        "ks": _xform(cx, cy + size / 3.0, opacity), "ao": 0,
        "t": {"d": {"k": [{"t": 0, "s": doc}]}, "p": {}, "m": {"g": 1, "a": {"a": 0, "k": [0, 0]}}, "a": []},
        "ip": ip, "op": op, "st": ip, "bm": 0,
    }


def render(spec: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
    """Build a Lottie animation dict from a normalized storyboard + tokens."""
    color = tokens.get("color", {})
    g = spec.get("global", {})
    fps = int(g.get("fps", 30))
    w, h = _ASPECT_WH.get(g.get("aspect", "16:9"), (1280, 720))

    layers: list[dict[str, Any]] = []
    ind = 1
    start = 0.0
    for scene in spec.get("scenes", []):
        s0 = round(start * fps)
        start += float(scene.get("duration", 0))
        s1 = round(start * fps)
        opacity = _opacity(s0, s1, fps)
        for lr in scene.get("layers", []):
            cx, cy, bw, bh = _box(lr.get("region", "center"), w, h)
            paint = color.get(_ROLE_COLOR.get(lr.get("role", ""), ""), color.get("foreground", "#1A2433"))
            rgb = _hex_rgb(paint)
            typ = lr.get("type")
            content = str(lr.get("content", ""))
            big = lr.get("region", "center") in ("center", "top", "full")
            if typ == "text":
                layers.append(_text_layer(ind, f"{scene['id']}:text", cx, cy, content,
                                          64 if big else 38, rgb, s0, s1, opacity))
            elif typ == "shape":
                is_rule = "rule" in content.lower()
                layers.append(_shape_layer(ind, f"{scene['id']}:shape", cx,
                                          cy if not is_rule else cy + bh / 2 - 4,
                                          bw, 8 if is_rule else bh, rgb, s0, s1, opacity))
            else:  # image / icon / chart → surface plate + label
                surf = _hex_rgb(color.get("surface", "#F1F3F6"))
                layers.append(_shape_layer(ind, f"{scene['id']}:{typ}", cx, cy, bw, bh, surf, s0, s1, opacity))
                ind += 1
                lbl = _hex_rgb(color.get("secondary", "#6B7280"))
                layers.append(_text_layer(ind, f"{scene['id']}:{typ}-label", cx, cy,
                                          f"{str(typ).upper()}  {content}", 22, lbl, s0, s1, opacity))
            ind += 1

    op = max(1, round(start * fps))
    bg = _hex_rgb(color.get("background", "#FFFFFF"))
    # Full-frame background solid. Lottie draws layers in array order with the
    # FIRST layer on top, so the background goes LAST (bottom of the stack).
    layers.append(_shape_layer(
        ind, "bg", w / 2, h / 2, w, h, bg, 0, op,
        {"a": 0, "k": 100}, radius=0,
    ))

    return {
        "v": "5.7.0", "fr": fps, "ip": 0, "op": op, "w": w, "h": h,
        "nm": g.get("title", "storyboard"), "ddd": 0, "assets": [],
        "fonts": {"list": [{
            "fName": _FONT_NAME, "fFamily": "Inter, system-ui, sans-serif",
            "fStyle": "Bold", "fWeight": "700", "ascent": 75,
        }]},
        "layers": layers,
    }
