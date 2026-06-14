"""Materialise the caller-supplied plan + derive deterministic rollups.

Caller-supplied-JSON materialiser pattern (mirror of commercial's value.py
and the tool-bench materialisers). The model (or any caller) produces the
structured plan; this module validates + materialises + derives rollups
(total days, contingency %, by-role / by-swimlane totals, phase
durations).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import load_yaml
from .store import write_plan


def _load_plan_payload(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yml", ".yaml"):
        return load_yaml(text)
    return json.loads(text)


def materialise(slug: str, plan_json: Path) -> dict:
    """Validate + write the plan; return the persisted payload."""
    payload = _load_plan_payload(plan_json)
    payload["rollups"] = rollups(payload)
    return write_plan(slug, payload)


def rollups(plan: dict) -> dict:
    """Deterministic derivations from the structured plan.

    Returned shape:

    .. code-block:: json

      {
        "total_days": 220,
        "buffer_days": 22,
        "phase_count": 5,
        "swimlane_count": 3,
        "by_role": {"lead": 30, "senior": 80, "mid": 100, "junior": 10},
        "by_swimlane": {"design": 40, "content": 60, ...},
        "phase_durations": [{"id": "phase-1-mobilise", "duration": 10, "buffer": 2}, ...],
        "contingency_pct": 11.4,  // (sum of buffers + pool) / total_days
        "raid": {"open": 0, "resolved": 0}  // populated separately if a raid arg is passed
      }
    """
    phases = plan.get("phases") or []
    by_role: dict[str, float] = {}
    by_swimlane: dict[str, float] = {}
    phase_durations = []
    total_days = 0.0
    buffer_days = 0.0
    for ph in phases:
        dur = float(ph.get("duration_days", 0))
        buf = float(ph.get("buffer_days", 0))
        total_days += dur
        buffer_days += buf
        swim = ph.get("swimlane") or "unassigned"
        by_swimlane[swim] = by_swimlane.get(swim, 0.0) + dur
        phase_durations.append(
            {
                "id": ph.get("id"),
                "name": ph.get("name"),
                "duration": dur,
                "buffer": buf,
            }
        )
        for r in ph.get("resourcing", []) or []:
            role = r.get("role")
            days = float(r.get("days", 0))
            if role:
                by_role[role] = by_role.get(role, 0.0) + days

    pool = float((plan.get("contingency") or {}).get("pool_days", 0))
    contingency_total = buffer_days + pool
    contingency_pct = (
        round(100 * contingency_total / total_days, 1) if total_days else 0.0
    )
    return {
        "total_days": total_days,
        "buffer_days": buffer_days,
        "contingency_pool_days": pool,
        "contingency_pct": contingency_pct,
        "phase_count": len(phases),
        "swimlane_count": len(plan.get("swimlanes") or []),
        "by_role": {k: round(v, 2) for k, v in by_role.items()},
        "by_swimlane": {k: round(v, 2) for k, v in by_swimlane.items()},
        "phase_durations": phase_durations,
    }
