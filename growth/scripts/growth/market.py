"""Materialise caller-supplied market map + rollups."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import load_yaml
from .store import write_market


def _load(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yml", ".yaml"):
        return load_yaml(text)
    return json.loads(text)


def materialise(slug: str, market_json: Path) -> dict:
    payload = _load(market_json)
    payload["rollups"] = rollups(payload)
    return write_market(slug, payload)


def rollups(market: dict) -> dict:
    segs = market.get("segments") or []
    comps = market.get("competitors") or []
    quadrants = Counter((c.get("positioning_quadrant") or "unknown") for c in comps)
    by_seg = Counter((c.get("segment") or "unknown") for c in comps)
    return {
        "segment_count": len(segs),
        "competitor_count": len(comps),
        "competitors_by_segment": dict(by_seg),
        "competitors_by_quadrant": dict(quadrants),
    }
