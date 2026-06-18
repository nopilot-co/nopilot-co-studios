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
    "flow": {"gslide", "pptx", "html"},
    "cards": {"gslide", "pptx", "html"},
    "swimlane": {"gslide", "html"},  # the timeline/gantt model. pptx renders a DISTINCT
    #                                  node-flow swimlane — not the same viz (see #129).
    "stat-panel": {"gslide", "html"},
    "pullquote": {"gslide", "html"},
    "cta": {"gslide", "html"},
    "bullseye": {"gslide", "html"},
}

# Fence name → canonical archetype (aliases collapse here as archetypes land).
ALIASES: dict[str, str] = {
    "chart": "chart",
    "flow": "flow",
    "process": "flow",  # gslide/pptx render :::process as a flow; HTML keeps its card
    #                     form pending a process→flow reconciliation of the 360 example.
    "cards": "cards",
    "card-grid": "cards",
    "swimlane": "swimlane",
    "timeline": "swimlane",  # gslide renders :::timeline via the swimlane (gantt) model
    "stat-panel": "stat-panel",
    "stats": "stat-panel",
    "pullquote": "pullquote",
    "cta": "cta",
    "bullseye": "bullseye",
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


# ----------------------------------------------------------------- flow / process
@dataclass
class Step:
    title: str = ""
    caption: str = ""


@dataclass
class FlowNode:
    steps: list[Step] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.steps


def _split_step(text: str) -> Step:
    """A flat step string 'Title — caption' (em/en dash or hyphen) → Step."""
    for sep in (" — ", " – ", " - "):
        if sep in text:
            head, _, tail = text.partition(sep)
            return Step(head.strip(), tail.strip())
    return Step(text.strip(), "")


def normalise_flow(spec: Any) -> FlowNode:
    """Reconcile flow dialects into ordered Steps (parsed value or raw body):
        gslide    steps:[{title,caption}]  |  a bare list
        html      steps:["Title — caption", …]   (the :::process card source)
        diagrams  nodes:[label, …]  |  steps:[label, …]
    """
    raw = spec
    if isinstance(spec, str):
        try:
            raw = yaml.safe_load(spec)
        except yaml.YAMLError:
            raw = None
    if isinstance(raw, dict):
        items = raw.get("steps") or raw.get("nodes") or raw.get("stages") or []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    steps: list[Step] = []
    for it in items:
        if isinstance(it, dict):
            steps.append(Step(
                str(it.get("title") or it.get("label") or it.get("name") or ""),
                str(it.get("caption") or it.get("body") or it.get("desc") or ""),
            ))
        else:
            steps.append(_split_step(str(it)))
    return FlowNode(steps)


# ----------------------------------------------------------------- cards
@dataclass
class Card:
    title: str = ""
    body: str = ""
    eyebrow: str = ""


@dataclass
class CardsNode:
    cards: list[Card] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.cards


def normalise_cards(spec: Any) -> CardsNode:
    """Reconcile card dialects into Cards (parsed value or raw body):
        gslide  a bare list of {eyebrow?,title,body}  |  {cards:[…]}
        a list of strings → title-only cards.
    """
    raw = spec
    if isinstance(spec, str):
        try:
            raw = yaml.safe_load(spec)
        except yaml.YAMLError:
            raw = None
    if isinstance(raw, dict):
        items = raw.get("cards") or raw.get("items") or []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    cards: list[Card] = []
    for it in items:
        if isinstance(it, dict):
            cards.append(Card(
                str(it.get("title") or it.get("label") or it.get("name") or ""),
                str(it.get("body") or it.get("caption") or it.get("desc") or it.get("excerpt") or ""),
                str(it.get("eyebrow") or ""),
            ))
        else:
            cards.append(Card(str(it)))
    return CardsNode(cards)


# ----------------------------------------------------------------- swimlane (timeline / gantt)
@dataclass
class Lane:
    name: str = ""
    label: str = ""
    start: str = ""
    end: str = ""


@dataclass
class Milestone:
    at: str = ""
    label: str = ""


@dataclass
class SwimlaneNode:
    months: list[str] = field(default_factory=list)
    lanes: list[Lane] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.months and self.lanes)


