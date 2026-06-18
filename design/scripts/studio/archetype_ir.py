"""Cross-backend archetype IR (ADR-006 / #129 — render convergence).

ONE normaliser turns a `:::` fence's spec into a typed, backend-agnostic *node*;
the gslide / pptx / UDS-HTML serialisers each render that node natively. Before
this, every backend re-parsed the fence with its own vocabulary and spec shape —
gslide's per-bar ``series:[{label,value,display}]`` vs the canonical
``series:[{name,y:[…]}]`` (charts.py / pptx / viz_data) vs raw YAML re-parsed in
pptx. The node is the single place those dialects reconcile, so a brand change or
a spec authored either way renders identically across HTML, PPTX and Slides.

Design rules:
- **Normalise once, render per-backend.** This module owns the fence→node
  reconciliation (no judgement); each backend owns only its native emit.
- **Degrade, never crash.** A malformed spec yields a node with empty data; the
  backend renders a visible placeholder (fail-closed — never a silent drop).
- **Tokens bridge in.** Colour comes from the brand's resolved dataviz ramp
  (`uds.resolve_uds`); ``palette_for`` adapts it (or the default) for any backend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

# Brand-agnostic dataviz ramp (crimson-led) — the fallback when no brand resolves.
# A brand's own ramp (uds.resolve_uds(brand)["dataviz"]) overrides this.
DEFAULT_RAMP = ["#E11A57", "#3B66CA", "#2F8F86", "#FFC10E", "#7A4FA3", "#E2683C"]

CHART_TYPES = {"bar", "line", "pie", "scatter", "area"}

# Capability matrix: which backends render which archetype. Drives the parity
# test and the fail-closed placeholder. Extended as archetypes converge (#129).
CAPABILITIES: dict[str, set[str]] = {
    "chart": {"gslide", "pptx", "html"},
}

# Fence name → canonical archetype (aliases collapse here as archetypes land).
ALIASES: dict[str, str] = {
    "chart": "chart",
}


def canonical(name: str) -> str:
    """The canonical archetype name for a fence name (identity if unknown)."""
    return ALIASES.get(name, name)


# ----------------------------------------------------------------- helpers
def _num(v: Any) -> float:
    """'30d' / '1.8M'→1.8 / 40 → float; non-numeric → 0.0 (never raises)."""
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?[0-9]*\.?[0-9]+", str(v if v is not None else ""))
    return float(m.group()) if m else 0.0


def _as_spec(spec: Any) -> dict:
    """Accept a parsed mapping or a raw YAML body string; never raise."""
    if isinstance(spec, dict):
        return spec
    if isinstance(spec, str):
        try:
            v = yaml.safe_load(spec)
        except yaml.YAMLError:
            return {}
        return v if isinstance(v, dict) else {}
    return {}


def palette_for(brand: str | None) -> list[str]:
    """The dataviz ramp for a brand (its resolved ``dataviz`` tokens), or the
    default ramp when no brand is given or it can't be resolved."""
    if brand:
        try:
            from . import uds as _uds

            ramp = _uds.resolve_uds(brand).get("dataviz")
            if ramp:
                return [str(c) for c in ramp]
        except Exception:  # noqa: BLE001 — colour is best-effort; never fail a render
            pass
    return list(DEFAULT_RAMP)


# ----------------------------------------------------------------- chart
@dataclass
class Series:
    name: str = ""
    values: list[float] = field(default_factory=list)
    displays: list[str] = field(default_factory=list)  # per-point label, e.g. "30d"


@dataclass
class ChartNode:
    chart_type: str = "bar"
    categories: list[str] = field(default_factory=list)
    series: list[Series] = field(default_factory=list)
    title: str = ""
    caption: str = ""

    @property
    def is_empty(self) -> bool:
        return not any(s.values for s in self.series)


def _per_bar(items: list, cats: list[str]) -> ChartNode:
    """gslide/per-bar dialect: each item is one category + one value (+ display)."""
    pts = [d for d in items if isinstance(d, dict)]
    cats = cats or [str(d.get("label", d.get("name", ""))) for d in pts]
    vals = [_num(d.get("value")) for d in pts]
    disp = [str(d.get("display", d.get("value", ""))) for d in pts]
    return ChartNode("bar", cats, [Series("", vals, disp)])


def normalise_chart(spec: Any) -> ChartNode:
    """Reconcile every chart dialect into one ChartNode (parsed dict or raw body).

    canonical (charts.py / pptx / viz_data):
        type, x|labels → categories; y → one series; series:[{name,y:[…]}] → many;
        pie: values|y with labels.
    gslide/per-bar:
        series:[{label,value,display}] or data:[…] → categories=labels, one series.
    """
    s = _as_spec(spec)
    ctype = (str(s.get("type", "bar")).strip().lower() or "bar")
    title = str(s.get("title", "") or "")
    caption = str(s.get("caption", "") or "")
    cats = [str(v) for v in (s.get("x") or s.get("labels") or [])]

    raw = s.get("series")
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        if "value" in raw[0] or "display" in raw[0]:        # per-bar dialect
            node = _per_bar(raw, cats)
        else:                                               # canonical multi-series
            out: list[Series] = []
            for d in raw:
                if not isinstance(d, dict):
                    continue
                ys = [_num(v) for v in (d.get("y") or [])]
                out.append(Series(str(d.get("name") or d.get("label") or ""), ys, [str(v) for v in ys]))
            node = ChartNode(ctype, cats, out)
    elif isinstance(s.get("data"), list):                    # gslide `data:` alias
        node = _per_bar(s["data"], cats)
    elif s.get("values") is not None:                        # pie (or single series via values)
        ys = [_num(v) for v in s["values"]]
        node = ChartNode(ctype, cats, [Series("", ys, [str(v) for v in s["values"]])])
    elif s.get("y") is not None:                             # canonical single series
        ys = [_num(v) for v in s["y"]]
        node = ChartNode(ctype, cats, [Series(str(s.get("name") or s.get("label") or ""), ys, [str(v) for v in s["y"]])])
    else:
        node = ChartNode(ctype, cats, [])
    node.chart_type, node.title, node.caption = ctype, title, caption
    return node
