"""Load, validate, and aggregate the nitpicker's scored test battery.

Tests are YAML scoring mechanisms in ``configs/tests/`` (e.g. the-so-what-test).
The *scoring judgment* — assigning each test/dimension a 1-5 — is the apply-tests
and verdict skills' job. This module is pure mechanics: it loads/validates the
test definitions and deterministically aggregates the per-test + per-dimension
scores into a single weighted result and verdict, against the global review
policy (``configs/default/review-policy.yml``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, TESTS
from . import config as config_mod


# ---------------------------------------------------------------- load / validate
def list_tests() -> list[str]:
    if not TESTS.exists():
        return []
    return sorted(p.stem for p in TESTS.glob("*.y*ml"))


def test_path(slug: str) -> Path:
    for ext in (".yaml", ".yml"):
        p = TESTS / f"{slug}{ext}"
        if p.exists():
            return p
    return TESTS / f"{slug}.yaml"


def load(slug: str) -> dict[str, Any]:
    p = test_path(slug)
    if not p.exists():
        raise FileNotFoundError(f"no test '{slug}' in {TESTS}")
    with p.open() as f:
        return yaml.safe_load(f) or {}


def validate(slug: str) -> list[str]:
    try:
        spec = load(slug)
    except FileNotFoundError as e:
        return [str(e)]
    schema_path = SCHEMAS / "test.schema.json"
    if not schema_path.exists():
        return ["test.schema.json missing from plugin"]
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(spec)
    ]


def show(slug: str) -> str:
    return yaml.safe_dump(load(slug), sort_keys=False, default_flow_style=False)


# ---------------------------------------------------------------- aggregation
def _scale(spec: dict, policy_scale: dict) -> tuple[float, float]:
    sc = spec.get("scale") or policy_scale or {"min": 1, "max": 5}
    return float(sc.get("min", 1)), float(sc.get("max", 5))


def _norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _flatten(scores: dict | None) -> dict[str, float]:
    """Accept either ``{key: 4}`` or ``{key: {score: 4, note: "..."}}``."""
    out: dict[str, float] = {}
    for key, val in (scores or {}).items():
        if isinstance(val, dict):
            if val.get("score") is not None:
                out[key] = float(val["score"])
        elif val is not None:
            out[key] = float(val)
    return out


def aggregate(scores: dict) -> dict[str, Any]:
    """Turn a ``scores.yml`` payload into a scorecard + verdict.

    ``scores`` shape::

        tests:        {the-so-what-test: 4, the-yawn-test: 3, the-sniff-test: 5}
        dimensions:   {visual-qa: 4, brief-fulfilment: 3, audience-fit: 4, tone-of-voice: 4}

    Returns ``{overall, verdict, items[], gates_failed[]}``.
    """
    policy = config_mod.review_policy()
    policy_scale = policy.get("scale") or {"min": 1, "max": 5}
    vbands = policy.get("verdict") or {}
    pass_band = float(vbands.get("pass", 80))
    revise_band = float(vbands.get("revise", 60))
    fail_floor_ratio = float(vbands.get("fail_floor_ratio", 0.4))
    weights = policy.get("weights") or {}
    test_weights = weights.get("tests") or {}
    dim_weights = weights.get("dimensions") or {}
    gates = set(policy.get("gates") or [])

    items: list[dict[str, Any]] = []

    for slug, score in _flatten(scores.get("tests")).items():
        try:
            spec = load(slug)
        except FileNotFoundError:
            spec = {}
        lo, hi = _scale(spec, policy_scale)
        if spec.get("weight") is not None:
            weight = float(spec["weight"])
        else:
            weight = float(test_weights.get(slug, test_weights.get("default", 1.0)))
        items.append(_item("test", slug, score, lo, hi, weight, slug in gates, spec))

    for key, score in _flatten(scores.get("dimensions")).items():
        lo, hi = float(policy_scale.get("min", 1)), float(policy_scale.get("max", 5))
        weight = float(dim_weights.get(key, 1.0))
        items.append(_item("dimension", key, score, lo, hi, weight, key in gates, {}))

    total_w = sum(i["weight"] for i in items) or 1.0
    overall = round(100 * sum(i["norm"] * i["weight"] for i in items) / total_w, 1)

    gates_failed = []
    for i in items:
        if i["gate"]:
            floor = i["min"] + fail_floor_ratio * (i["max"] - i["min"])
            if i["score"] <= floor:
                gates_failed.append(i["key"])

    if gates_failed or overall < revise_band:
        verdict = "fail"
    elif overall < pass_band:
        verdict = "revise"
    else:
        verdict = "pass"

    return {
        "overall": overall,
        "verdict": verdict,
        "bands": {"pass": pass_band, "revise": revise_band},
        "gates_failed": gates_failed,
        "items": items,
    }


def _item(
    kind: str,
    key: str,
    score: float,
    lo: float,
    hi: float,
    weight: float,
    gate: bool,
    spec: dict,
) -> dict[str, Any]:
    threshold = spec.get("threshold") or {}
    pass_t = threshold.get("pass")
    warn_t = threshold.get("warn")
    if pass_t is not None and score >= pass_t:
        status = "pass"
    elif warn_t is not None and score >= warn_t:
        status = "warn"
    elif pass_t is not None or warn_t is not None:
        status = "fail"
    else:  # no per-item threshold: derive from the normalised value
        status = "pass" if _norm(score, lo, hi) >= 0.6 else "warn"
    return {
        "kind": kind,
        "key": key,
        "score": score,
        "min": lo,
        "max": hi,
        "norm": round(_norm(score, lo, hi), 3),
        "weight": weight,
        "gate": gate,
        "status": status,
    }