def normalise_swimlane(spec: Any) -> SwimlaneNode:
    """Reconcile the timeline/gantt swimlane (gslide model): a month axis, lanes each with
    a span bar (start→end month + label), and milestones (at + label). NB: the pptx
    node-flow swimlane is a different visualisation and is NOT unified here (#129)."""
    s = _as_spec(spec)
    months = [str(m) for m in (s.get("months") or [])]
    lanes: list[Lane] = []
    for ln in (s.get("lanes") or []):
        if isinstance(ln, dict):
            lanes.append(Lane(str(ln.get("name", "")), str(ln.get("label", "")),
                              str(ln.get("start", "")), str(ln.get("end", ""))))
    milestones: list[Milestone] = []
    for m in (s.get("milestones") or []):
        if isinstance(m, dict):
            milestones.append(Milestone(str(m.get("at", "")), str(m.get("label", ""))))
    return SwimlaneNode(months, lanes, milestones)


# ----------------------------------------------------------------- stat-panel / pullquote / cta
@dataclass
class Stat:
    value: str = ""
    label: str = ""
    delta: str = ""


@dataclass
class StatsNode:
    items: list[Stat] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.items


def normalise_stats(spec: Any) -> StatsNode:
    """A stat panel: a list of {value, label, delta?} (the HTML `_stat_grid` shape)."""
    raw = spec
    if isinstance(spec, str):
        try:
            raw = yaml.safe_load(spec)
        except yaml.YAMLError:
            raw = None
    items_raw = (raw.get("items") or raw.get("stats")) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    items: list[Stat] = []
    for it in (items_raw or []):
        if isinstance(it, dict):
            items.append(Stat(str(it.get("value", "")), str(it.get("label", "")), str(it.get("delta", "") or "")))
    return StatsNode(items)


@dataclass
class PullQuoteNode:
    body: str = ""
    attribution: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.body


def normalise_pullquote(spec: Any) -> PullQuoteNode:
    """A pull-quote: body + optional trailing `— attribution` line (the HTML shape)."""
    if isinstance(spec, dict):
        return PullQuoteNode(str(spec.get("quote") or spec.get("body", "")), str(spec.get("attribution", "") or spec.get("by", "")))
    lines = [ln.strip() for ln in str(spec or "").strip().splitlines() if ln.strip()]
    attribution = ""
    if lines and re.match(r"^[—–-]\s+", lines[-1]):
        attribution = re.sub(r"^[—–-]\s+", "", lines.pop())
    return PullQuoteNode(" ".join(lines), attribution)


@dataclass
class CTANode:
    text: str = ""
    button: str = ""
    href: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.text


def normalise_cta(spec: Any) -> CTANode:
    """A call-to-action banner: text (+ optional button label / href)."""
    if isinstance(spec, dict):
        return CTANode(str(spec.get("text", "")), str(spec.get("button", "") or spec.get("label", "")), str(spec.get("href", "")))
    return CTANode(" ".join(str(spec or "").split()))


# ----------------------------------------------------------------- bullseye (concentric rings)
@dataclass
class Ring:
    label: str = ""
    items: list[str] = field(default_factory=list)


@dataclass
class BullseyeNode:
    rings: list[Ring] = field(default_factory=list)  # centre → outward

    @property
    def is_empty(self) -> bool:
        return not self.rings


def normalise_bullseye(spec: Any) -> BullseyeNode:
    """Concentric rings, centre→outward: rings:[{ring,items}] | items:[{ring,label}]
    (mirrors frameworks._bands so the gslide / html / pptx bullseye agree)."""
    s = _as_spec(spec)
    out: list[Ring] = []
    rings = s.get("rings")
    if isinstance(rings, list):
        for r in rings:
            if isinstance(r, dict):
                out.append(Ring(str(r.get("ring") or r.get("label", "")), [str(x) for x in (r.get("items") or [])]))
            else:
                out.append(Ring(str(r), []))
    else:
        grouped: dict[str, list[str]] = {}
        order: list[str] = []
        for it in (s.get("items") or []):
            ring = str(it.get("ring", "")) if isinstance(it, dict) else ""
            label = str(it.get("label", it.get("name", ""))) if isinstance(it, dict) else str(it)
            if ring not in grouped:
                grouped[ring] = []
                order.append(ring)
            grouped[ring].append(label)
        out = [Ring(r, grouped[r]) for r in order]
    return BullseyeNode(out)
