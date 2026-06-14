"""Materialise caller-supplied lead list + rollups."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import load_yaml
from .store import write_leads


def _load(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yml", ".yaml"):
        return load_yaml(text)
    return json.loads(text)


def materialise(slug: str, leads_json: Path) -> dict:
    payload = _load(leads_json)
    payload["rollups"] = rollups(payload)
    return write_leads(slug, payload)


def rollups(leads: dict) -> dict:
    rows = leads.get("leads") or []
    by_fit = Counter((r.get("fit") or "unknown") for r in rows)
    by_source = Counter((r.get("source") or "unknown") for r in rows)
    by_owner = Counter((r.get("owner") or "unassigned") for r in rows)
    return {
        "count": len(rows),
        "by_fit": dict(by_fit),
        "by_source": dict(by_source),
        "by_owner": dict(by_owner),
    }
