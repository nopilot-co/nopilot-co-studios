"""Materialise the caller-supplied analysis + derive deterministic rollups."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import load_yaml
from .store import write_analysis


def _load_payload(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yml", ".yaml"):
        return load_yaml(text)
    return json.loads(text)


def materialise(slug: str, analysis_json: Path) -> dict:
    payload = _load_payload(analysis_json)
    payload["rollups"] = rollups(payload)
    return write_analysis(slug, payload)


def rollups(analysis: dict) -> dict:
    patterns = analysis.get("patterns") or []
    insights = analysis.get("insights") or []
    recs = analysis.get("recommendations") or []
    dataset = analysis.get("dataset") or {}
    insight_severity = Counter((i.get("severity") or "unknown") for i in insights)
    insight_confidence = Counter((i.get("confidence") or "unknown") for i in insights)
    pattern_confidence = Counter((p.get("confidence") or "unknown") for p in patterns)
    rec_owners = Counter((r.get("owner") or "unassigned") for r in recs)
    rec_severity = Counter((r.get("severity") or "unknown") for r in recs)
    return {
        "sample_size": dataset.get("sample_size"),
        "pattern_count": len(patterns),
        "insight_count": len(insights),
        "recommendation_count": len(recs),
        "insights_by_severity": dict(insight_severity),
        "insights_by_confidence": dict(insight_confidence),
        "patterns_by_confidence": dict(pattern_confidence),
        "recommendations_by_severity": dict(rec_severity),
        "recommendations_by_owner": dict(rec_owners),
    }
