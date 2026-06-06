"""Deterministic check evaluation for the beancounter.

Given a deal + the org rate card + pricing policy, this module computes the
per-check scores that feed the nitpicker engine. Each check is one scored test
in the nitpicker test format. The CLI calls these; the LLM (`check-commercials`
skill) interprets and narrates findings.

Checks (extensible via `configs/checks/<name>.yaml`):

- ``rate-card-compliance`` (gate) — every role rate ≥ rate-card floor.
- ``margin-floor`` (gate) — projected margin ≥ policy floor.
- ``ratio-mix`` (advisory) — role mix within policy bands.
"""

from __future__ import annotations

from typing import Any

from . import load_yaml


def _role_index(rate_card: dict) -> dict[str, dict]:
    return {r["role"]: r for r in rate_card.get("roles", [])}


# ----------------------------------------------------------------- per-check


def check_rate_card_compliance(deal: dict, rate_card: dict) -> dict[str, Any]:
    """Score 5 = every role rate ≥ floor; 1 = any role below floor.

    Returns a structured result with score + evidence so the skill can narrate.
    """
    idx = _role_index(rate_card)
    breaches = []
    for line in deal.get("lines", []):
        role = line.get("role")
        rate = float(line.get("rate", 0))
        floor = float((idx.get(role) or {}).get("rate", 0))
        if floor and rate < floor:
            breaches.append(
                {"role": role, "rate": rate, "floor": floor, "shortfall": floor - rate}
            )
    return {
        "id": "rate-card-compliance",
        "score": 1 if breaches else 5,
        "passed": not breaches,
        "evidence": {
            "lines_checked": len(deal.get("lines", [])),
            "breaches": breaches,
        },
    }


def deal_totals(deal: dict, rate_card: dict) -> dict[str, float]:
    """Derive deal revenue + cost + margin from the deal lines and rate card."""
    idx = _role_index(rate_card)
    rev = 0.0
    cost = 0.0
    days_total = 0.0
    by_role_days: dict[str, float] = {}
    for line in deal.get("lines", []):
        role = line.get("role")
        rate = float(line.get("rate", 0))
        days = float(line.get("days", 0))
        rev += rate * days
        cost_rate = float((idx.get(role) or {}).get("cost", 0))
        cost += cost_rate * days
        days_total += days
        by_role_days[role] = by_role_days.get(role, 0.0) + days
    margin = (rev - cost) / rev if rev else 0.0
    return {
        "revenue": rev,
        "cost": cost,
        "margin": margin,
        "days_total": days_total,
        "by_role_days": by_role_days,
    }


def check_margin_floor(deal: dict, rate_card: dict, policy: dict) -> dict[str, Any]:
    """Score 5 = margin ≥ floor + 5pp; 4 = ≥ floor; 1 = below floor."""
    totals = deal_totals(deal, rate_card)
    floor = float(policy.get("margin_floor", 0))
    m = totals["margin"]
    if m >= floor + 0.05:
        score = 5
    elif m >= floor:
        score = 4
    elif m >= floor - 0.05:
        score = 2
    else:
        score = 1
    return {
        "id": "margin-floor",
        "score": score,
        "passed": m >= floor,
        "evidence": {
            "revenue": totals["revenue"],
            "cost": totals["cost"],
            "margin": m,
            "floor": floor,
        },
    }


def check_ratio_mix(deal: dict, rate_card: dict, policy: dict) -> dict[str, Any]:
    """Score 5 = every role within its policy band; 1 = any role outside band.

    Advisory (not a gate) — surfaces skill-mix concerns without blocking.
    """
    totals = deal_totals(deal, rate_card)
    days_total = totals["days_total"] or 1.0
    by_role = totals["by_role_days"]
    breaches = []
    for role, max_share in (policy.get("max_ratios") or {}).items():
        share = by_role.get(role, 0.0) / days_total
        if share > float(max_share):
            breaches.append(
                {
                    "role": role,
                    "share": share,
                    "max": float(max_share),
                    "kind": "above-max",
                }
            )
    for role, min_share in (policy.get("min_ratios") or {}).items():
        share = by_role.get(role, 0.0) / days_total
        if share < float(min_share):
            breaches.append(
                {
                    "role": role,
                    "share": share,
                    "min": float(min_share),
                    "kind": "below-min",
                }
            )
    return {
        "id": "ratio-mix",
        "score": 5 if not breaches else max(1, 5 - len(breaches)),
        "passed": not breaches,
        "evidence": {
            "days_total": days_total,
            "by_role_days": by_role,
            "breaches": breaches,
        },
    }


# ----------------------------------------------------------------- orchestrator


CHECKS = {
    "rate-card-compliance": check_rate_card_compliance,
    "margin-floor": check_margin_floor,
    "ratio-mix": check_ratio_mix,
}


def evaluate(deal: dict, rate_card: dict, policy: dict) -> list[dict]:
    """Run every wired-up check; return per-check results."""
    results = []
    for cid, fn in CHECKS.items():
        if cid == "rate-card-compliance":
            results.append(fn(deal, rate_card))
        else:
            results.append(fn(deal, rate_card, policy))
    return results


def to_scores_yaml(results: list[dict]) -> dict:
    """Shape per-check results for the nitpicker engine's ``scores.yml`` input.

    The nitpicker engine reads ``{tests: {slug: score}}`` (see
    ``nitpicker/scripts/nit/tests.py::aggregate``). Critical gates are honored
    via the rubric's ``gates:`` list, so we keep this payload minimal — just
    the per-check 1-5 scores. The per-check ``evidence`` lives in
    ``review/v<ver>/findings.md`` (skill-written) rather than scores.yml so
    the engine input matches every other studio's.
    """
    return {"tests": {r["id"]: r["score"] for r in results}}


def load_checks_dir(path) -> list[dict]:
    """Read all <name>.yaml from configs/checks/. Same shape as nitpicker tests."""
    out = []
    for p in sorted(path.glob("*.yaml")):
        data = load_yaml(p.read_text())
        if data:
            data["__file"] = str(p)
            out.append(data)
    return out
